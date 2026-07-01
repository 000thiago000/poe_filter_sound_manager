from __future__ import annotations

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from exile_filter_studio.models import SoundMapping  # noqa: E402
from exile_filter_studio.services.filter_editor import FilterEditor  # noqa: E402


SAMPLE_FILTER = """# Sample filter
Show # HIGH VALUE
    Class "Stackable Currency"
    BaseType "Divine Orb"
    PlayAlertSound 6 300

Show
    Class "Stackable Currency"
    BaseType "Orb of Alteration"
    CustomAlertSound "old.mp3" 100

Show
    Class "Divination Cards"
    SetFontSize 40

Show
    Rarity Unique
    SetBorderColor 255 100 0
"""


class FilterEditorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.editor = FilterEditor()

    def test_validates_and_counts_blocks(self) -> None:
        valid, message = self.editor.validate_content(SAMPLE_FILTER)
        self.assertTrue(valid)
        self.assertIn("4 bloco", message)

    def test_rejects_html(self) -> None:
        valid, _ = self.editor.validate_content("<html><body>Show me</body></html>")
        self.assertFalse(valid)

    def test_classifies_priority_categories(self) -> None:
        _, blocks = self.editor.parse_blocks(SAMPLE_FILTER)
        self.assertEqual("High Value Items", self.editor.classify_block(blocks[0].text))
        self.assertEqual("Currency", self.editor.classify_block(blocks[1].text))
        self.assertEqual("Divination Cards", self.editor.classify_block(blocks[2].text))
        self.assertEqual("Unique Items", self.editor.classify_block(blocks[3].text))

    def test_applies_custom_sounds_and_removes_builtin_alert(self) -> None:
        result = self.editor.apply_mappings(
            SAMPLE_FILTER,
            [
                SoundMapping("High Value Items", "Audio/high.mp3", True, True),
                SoundMapping("Currency", "Audio/currency.wav", True, False),
            ],
        )
        self.assertEqual(2, len(result.changes))
        self.assertIn('CustomAlertSoundOptional "Audio/high.mp3" 300', result.content)
        self.assertNotIn("PlayAlertSound 6 300", result.content)
        self.assertIn('CustomAlertSound "Audio/currency.wav" 300', result.content)
        self.assertNotIn('CustomAlertSound "old.mp3"', result.content)

    def test_replaces_all_alert_commands_in_poe2_currency_block(self) -> None:
        content = """Show # $type->currency $tier->s !apex_stier
    Class == "Incubators" "Stackable Currency"
    BaseType == "Divine Orb" "Mirror of Kalandra"
    PlayAlertSound 6 300
    PlayEffect Red
"""
        result = self.editor.apply_mappings(
            content,
            [SoundMapping("High Value Items", "ExileFilterStudio/quantos_viados.mp3", True, False)],
            game_version="poe2",
        )
        self.assertIn(
            'CustomAlertSound "ExileFilterStudio/quantos_viados.mp3" 300', result.content
        )
        self.assertNotIn("PlayAlertSound 6 300", result.content)
        self.assertEqual(
            ["PlayAlertSound 6 300"], result.changes[0].replaced_commands
        )

    def test_does_not_duplicate_custom_sound_on_second_application(self) -> None:
        mappings = [SoundMapping("Currency", "Audio/currency.wav", True, True)]
        once = self.editor.apply_mappings(SAMPLE_FILTER, mappings).content
        twice = self.editor.apply_mappings(once, mappings).content
        currency_commands = [
            line for line in twice.splitlines() if 'CustomAlertSoundOptional "Audio/currency.wav"' in line
        ]
        self.assertEqual(1, len(currency_commands))

    def test_classifies_poe2_only_categories(self) -> None:
        cases = {
            "Waystones": 'Show # $type->waystones\n    Class == "Waystones"\n',
            "Tablets": 'Show\n    Class "Map Fragments" "Tablet"\n',
            "Omens": 'Show # $type->endgame->omen\n    Class == "Omen"\n',
            "Runes & Soul Cores": 'Show # $type->sockets->general\n    Class == "Augment"\n',
            "Gems & Uncut Gems": 'Show # $type->gems->uncut\n    BaseType "Uncut Skill Gem"\n',
            "Charms": 'Show\n    Class == "Charms"\n',
            "Fragments & Keys": 'Show\n    Class == "Pinnacle Keys"\n',
            "Expedition Logbooks": 'Show\n    Class == "Expedition Logbook"\n',
            "Relics": 'Show # $type->relics->generic\n    BaseType "Amphora Relic"\n',
        }
        for expected, block in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(expected, self.editor.classify_block(block, "poe2"))

    def test_poe2_waystones_do_not_use_poe1_maps_mapping(self) -> None:
        content = 'Show # $type->waystones\n    Class == "Waystones"\n    WaystoneTier >= 10\n'
        result = self.editor.apply_mappings(
            content,
            [SoundMapping("Waystones", "Audio/waystone.wav", True, True)],
            game_version="poe2",
        )
        self.assertIn('CustomAlertSoundOptional "Audio/waystone.wav" 300', result.content)

    def test_trailing_high_value_section_does_not_contaminate_previous_block(self) -> None:
        rare_block = """Show # $type->decorators->rareeg $tier->corruptedraresimplicit !exotics_corrupthigh
    AnyEnchantment True
    Corrupted True
    Rarity Rare
    Class == "Amulets" "Belts" "Body Armours"
    AreaLevel >= 65
    Continue

# [1102] Additional High Value Rules
# Mirror of Kalandra rules below
"""
        jewellery_block = """Show # $type->endgame->normalcraft->decorator $tier->normaldecoratorjwlry !gear_unstyled
    Mirrored False
    Corrupted False
    Rarity Normal Magic
    Class == "Amulets" "Rings"
    AreaLevel >= 65
    Continue

# Additional High Value Rules
"""
        self.assertIsNone(self.editor.classify_block(rare_block, "poe2"))
        self.assertIsNone(self.editor.classify_block(jewellery_block, "poe2"))

    def test_removes_stale_managed_sound_from_block_outside_mapping(self) -> None:
        content = """Show # $type->decorators->rareeg $tier->corruptedraresimplicit
    CustomAlertSound "ExileFilterStudio/old_wrong_sound.mp3" 300
    AnyEnchantment True
    Corrupted True
    Rarity Rare
    Continue

# Additional High Value Rules

Show # $type->currency $tier->s
    Class == "Stackable Currency"
    BaseType == "Divine Orb" "Mirror of Kalandra"
    PlayAlertSound 6 300
"""
        result = self.editor.apply_mappings(
            content,
            [SoundMapping("High Value Items", "ExileFilterStudio/right.mp3", True, False)],
            game_version="poe2",
            managed_sound_prefixes=("ExileFilterStudio",),
        )
        self.assertNotIn("old_wrong_sound.mp3", result.content)
        self.assertEqual(1, result.content.count("CustomAlertSound"))
        self.assertIn('CustomAlertSound "ExileFilterStudio/right.mp3" 300', result.content)
        self.assertTrue(
            any(change.category == "Limpeza fora do mapeamento" for change in result.changes)
        )


if __name__ == "__main__":
    unittest.main()
