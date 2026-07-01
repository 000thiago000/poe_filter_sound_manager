from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from exile_filter_studio.config import AppPaths
from exile_filter_studio.database import Database
from exile_filter_studio.logging_setup import configure_logging
from exile_filter_studio.models import ApplyResult, ExportResult, InstallResult, SoundMapping
from exile_filter_studio.repositories.app_repository import AppRepository
from exile_filter_studio.repositories.settings_repository import SettingsRepository
from exile_filter_studio.services.backup_service import BackupService
from exile_filter_studio.services.file_utils import (
    atomic_copy,
    atomic_write_text,
    ensure_writable_directory,
    read_text_flexible,
    safe_stem,
    sha256_file,
    timestamp,
)
from exile_filter_studio.services.export_service import ExportService
from exile_filter_studio.services.filter_editor import FilterEditor
from exile_filter_studio.services.filterblade_service import FilterBladeService
from exile_filter_studio.services.online_filter_service import OnlineFilterService
from exile_filter_studio.services.report_service import ReportService
from exile_filter_studio.services.sound_service import SoundService


class ApplicationManager:
    def __init__(self, paths: AppPaths | None = None):
        self.paths = paths or AppPaths.create()
        self.database = Database(self.paths.database)
        self.database.initialize()
        self.settings = SettingsRepository(self.database)
        self.repository = AppRepository(self.database)
        self.repository.ensure_sound_pack("Padrão", self.settings.get("sound_source_directory"))
        self.logger = configure_logging(self.paths.logs)
        self.filterblade = FilterBladeService()
        self.online_filters = OnlineFilterService()
        self.exporter = ExportService()
        self.editor = FilterEditor()
        self.sounds = SoundService()
        self.backups = BackupService(self.paths.backups, self.repository)
        self.reports = ReportService(self.paths.reports)

    def audit(self, level: str, event: str, message: str, details: object = "") -> None:
        self.repository.log(level, event, message, details)
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method("%s | %s | %s", event, message, details)

    def report_error(self, event: str, error: BaseException) -> None:
        self.audit("ERROR", event, str(error), {"type": type(error).__name__})

    def game_version(self) -> str:
        value = self.settings.get("game_version", "poe2")
        return value if value in {"poe1", "poe2"} else "poe2"

    def set_game_version(self, game_version: str) -> None:
        if game_version not in {"poe1", "poe2"}:
            raise ValueError("Versão de jogo inválida.")
        directory = self.settings.get(f"filter_directory_{game_version}")
        current_filter = self.settings.get(f"current_filter_path_{game_version}")
        self.settings.update(
            {
                "game_version": game_version,
                "filter_directory": directory,
                "current_filter_path": current_filter,
            }
        )

    def close(self) -> None:
        """Release file handlers explicitly (important on Windows)."""
        for handler in list(self.logger.handlers):
            handler.flush()
            handler.close()
            self.logger.removeHandler(handler)

    def filter_directory(self) -> Path:
        value = self.settings.get(f"filter_directory_{self.game_version()}")
        if not value:
            value = self.settings.get("filter_directory")
        if not value:
            raise ValueError("Configure a pasta de filtros do Path of Exile.")
        return Path(value).expanduser()

    def test_write_permission(self, directory: Path | None = None) -> str:
        target = Path(directory) if directory else self.filter_directory()
        ensure_writable_directory(target)
        self.audit("INFO", "permissions.test", "Permissão de escrita confirmada", {"path": str(target)})
        return f"Permissão de escrita confirmada em {target}"

    def _install_filter(
        self,
        source: Path,
        *,
        base_name: str,
        source_type: str,
        url: str = "",
        require_extension: bool = True,
        destination_directory: Path | None = None,
    ) -> InstallResult:
        source = Path(source).resolve()
        valid, reason = self.editor.validate_file(source, require_extension=require_extension)
        if not valid:
            raise ValueError(reason)
        filter_directory = Path(destination_directory) if destination_directory else self.filter_directory()
        ensure_writable_directory(filter_directory)
        clean_name = safe_stem(base_name or source.stem)
        destination = filter_directory / f"{clean_name}.filter"
        overwrite = self.settings.get_bool("overwrite_existing")

        if destination.exists() and sha256_file(source) != sha256_file(destination):
            if not overwrite:
                raise FileExistsError(
                    f"{destination.name} já existe. Ative 'Sobrescrever filtro existente' ou use outro nome."
                )
            self.backups.create(destination, f"Antes de instalar filtro via {source_type}")

        original = self.paths.originals / f"{clean_name}-{timestamp()}.filter"
        atomic_copy(source, original)
        if not destination.exists() or sha256_file(source) != sha256_file(destination):
            atomic_copy(source, destination)

        history_id: int | None = None
        if self.settings.get_bool("keep_history", True):
            history_id = self.repository.add_history(
                name=destination.name,
                source_type=source_type,
                url=url,
                sound_pack="",
                final_path=destination,
                original_path=original,
                checksum=sha256_file(destination),
            )
        self.settings.set("current_filter_path", str(destination))
        self.settings.set(f"current_filter_path_{self.game_version()}", str(destination))
        self.audit(
            "INFO",
            "filter.installed",
            f"Filtro instalado: {destination.name}",
            {"source": str(source), "destination": str(destination), "validation": reason},
        )
        return InstallResult(destination, original, history_id)

    def import_filter(self, source: Path, base_name: str | None = None) -> InstallResult:
        source = Path(source)
        self.audit("INFO", "filter.import.started", "Importação iniciada", {"source": str(source)})
        return self._install_filter(
            source,
            base_name=base_name or self.settings.get("base_filter_name") or source.stem,
            source_type="import",
        )

    def list_online_filters(self, directory: Path | None = None) -> list[dict[str, str]]:
        target = Path(directory or self.settings.get("online_filter_directory")).expanduser()
        return self.online_filters.list_filters(target)

    def import_online_filter(self, source: Path) -> InstallResult:
        source = Path(source).resolve()
        online_directory = source.parent
        if online_directory.name.lower() != "onlinefilters":
            raise ValueError("Selecione um arquivo dentro da pasta OnlineFilters do Path of Exile 2.")
        valid, reason = self.online_filters.validate(source)
        if not valid:
            raise ValueError(reason)
        metadata = self.online_filters.metadata(source)
        local_filter_directory = online_directory.parent
        self.set_game_version("poe2")
        self.settings.update(
            {
                "online_filter_directory": str(online_directory),
                "filter_directory": str(local_filter_directory),
                "filter_directory_poe2": str(local_filter_directory),
            }
        )
        self.audit(
            "INFO",
            "filter.online.import.started",
            "Importação de filtro online iniciada",
            metadata,
        )
        return self._install_filter(
            source,
            base_name=metadata.get("name") or source.name,
            source_type="online-cache",
            require_extension=False,
            destination_directory=local_filter_directory,
        )

    def download_filter(
        self,
        url: str | None = None,
        base_name: str | None = None,
        progress: Callable[[int], None] | None = None,
    ) -> InstallResult:
        download_url = (url or self.settings.get("download_url")).strip()
        if not download_url:
            raise ValueError("Configure uma URL direta ou use a importação manual.")
        clean_name = safe_stem(base_name or self.settings.get("base_filter_name"))
        temporary_download = self.paths.downloads / f"{clean_name}-{timestamp()}.filter"
        self.audit("INFO", "filter.download.started", "Download iniciado", {"url": download_url})
        self.filterblade.download(download_url, temporary_download, progress)
        result = self._install_filter(
            temporary_download,
            base_name=clean_name,
            source_type="download",
            url=download_url,
        )
        temporary_download.unlink(missing_ok=True)
        self.audit("INFO", "filter.download.finished", "Download finalizado", {"path": str(result.final_path)})
        return result

    def current_filter(self) -> Path:
        game_version = self.game_version()
        saved = self.settings.get(f"current_filter_path_{game_version}")
        if not saved:
            saved = self.settings.get("current_filter_path")
        path = Path(saved).expanduser()
        if not str(path) or not path.is_file():
            candidates = sorted(self.filter_directory().glob("*.filter")) if self.filter_directory().is_dir() else []
            if not candidates:
                raise FileNotFoundError("Nenhum filtro ativo foi encontrado. Baixe ou importe um filtro primeiro.")
            path = candidates[0]
            self.settings.set("current_filter_path", str(path))
            self.settings.set(f"current_filter_path_{game_version}", str(path))
        return path

    def read_filter(self, path: Path | None = None) -> str:
        content, _ = read_text_flexible(path or self.current_filter())
        return content

    def validate_filter(self, path: Path | None = None) -> str:
        target = Path(path) if path else self.current_filter()
        valid, reason = self.editor.validate_file(target)
        self.audit("INFO" if valid else "WARNING", "filter.validated", reason, {"path": str(target)})
        if not valid:
            raise ValueError(reason)
        return reason

    def save_sound_mappings(
        self, pack_name: str, source_directory: str, mappings: list[SoundMapping]
    ) -> None:
        self.repository.save_mappings(pack_name, source_directory, mappings)
        self.settings.update(
            {"active_sound_pack": pack_name, "sound_source_directory": source_directory}
        )
        self.audit(
            "INFO",
            "sounds.mappings.saved",
            f"Mapeamentos salvos para {pack_name}",
            {"active": sum(mapping.active for mapping in mappings)},
        )

    def apply_sounds(self, progress: Callable[[int], None] | None = None) -> ApplyResult:
        filter_path = self.current_filter()
        filter_directory = self.filter_directory()
        if filter_path.parent.resolve() != filter_directory.resolve():
            raise ValueError("O filtro ativo precisa estar na pasta configurada do Path of Exile.")
        ensure_writable_directory(filter_directory)

        pack_name = self.settings.get("active_sound_pack", "Padrão")
        game_version = self.game_version()
        mappings = self.repository.get_mappings(pack_name, game_version)
        active_mappings = [mapping for mapping in mappings if mapping.active]
        if not active_mappings:
            raise ValueError("Ative ao menos um mapeamento de som.")
        source_directory = Path(self.settings.get("sound_source_directory")).expanduser()
        if progress:
            progress(5)
        sources = self.sounds.resolve_mapping_sources(source_directory, active_mappings)
        if progress:
            progress(20)

        original_snapshot = self.paths.originals / f"{safe_stem(filter_path.stem)}-pre-sounds-{timestamp()}.filter"
        atomic_copy(filter_path, original_snapshot)
        backup_path = self.backups.create(filter_path, f"Antes de aplicar pacote {pack_name}")
        if progress:
            progress(35)

        copied, references = self.sounds.copy_mapped_sounds(
            sources,
            filter_directory,
            self.settings.get("sound_subdirectory", "ExileFilterStudio"),
            self.settings.get_bool("overwrite_existing"),
        )
        mapped_for_editor = [
            SoundMapping(
                category=mapping.category,
                sound_path=references.get(mapping.category, ""),
                active=mapping.active,
                optional=mapping.optional,
            )
            for mapping in active_mappings
        ]
        if progress:
            progress(55)

        original_content = self.read_filter(filter_path)
        edit_result = self.editor.apply_mappings(
            original_content,
            mapped_for_editor,
            game_version=game_version,
            managed_sound_prefixes=(
                self.settings.get("sound_subdirectory", "ExileFilterStudio"),
                "ExileFilterStudio",
            ),
        )
        if not edit_result.changes:
            raise ValueError(
                "Nenhum bloco do filtro corresponde aos mapeamentos ativos. O original foi preservado."
            )
        modified_path = self.paths.modified / f"{safe_stem(filter_path.stem)}-{timestamp()}.filter"
        atomic_write_text(modified_path, edit_result.content)
        if progress:
            progress(75)
        atomic_write_text(filter_path, edit_result.content)

        report_path = self.reports.create(
            filter_path,
            pack_name,
            edit_result.changes,
            copied,
            edit_result.unmatched_categories,
        )
        if self.settings.get_bool("keep_history", True):
            self.repository.add_history(
                name=filter_path.name,
                source_type="sounds",
                url="",
                sound_pack=pack_name,
                final_path=filter_path,
                original_path=original_snapshot,
                modified_path=modified_path,
                checksum=sha256_file(filter_path),
            )
        self.audit(
            "INFO",
            "sounds.applied",
            f"Pacote {pack_name} aplicado em {len(edit_result.changes)} bloco(s)",
            {
                "filter": str(filter_path),
                "copied_sounds": [str(path) for path in copied],
                "report": str(report_path),
            },
        )
        if progress:
            progress(100)
        return ApplyResult(
            final_path=filter_path,
            original_path=original_snapshot,
            modified_path=modified_path,
            backup_path=backup_path,
            copied_sounds=copied,
            changes=edit_result.changes,
            report_path=report_path,
        )

    def restore_backup(self, backup_path: Path, destination: Path | None = None) -> Path:
        target = Path(destination) if destination else self.current_filter()
        restored = self.backups.restore(Path(backup_path), target)
        self.settings.set("current_filter_path", str(restored))
        self.settings.set(f"current_filter_path_{self.game_version()}", str(restored))
        self.audit(
            "INFO", "backup.restored", "Backup restaurado", {"backup": str(backup_path), "target": str(target)}
        )
        return restored

    def remove_history(self, history_id: int) -> None:
        self.repository.delete_history(history_id)
        self.audit("INFO", "history.removed", "Registro de histórico removido", {"id": history_id})

    def export_share_zip(
        self,
        destination: Path,
        progress: Callable[[int], None] | None = None,
    ) -> ExportResult:
        filter_path = self.current_filter()
        result = self.exporter.create_share_zip(filter_path, destination, progress)
        self.audit(
            "INFO",
            "filter.share.exported",
            f"Pacote de compartilhamento criado com {result.sound_count} som(ns)",
            {
                "filter": str(filter_path),
                "zip": str(result.zip_path),
                "game": self.game_version(),
            },
        )
        return result
