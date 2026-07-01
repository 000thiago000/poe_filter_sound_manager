from __future__ import annotations

import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from exile_filter_studio.services.export_service import ExportService  # noqa: E402


class ExportServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.sound_directory = self.root / "ExileFilterStudio"
        self.sound_directory.mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_creates_self_contained_zip_with_opaque_sound_names(self) -> None:
        first = self.sound_directory / "quantos_viados.mp3"
        second = self.sound_directory / "spoiler_da_voz.wav"
        first.write_bytes(b"ID3-secret-audio")
        second.write_bytes(b"RIFF-secret-audio")
        filter_path = self.root / "MeuFiltro.filter"
        original = """Show
    CustomAlertSound "ExileFilterStudio/quantos_viados.mp3" 300
    Class "Stackable Currency"

Show
    CustomAlertSoundOptional "ExileFilterStudio/spoiler_da_voz.wav" 300
    Class "Waystones"
"""
        filter_path.write_text(original, encoding="utf-8")
        destination = self.root / "Surpresa.zip"

        result = ExportService().create_share_zip(filter_path, destination)

        self.assertEqual(2, result.sound_count)
        self.assertEqual(original, filter_path.read_text(encoding="utf-8"))
        with zipfile.ZipFile(destination) as archive:
            names = archive.namelist()
            sound_names = [name for name in names if name.startswith("sounds/")]
            self.assertEqual(2, len(sound_names))
            self.assertTrue(all(Path(name).name.startswith("asset_") for name in sound_names))
            self.assertNotIn("quantos_viados", "\n".join(names))
            self.assertNotIn("spoiler_da_voz", "\n".join(names))
            bundled_filter = archive.read("Surpresa.filter").decode("utf-8")
            self.assertNotIn("quantos_viados", bundled_filter)
            self.assertNotIn("spoiler_da_voz", bundled_filter)
            self.assertEqual(2, bundled_filter.count('CustomAlertSound'))
            self.assertEqual({b"ID3-secret-audio", b"RIFF-secret-audio"}, {archive.read(name) for name in sound_names})

    def test_reuses_one_opaque_file_for_repeated_reference(self) -> None:
        sound = self.sound_directory / "same.mp3"
        sound.write_bytes(b"same-audio")
        filter_path = self.root / "Repeated.filter"
        filter_path.write_text(
            """Show
    CustomAlertSound "ExileFilterStudio/same.mp3" 300
    Class "Omen"
Show
    CustomAlertSound "ExileFilterStudio/same.mp3" 300
    Class "Waystones"
""",
            encoding="utf-8",
        )
        destination = self.root / "Repeated.zip"
        result = ExportService().create_share_zip(filter_path, destination)
        self.assertEqual(1, result.sound_count)
        with zipfile.ZipFile(destination) as archive:
            self.assertEqual(1, len([name for name in archive.namelist() if name.startswith("sounds/")]))

    def test_refuses_missing_referenced_sound(self) -> None:
        filter_path = self.root / "Broken.filter"
        filter_path.write_text(
            'Show\n    CustomAlertSound "ExileFilterStudio/missing.mp3" 300\n',
            encoding="utf-8",
        )
        with self.assertRaises(FileNotFoundError):
            ExportService().create_share_zip(filter_path, self.root / "Broken.zip")


if __name__ == "__main__":
    unittest.main()

