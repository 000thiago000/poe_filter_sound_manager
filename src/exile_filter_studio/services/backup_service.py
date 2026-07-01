from __future__ import annotations

from pathlib import Path

from exile_filter_studio.repositories.app_repository import AppRepository
from exile_filter_studio.services.file_utils import atomic_copy, safe_stem, timestamp


class BackupService:
    def __init__(self, backup_directory: Path, repository: AppRepository):
        self.backup_directory = Path(backup_directory)
        self.repository = repository

    def create(self, source: Path, reason: str) -> Path:
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(f"Filtro não encontrado para backup: {source}")
        destination = self.backup_directory / f"{safe_stem(source.stem)}-{timestamp()}.filter"
        atomic_copy(source, destination)
        self.repository.add_backup(source.name, destination, source, reason)
        return destination

    def restore(self, backup: Path, destination: Path) -> Path:
        backup = Path(backup)
        destination = Path(destination)
        if not backup.is_file():
            raise FileNotFoundError(f"Backup não encontrado: {backup}")
        if destination.exists():
            self.create(destination, "Backup automático antes da restauração")
        return atomic_copy(backup, destination)

