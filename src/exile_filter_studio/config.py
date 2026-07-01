from __future__ import annotations

import os
import platform
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "Exile Filter Studio"
APP_SLUG = "exile-filter-studio"


@dataclass(frozen=True, slots=True)
class AppPaths:
    root: Path
    database: Path
    logs: Path
    originals: Path
    modified: Path
    backups: Path
    reports: Path
    downloads: Path

    @classmethod
    def create(cls) -> "AppPaths":
        override = os.getenv("EXILE_FILTER_STUDIO_HOME")
        if override:
            root = Path(override).expanduser()
        elif platform.system() == "Windows":
            root = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME
        else:
            root = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_SLUG

        paths = cls(
            root=root,
            database=root / "studio.db",
            logs=root / "logs",
            originals=root / "filters" / "originals",
            modified=root / "filters" / "modified",
            backups=root / "backups",
            reports=root / "reports",
            downloads=root / "downloads",
        )
        for directory in (
            paths.root,
            paths.logs,
            paths.originals,
            paths.modified,
            paths.backups,
            paths.reports,
            paths.downloads,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        return paths


def detect_poe_filter_directory(game_version: str | None = None) -> Path:
    """Return the most likely local item-filter directory without creating it."""
    home = Path.home()
    if platform.system() == "Windows":
        names = (
            ["Path of Exile 2"]
            if game_version == "poe2"
            else ["Path of Exile"]
            if game_version == "poe1"
            else ["Path of Exile 2", "Path of Exile"]
        )
        candidates = [home / "Documents" / "My Games" / name for name in names]
        user_profile = os.getenv("USERPROFILE")
        if user_profile:
            candidates.extend(Path(user_profile) / "Documents" / "My Games" / name for name in names)
    else:
        proton_tail = Path(
            "steamapps/compatdata/238960/pfx/drive_c/users/steamuser/Documents/My Games/Path of Exile"
        )
        candidates = []
        if game_version != "poe2":
            candidates.extend(
                [
                    home / ".local/share/Steam" / proton_tail,
                    home / ".steam/steam" / proton_tail,
                    home / ".steam/debian-installation" / proton_tail,
                ]
            )
        if game_version != "poe1":
            candidates.append(home / "Documents/My Games/Path of Exile 2")
        if game_version != "poe2":
            candidates.append(home / "Documents/My Games/Path of Exile")

    return next((path for path in candidates if path.is_dir()), candidates[0])


def detect_online_filter_directory() -> Path:
    """Return the usual PoE 2 online-filter cache directory."""
    home = Path.home()
    candidates = [home / "Documents" / "My Games" / "Path of Exile 2" / "OnlineFilters"]
    user_profile = os.getenv("USERPROFILE")
    if user_profile:
        candidates.append(
            Path(user_profile) / "Documents" / "My Games" / "Path of Exile 2" / "OnlineFilters"
        )
    return next((path for path in candidates if path.is_dir()), candidates[0])


DEFAULT_SETTINGS: dict[str, str] = {
    "game_version": "poe2",
    "filter_directory": str(detect_poe_filter_directory("poe2")),
    "filter_directory_poe1": str(detect_poe_filter_directory("poe1")),
    "filter_directory_poe2": str(detect_poe_filter_directory("poe2")),
    "online_filter_directory": str(detect_online_filter_directory()),
    "download_url": "",
    "base_filter_name": "MeuFiltro",
    "sound_source_directory": "",
    "sound_subdirectory": "ExileFilterStudio",
    "backup_before_apply": "1",
    "overwrite_existing": "0",
    "validate_sounds": "1",
    "keep_history": "1",
    "use_optional_sounds": "1",
    "theme": "dark",
    "current_filter_path": "",
    "current_filter_path_poe1": "",
    "current_filter_path_poe2": "",
    "active_sound_pack": "Padrão",
}
