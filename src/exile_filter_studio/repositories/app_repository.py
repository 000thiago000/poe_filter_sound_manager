from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from exile_filter_studio.database import Database
from exile_filter_studio.models import CATEGORIES, SoundMapping, categories_for_game


class AppRepository:
    def __init__(self, database: Database):
        self.database = database

    def log(self, level: str, event: str, message: str, details: Any = "") -> int:
        detail_text = details if isinstance(details, str) else json.dumps(details, ensure_ascii=False)
        with self.database.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO logs(level, event, message, details) VALUES (?, ?, ?, ?)",
                (level.upper(), event, message, detail_text),
            )
            return int(cursor.lastrowid)

    def list_logs(self, limit: int = 500) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def clear_logs(self) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM logs")

    def add_history(
        self,
        *,
        name: str,
        source_type: str,
        url: str,
        sound_pack: str,
        final_path: Path,
        original_path: Path,
        modified_path: Path | None = None,
        checksum: str = "",
    ) -> int:
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO filter_history(
                    name, source_type, url, sound_pack, final_path,
                    original_path, modified_path, checksum
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    source_type,
                    url,
                    sound_pack,
                    str(final_path),
                    str(original_path),
                    str(modified_path or ""),
                    checksum,
                ),
            )
            return int(cursor.lastrowid)

    def list_history(self, limit: int = 250) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM filter_history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_history(self, history_id: int) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM filter_history WHERE id = ?", (history_id,))

    def add_backup(self, filter_name: str, backup_path: Path, original_path: Path, reason: str) -> int:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "INSERT INTO backups(filter_name, backup_path, original_path, reason) VALUES (?, ?, ?, ?)",
                (filter_name, str(backup_path), str(original_path), reason),
            )
            return int(cursor.lastrowid)

    def list_backups(self, limit: int = 250) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM backups ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_backup(self, backup_id: int) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM backups WHERE id = ?", (backup_id,))

    def ensure_sound_pack(self, name: str, directory: str = "") -> int:
        clean_name = name.strip() or "Padrão"
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO sound_packs(name, directory) VALUES (?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    directory = CASE WHEN excluded.directory <> '' THEN excluded.directory ELSE directory END,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (clean_name, directory),
            )
            row = connection.execute(
                "SELECT id FROM sound_packs WHERE name = ?", (clean_name,)
            ).fetchone()
            pack_id = int(row["id"])
            connection.executemany(
                "INSERT OR IGNORE INTO sound_mappings(sound_pack_id, category) VALUES (?, ?)",
                [(pack_id, category) for category in CATEGORIES],
            )
        return pack_id

    def list_sound_packs(self) -> list[dict[str, Any]]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM sound_packs ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def get_mappings(self, pack_name: str, game_version: str = "poe1") -> list[SoundMapping]:
        pack_id = self.ensure_sound_pack(pack_name)
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT category, sound_path, active, optional
                FROM sound_mappings WHERE sound_pack_id = ?
                """,
                (pack_id,),
            ).fetchall()
        by_category = {
            str(row["category"]): SoundMapping(
                category=str(row["category"]),
                sound_path=str(row["sound_path"]),
                active=bool(row["active"]),
                optional=bool(row["optional"]),
            )
            for row in rows
        }
        return [
            by_category.get(category, SoundMapping(category))
            for category in categories_for_game(game_version)
        ]

    def save_mappings(self, pack_name: str, directory: str, mappings: list[SoundMapping]) -> None:
        pack_id = self.ensure_sound_pack(pack_name, directory)
        with self.database.connect() as connection:
            connection.executemany(
                """
                INSERT INTO sound_mappings(sound_pack_id, category, sound_path, active, optional)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(sound_pack_id, category) DO UPDATE SET
                    sound_path = excluded.sound_path,
                    active = excluded.active,
                    optional = excluded.optional
                """,
                [
                    (pack_id, mapping.category, mapping.sound_path, int(mapping.active), int(mapping.optional))
                    for mapping in mappings
                ],
            )

    def delete_sound_pack(self, pack_name: str) -> None:
        if pack_name == "Padrão":
            raise ValueError("O pacote Padrão não pode ser removido.")
        with self.database.connect() as connection:
            connection.execute("DELETE FROM sound_packs WHERE name = ?", (pack_name,))
