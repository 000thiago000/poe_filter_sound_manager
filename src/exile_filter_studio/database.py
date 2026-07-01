from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS filter_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    downloaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_type TEXT NOT NULL DEFAULT 'download',
    url TEXT NOT NULL DEFAULT '',
    sound_pack TEXT NOT NULL DEFAULT '',
    final_path TEXT NOT NULL,
    original_path TEXT NOT NULL DEFAULT '',
    modified_path TEXT NOT NULL DEFAULT '',
    checksum TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sound_packs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    directory TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sound_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sound_pack_id INTEGER NOT NULL,
    category TEXT NOT NULL,
    sound_path TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 0,
    optional INTEGER NOT NULL DEFAULT 1,
    UNIQUE(sound_pack_id, category),
    FOREIGN KEY(sound_pack_id) REFERENCES sound_packs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS backups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filter_name TEXT NOT NULL,
    backup_path TEXT NOT NULL UNIQUE,
    original_path TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reason TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,
    event TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_history_date ON filter_history(downloaded_at DESC);
CREATE INDEX IF NOT EXISTS idx_backups_date ON backups(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_logs_date ON logs(created_at DESC);
"""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

