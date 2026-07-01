from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def safe_stem(value: str, fallback: str = "Filtro") -> str:
    cleaned = re.sub(r"[^\w .-]+", "_", value, flags=re.UNICODE).strip(" ._-")
    return cleaned[:100] or fallback


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text_flexible(path: Path) -> tuple[str, str]:
    data = Path(path).read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("Não foi possível identificar a codificação do filtro.")


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, destination)
    finally:
        if temporary and temporary.exists():
            temporary.unlink(missing_ok=True)


def atomic_copy(source: Path, destination: Path) -> Path:
    source = Path(source).resolve()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
        shutil.copy2(source, temporary)
        os.replace(temporary, destination)
        return destination
    finally:
        if temporary and temporary.exists():
            temporary.unlink(missing_ok=True)


def ensure_writable_directory(path: Path) -> None:
    directory = Path(path).expanduser()
    if not directory.exists():
        raise FileNotFoundError(f"A pasta não existe: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"O caminho não é uma pasta: {directory}")
    probe: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".efs-write-test-", delete=False) as handle:
            handle.write(b"ok")
            probe = Path(handle.name)
    except PermissionError as exc:
        raise PermissionError(f"Sem permissão de escrita em: {directory}") from exc
    finally:
        if probe:
            probe.unlink(missing_ok=True)

