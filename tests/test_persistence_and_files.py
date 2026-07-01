from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from exile_filter_studio.database import Database  # noqa: E402
from exile_filter_studio.models import SoundMapping  # noqa: E402
from exile_filter_studio.repositories.app_repository import AppRepository  # noqa: E402
from exile_filter_studio.repositories.settings_repository import SettingsRepository  # noqa: E402
from exile_filter_studio.services.file_utils import atomic_write_text, sha256_file  # noqa: E402
from exile_filter_studio.services.sound_service import SoundService  # noqa: E402


class PersistenceAndFileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = Database(self.root / "test.db")
        self.database.initialize()
        self.settings = SettingsRepository(self.database)
        self.repository = AppRepository(self.database)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_settings_round_trip(self) -> None:
        self.settings.update({"overwrite_existing": True, "base_filter_name": "Teste"})
        self.assertTrue(self.settings.get_bool("overwrite_existing"))
        self.assertEqual("Teste", self.settings.get("base_filter_name"))

    def test_sound_pack_round_trip(self) -> None:
        mappings = [SoundMapping("Currency", "ding.wav", True, False)]
        self.repository.save_mappings("Meu Pack", str(self.root), mappings)
        loaded = {item.category: item for item in self.repository.get_mappings("Meu Pack")}
        self.assertTrue(loaded["Currency"].active)
        self.assertEqual("ding.wav", loaded["Currency"].sound_path)
        self.assertFalse(loaded["Currency"].optional)

    def test_atomic_write_and_sound_copy(self) -> None:
        source_dir = self.root / "source"
        game_dir = self.root / "game"
        source_dir.mkdir()
        game_dir.mkdir()
        sound = source_dir / "ding.wav"
        sound.write_bytes(b"RIFF-test")
        service = SoundService()
        sources = service.resolve_mapping_sources(
            source_dir, [SoundMapping("Currency", "ding.wav", True, True)]
        )
        copied, references = service.copy_mapped_sounds(
            sources, game_dir, "ExileFilterStudio", overwrite=False
        )
        self.assertEqual("ExileFilterStudio/ding.wav", references["Currency"])
        self.assertEqual(sha256_file(sound), sha256_file(copied[0]))
        target = game_dir / "test.filter"
        atomic_write_text(target, "Show\n    Class Currency\n")
        self.assertTrue(target.read_text(encoding="utf-8").startswith("Show"))

    def test_rejects_mapping_outside_sound_pack(self) -> None:
        source_dir = self.root / "source"
        source_dir.mkdir()
        outside = self.root / "outside.wav"
        outside.write_bytes(b"RIFF")
        with self.assertRaises(ValueError):
            SoundService().resolve_mapping_sources(
                source_dir, [SoundMapping("Currency", str(outside), True, True)]
            )


if __name__ == "__main__":
    unittest.main()

