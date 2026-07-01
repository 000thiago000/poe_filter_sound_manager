from __future__ import annotations

from pathlib import Path, PurePosixPath

from exile_filter_studio.models import SoundMapping
from exile_filter_studio.services.file_utils import atomic_copy, safe_stem, sha256_file


class SoundService:
    SUPPORTED_EXTENSIONS = {".wav", ".mp3"}

    def list_sounds(self, directory: Path) -> list[Path]:
        folder = Path(directory).expanduser()
        if not folder.is_dir():
            return []
        return sorted(
            (
                path
                for path in folder.rglob("*")
                if path.is_file() and path.suffix.lower() in self.SUPPORTED_EXTENSIONS
            ),
            key=lambda path: path.name.lower(),
        )

    def resolve_mapping_sources(self, source_directory: Path, mappings: list[SoundMapping]) -> dict[str, Path]:
        source_root = Path(source_directory).expanduser().resolve()
        if not source_root.is_dir():
            raise FileNotFoundError(f"A pasta de sons não existe: {source_root}")

        resolved: dict[str, Path] = {}
        for mapping in mappings:
            if not mapping.active:
                continue
            if not mapping.sound_path.strip():
                raise ValueError(f"Selecione um som para {mapping.category}.")
            candidate = Path(mapping.sound_path).expanduser()
            if not candidate.is_absolute():
                candidate = source_root / candidate
            candidate = candidate.resolve()
            try:
                candidate.relative_to(source_root)
            except ValueError as exc:
                raise ValueError(f"O som de {mapping.category} está fora do pacote selecionado.") from exc
            if candidate.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                raise ValueError(f"Formato não suportado em {candidate.name}; use WAV ou MP3.")
            if not candidate.is_file():
                raise FileNotFoundError(f"Som não encontrado para {mapping.category}: {candidate}")
            resolved[mapping.category] = candidate
        return resolved

    def copy_mapped_sounds(
        self,
        sources: dict[str, Path],
        filter_directory: Path,
        subdirectory: str,
        overwrite: bool,
    ) -> tuple[list[Path], dict[str, str]]:
        destination_root = Path(filter_directory)
        clean_subdirectory = safe_stem(subdirectory, "") if subdirectory.strip() else ""
        if clean_subdirectory:
            destination_root = destination_root / clean_subdirectory
        destination_root.mkdir(parents=True, exist_ok=True)

        copied: list[Path] = []
        references: dict[str, str] = {}
        used_names: dict[str, Path] = {}
        for category, source in sources.items():
            name = source.name
            if name.lower() in used_names and used_names[name.lower()] != source:
                name = f"{safe_stem(category)}-{source.name}"
            used_names[name.lower()] = source
            destination = destination_root / name

            if destination.exists():
                if sha256_file(source) != sha256_file(destination):
                    if not overwrite:
                        raise FileExistsError(
                            f"Já existe um som diferente chamado {destination.name}. Ative sobrescrita ou renomeie o arquivo."
                        )
                    atomic_copy(source, destination)
                    copied.append(destination)
            else:
                atomic_copy(source, destination)
                copied.append(destination)

            reference = PurePosixPath(clean_subdirectory, name) if clean_subdirectory else PurePosixPath(name)
            references[category] = str(reference)
        return copied, references

