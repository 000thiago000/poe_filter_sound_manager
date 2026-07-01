from __future__ import annotations

from exile_filter_studio.config import DEFAULT_SETTINGS
from exile_filter_studio.database import Database


class SettingsRepository:
    def __init__(self, database: Database):
        self.database = database
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        with self.database.connect() as connection:
            connection.executemany(
                "INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)",
                DEFAULT_SETTINGS.items(),
            )

    def get(self, key: str, default: str = "") -> str:
        with self.database.connect() as connection:
            row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return str(row["value"]) if row else default

    def get_bool(self, key: str, default: bool = False) -> bool:
        return self.get(key, "1" if default else "0") in {"1", "true", "True", "yes"}

    def set(self, key: str, value: str | bool | int) -> None:
        normalized = "1" if value is True else "0" if value is False else str(value)
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO settings(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """,
                (key, normalized),
            )

    def update(self, values: dict[str, str | bool | int]) -> None:
        with self.database.connect() as connection:
            connection.executemany(
                """
                INSERT INTO settings(key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """,
                [
                    (key, "1" if value is True else "0" if value is False else str(value))
                    for key, value in values.items()
                ],
            )

    def all(self) -> dict[str, str]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT key, value FROM settings").fetchall()
        return {str(row["key"]): str(row["value"]) for row in rows}

