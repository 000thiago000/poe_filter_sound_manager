from __future__ import annotations

import os
import re
import secrets
import shutil
import tempfile
import zipfile
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from exile_filter_studio.models import ExportResult
from exile_filter_studio.services.file_utils import read_text_flexible, safe_stem


CUSTOM_SOUND_LINE = re.compile(
    r'^(?P<prefix>\s*CustomAlertSound(?:Optional)?\s+)"(?P<reference>[^"]+)"(?P<suffix>[^\r\n]*)(?=\r?$)',
    re.IGNORECASE | re.MULTILINE,
)


class ExportService:
    """Builds a self-contained filter bundle without leaking original sound names."""

    def _resolve_sound(self, filter_directory: Path, reference: str) -> Path:
        normalized = reference.strip().replace("\\", "/")
        candidate = Path(normalized)
        if not candidate.is_absolute():
            candidate = filter_directory / Path(*PurePosixPath(normalized).parts)
        candidate = candidate.resolve()
        try:
            candidate.relative_to(filter_directory.resolve())
        except ValueError as exc:
            raise ValueError(f"O som está fora da pasta do filtro e não pode ser exportado: {reference}") from exc
        if not candidate.is_file():
            raise FileNotFoundError(f"Som referenciado pelo filtro não foi encontrado: {candidate}")
        return candidate

    @staticmethod
    def _opaque_name(extension: str, used_names: set[str]) -> str:
        while True:
            name = f"asset_{secrets.token_hex(8)}{extension.lower()}"
            if name not in used_names:
                used_names.add(name)
                return name

    @staticmethod
    def _write_bytes(archive: zipfile.ZipFile, archive_name: str, data: bytes) -> None:
        info = zipfile.ZipInfo(archive_name)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, data)

    @staticmethod
    def _write_file(archive: zipfile.ZipFile, archive_name: str, source: Path) -> None:
        info = zipfile.ZipInfo(archive_name)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        with archive.open(info, "w") as destination, source.open("rb") as origin:
            shutil.copyfileobj(origin, destination, length=1024 * 1024)

    def create_share_zip(
        self,
        filter_path: Path,
        destination: Path,
        progress: Callable[[int], None] | None = None,
    ) -> ExportResult:
        filter_path = Path(filter_path).resolve()
        if not filter_path.is_file():
            raise FileNotFoundError(f"Filtro não encontrado: {filter_path}")
        destination = Path(destination).expanduser()
        if destination.suffix.lower() != ".zip":
            destination = destination.with_suffix(".zip")
        destination.parent.mkdir(parents=True, exist_ok=True)

        content, _ = read_text_flexible(filter_path)
        filter_directory = filter_path.parent.resolve()
        source_to_opaque: dict[Path, str] = {}
        used_names: set[str] = set()

        def replace_reference(match: re.Match[str]) -> str:
            raw_reference = match.group("reference")
            if raw_reference.strip().lower() == "none":
                return match.group(0)
            rewritten: list[str] = []
            for part in raw_reference.split(";"):
                reference = part.strip()
                if not reference:
                    continue
                source = self._resolve_sound(filter_directory, reference)
                opaque = source_to_opaque.get(source)
                if not opaque:
                    opaque = self._opaque_name(source.suffix, used_names)
                    source_to_opaque[source] = opaque
                rewritten.append(str(PurePosixPath("sounds", opaque)))
            if not rewritten:
                return match.group(0)
            return f'{match.group("prefix")}"{";".join(rewritten)}"{match.group("suffix")}'

        rewritten_content = CUSTOM_SOUND_LINE.sub(replace_reference, content)
        if not source_to_opaque:
            raise ValueError("O filtro ativo não possui sons personalizados para exportar.")
        if progress:
            progress(15)

        bundle_stem = safe_stem(destination.stem, safe_stem(filter_path.stem))
        exported_filter_name = f"{bundle_stem}.filter"
        instructions = (
            "EXILE FILTER STUDIO - PACOTE DE COMPARTILHAMENTO\n\n"
            "1. Extraia todo o conteudo deste ZIP na pasta de filtros do Path of Exile.\n"
            "2. Mantenha a pasta 'sounds' ao lado do arquivo .filter.\n"
            "3. Selecione o filtro dentro do jogo.\n\n"
            "Os nomes dos audios foram aleatorizados de proposito.\n"
        ).encode("utf-8")

        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=destination.parent,
                prefix=f".{destination.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary = Path(handle.name)
            with zipfile.ZipFile(temporary, "w") as archive:
                self._write_bytes(archive, exported_filter_name, rewritten_content.encode("utf-8"))
                total = len(source_to_opaque)
                for index, (source, opaque) in enumerate(source_to_opaque.items(), start=1):
                    self._write_file(archive, str(PurePosixPath("sounds", opaque)), source)
                    if progress:
                        progress(15 + int(index * 75 / total))
                self._write_bytes(archive, "LEIA-ME.txt", instructions)
            os.replace(temporary, destination)
            temporary = None
            if progress:
                progress(100)
            return ExportResult(destination, exported_filter_name, len(source_to_opaque))
        finally:
            if temporary and temporary.exists():
                temporary.unlink(missing_ok=True)
