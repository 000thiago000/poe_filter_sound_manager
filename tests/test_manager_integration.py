from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from exile_filter_studio.config import AppPaths  # noqa: E402
from exile_filter_studio.manager import ApplicationManager  # noqa: E402
from exile_filter_studio.models import SoundMapping  # noqa: E402


class ManagerIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        os.environ["EXILE_FILTER_STUDIO_HOME"] = str(self.root / "app-data")
        self.game = self.root / "game"
        self.sounds = self.root / "sounds"
        self.game.mkdir()
        self.sounds.mkdir()
        self.manager = ApplicationManager(AppPaths.create())
        self.manager.settings.update(
            {
                "game_version": "poe1",
                "filter_directory": str(self.game),
                "filter_directory_poe1": str(self.game),
                "filter_directory_poe2": str(self.game),
                "sound_source_directory": str(self.sounds),
                "base_filter_name": "Integration",
                "sound_subdirectory": "StudioSounds",
                "overwrite_existing": False,
            }
        )

    def tearDown(self) -> None:
        self.manager.close()
        os.environ.pop("EXILE_FILTER_STUDIO_HOME", None)
        self.temp.cleanup()

    def test_import_apply_report_and_restore(self) -> None:
        source = self.root / "source.filter"
        source.write_text(
            '# integration\nShow\n    Class "Stackable Currency"\n    PlayAlertSound 2 100\n',
            encoding="utf-8",
        )
        sound = self.sounds / "currency.wav"
        sound.write_bytes(b"RIFF-test-sound")
        installed = self.manager.import_filter(source)
        self.assertTrue(installed.final_path.is_file())

        self.manager.save_sound_mappings(
            "Integration Pack",
            str(self.sounds),
            [SoundMapping("Currency", "currency.wav", True, True)],
        )
        result = self.manager.apply_sounds()
        updated = result.final_path.read_text(encoding="utf-8")
        self.assertIn('CustomAlertSoundOptional "StudioSounds/currency.wav" 300', updated)
        self.assertTrue(result.backup_path.is_file())
        self.assertTrue(result.modified_path.is_file())
        self.assertTrue(result.report_path.is_file())
        self.assertTrue((self.game / "StudioSounds" / "currency.wav").is_file())
        self.assertEqual(2, len(self.manager.repository.list_history()))

        self.manager.restore_backup(result.backup_path)
        restored = result.final_path.read_text(encoding="utf-8")
        self.assertNotIn("CustomAlertSoundOptional", restored)
        self.assertIn("PlayAlertSound 2 100", restored)

    def test_imports_extensionless_poe2_online_filter_without_changing_cache(self) -> None:
        online_directory = self.root / "Path of Exile 2" / "OnlineFilters"
        online_directory.mkdir(parents=True)
        cached = online_directory / "nN3jOauR"
        original = (
            "#Online Item Filter\n"
            "#name:NeverSink-4verystr-PoE2\n"
            "#version:4.5.0\n"
            "#realm:poe2\n"
            "#filterVersion:0.10.3\n"
            "Show\n"
            '    Class "Stackable Currency"\n'
        )
        cached.write_text(original, encoding="utf-8")

        listed = self.manager.list_online_filters(online_directory)
        self.assertEqual("NeverSink-4verystr-PoE2", listed[0]["name"])
        result = self.manager.import_online_filter(cached)

        self.assertEqual(online_directory.parent, result.final_path.parent)
        self.assertEqual("NeverSink-4verystr-PoE2.filter", result.final_path.name)
        self.assertEqual(original, cached.read_text(encoding="utf-8"))
        self.assertEqual(str(online_directory.parent), self.manager.settings.get("filter_directory"))
        self.assertEqual("poe2", self.manager.game_version())
        self.assertEqual(
            str(online_directory.parent), self.manager.settings.get("filter_directory_poe2")
        )

    def test_switches_filter_directory_per_game(self) -> None:
        poe1 = self.root / "poe1"
        poe2 = self.root / "poe2"
        poe1.mkdir()
        poe2.mkdir()
        self.manager.settings.update(
            {"filter_directory_poe1": str(poe1), "filter_directory_poe2": str(poe2)}
        )
        self.manager.set_game_version("poe1")
        self.assertEqual(poe1, self.manager.filter_directory())
        self.manager.set_game_version("poe2")
        self.assertEqual(poe2, self.manager.filter_directory())


if __name__ == "__main__":
    unittest.main()
