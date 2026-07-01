from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


GAME_LABELS: dict[str, str] = {
    "poe1": "Path of Exile 1",
    "poe2": "Path of Exile 2",
}

POE1_CATEGORIES: tuple[str, ...] = (
    "High Value Items",
    "Currency",
    "Divination Cards",
    "Unique Items",
    "Maps",
    "Scarabs",
    "Essences",
    "Fragments",
    "Gems",
)

POE2_CATEGORIES: tuple[str, ...] = (
    "High Value Items",
    "Currency",
    "Unique Items",
    "Waystones",
    "Tablets",
    "Omens",
    "Runes & Soul Cores",
    "Gems & Uncut Gems",
    "Charms",
    "Fragments & Keys",
    "Expedition Logbooks",
    "Relics",
)

CATEGORIES_BY_GAME: dict[str, tuple[str, ...]] = {
    "poe1": POE1_CATEGORIES,
    "poe2": POE2_CATEGORIES,
}

# União usada apenas para inicializar a persistência; a UI usa o catálogo do jogo ativo.
CATEGORIES: tuple[str, ...] = tuple(dict.fromkeys(POE1_CATEGORIES + POE2_CATEGORIES))


def categories_for_game(game_version: str) -> tuple[str, ...]:
    return CATEGORIES_BY_GAME.get(game_version, POE1_CATEGORIES)


@dataclass(slots=True)
class SoundMapping:
    category: str
    sound_path: str = ""
    active: bool = False
    optional: bool = True


@dataclass(slots=True)
class FilterChange:
    category: str
    block_line: int
    sound_reference: str
    replaced_commands: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EditResult:
    content: str
    changes: list[FilterChange]
    unmatched_categories: list[str]


@dataclass(slots=True)
class InstallResult:
    final_path: Path
    original_path: Path
    history_id: int | None


@dataclass(slots=True)
class ApplyResult:
    final_path: Path
    original_path: Path
    modified_path: Path
    backup_path: Path
    copied_sounds: list[Path]
    changes: list[FilterChange]
    report_path: Path


@dataclass(slots=True)
class ExportResult:
    zip_path: Path
    filter_name: str
    sound_count: int
