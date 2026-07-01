from __future__ import annotations

from pathlib import Path

from exile_filter_studio.services.file_utils import read_text_flexible
from exile_filter_studio.services.filter_editor import FilterEditor


class OnlineFilterService:
    """Reads PoE 2's local OnlineFilters cache without modifying it."""

    HEADER_LIMIT = 40
    MAX_FILTER_BYTES = 20 * 1024 * 1024

    @staticmethod
    def metadata(path: Path) -> dict[str, str]:
        target = Path(path)
        content, _ = read_text_flexible(target)
        values: dict[str, str] = {
            "id": target.name,
            "name": target.name,
            "version": "—",
            "realm": "—",
            "filterVersion": "—",
        }
        first_lines = content.splitlines()[: OnlineFilterService.HEADER_LIMIT]
        if not first_lines or first_lines[0].strip().lower() != "#online item filter":
            raise ValueError(f"{target.name} não possui um cabeçalho de filtro online do Path of Exile.")
        for line in first_lines[1:]:
            if not line.startswith("#") or ":" not in line:
                continue
            key, value = line[1:].split(":", 1)
            key = key.strip()
            if key in values:
                values[key] = value.strip() or "—"
        values["path"] = str(target)
        return values

    def list_filters(self, directory: Path) -> list[dict[str, str]]:
        root = Path(directory).expanduser()
        if not root.is_dir():
            return []
        filters: list[dict[str, str]] = []
        for path in sorted(root.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
            if not path.is_file() or path.stat().st_size > self.MAX_FILTER_BYTES:
                continue
            try:
                values = self.metadata(path)
                values["modified"] = str(path.stat().st_mtime_ns)
                filters.append(values)
            except (OSError, UnicodeError, ValueError):
                continue
        return filters

    def validate(self, path: Path) -> tuple[bool, str]:
        self.metadata(path)
        return FilterEditor.validate_file(Path(path), require_extension=False)

