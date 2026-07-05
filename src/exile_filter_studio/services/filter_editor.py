from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from exile_filter_studio.models import EditResult, FilterChange, SoundMapping, categories_for_game
from exile_filter_studio.services.file_utils import read_text_flexible


BLOCK_START = re.compile(r"^\s*(Show|Hide|Minimal)\b", re.IGNORECASE)
SOUND_COMMAND = re.compile(
    r"^\s*(CustomAlertSoundOptional|CustomAlertSound|PlayAlertSoundPositional|PlayAlertSound)\b",
    re.IGNORECASE,
)
CUSTOM_SOUND_REFERENCE = re.compile(
    r'^\s*CustomAlertSound(?:Optional)?\s+"([^"]+)"',
    re.IGNORECASE,
)


@dataclass(slots=True)
class FilterBlock:
    start: int
    end: int
    lines: list[str]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


class FilterEditor:
    MIN_FILTER_LENGTH = 20

    @staticmethod
    def validate_content(content: str) -> tuple[bool, str]:
        if "\x00" in content:
            return False, "O arquivo contém bytes nulos e não parece ser texto."
        if len(content.strip()) < FilterEditor.MIN_FILTER_LENGTH:
            return False, "O arquivo está vazio ou é curto demais para ser um filtro."
        lowered = content.lstrip().lower()
        if lowered.startswith(("<!doctype html", "<html", "{")):
            return False, "O conteúdo não parece ser um filtro do Path of Exile."
        block_count = sum(1 for line in content.splitlines() if BLOCK_START.match(line))
        if block_count == 0:
            return False, "Nenhum bloco Show, Hide ou Minimal foi encontrado."
        return True, f"Filtro válido: {block_count} bloco(s) encontrado(s)."

    @classmethod
    def validate_file(cls, path: Path, require_extension: bool = True) -> tuple[bool, str]:
        if require_extension and Path(path).suffix.lower() != ".filter":
            return False, "O arquivo precisa ter a extensão .filter."
        if Path(path).stat().st_size > 20 * 1024 * 1024:
            return False, "O filtro excede o limite de 20 MB."
        content, _ = read_text_flexible(path)
        return cls.validate_content(content)

    @staticmethod
    def parse_blocks(content: str) -> tuple[list[str], list[FilterBlock]]:
        lines = content.splitlines()
        starts = [index for index, line in enumerate(lines) if BLOCK_START.match(line)]
        prefix = lines[: starts[0]] if starts else lines
        blocks: list[FilterBlock] = []
        for position, start in enumerate(starts):
            end = starts[position + 1] if position + 1 < len(starts) else len(lines)
            blocks.append(FilterBlock(start=start, end=end, lines=lines[start:end]))
        return prefix, blocks

    @staticmethod
    def classify_block(block_text: str, game_version: str = "poe1") -> str | None:
        lines = block_text.splitlines()
        # Comentários de seção entre duas regras pertencem semanticamente à próxima regra.
        # Mantemos o comentário inline da linha Show, mas ignoramos comentários autônomos.
        rule_lines = [
            line
            for index, line in enumerate(lines)
            if index == 0 or not line.lstrip().startswith("#")
        ]
        text = "\n".join(rule_lines).lower()

        high_markers = (
            "high value",
            "highest value",
            "mirror of kalandra",
            "divine orb",
            "headhunter",
            "mageblood",
            "squire",
            "t0 unique",
            "tier 0",
            "tier-0",
        )
        if any(marker in text for marker in high_markers):
            return "High Value Items"

        if re.search(r"^\s*rarity\s+(?:==?\s*)?unique\b", text, re.MULTILINE):
            return "Unique Items"

        if game_version == "poe2":
            if re.search(r"^\s*(waystonetier)\b", text, re.MULTILINE) or re.search(
                r"^\s*class\s+.*\bwaystones?\b", text, re.MULTILINE
            ):
                return "Waystones"
            if re.search(r"^\s*class\s+.*\btablet\b", text, re.MULTILINE):
                return "Tablets"
            if re.search(r"^\s*class\s+(?:==?\s*)?[\"']?omen[\"']?\s*$", text, re.MULTILINE):
                return "Omens"
            if "$type->sockets" in text or "soul core" in text or re.search(
                r"^\s*basetype\s+.*\brune\b", text, re.MULTILINE
            ):
                return "Runes & Soul Cores"
            if (
                "$type->gems" in text
                or "uncut skill gem" in text
                or "uncut spirit gem" in text
                or re.search(r"^\s*class\s+.*(?:skill gems|support gems)", text, re.MULTILINE)
            ):
                return "Gems & Uncut Gems"
            if re.search(r"^\s*class\s+(?:==?\s*)?.*\bcharms?\b", text, re.MULTILINE):
                return "Charms"
            if re.search(
                r"^\s*class\s+.*(?:map fragments|vault keys|pinnacle keys)", text, re.MULTILINE
            ):
                return "Fragments & Keys"
            if re.search(r"^\s*class\s+.*expedition logbook", text, re.MULTILINE):
                return "Expedition Logbooks"
            if "$type->relics" in text:
                return "Relics"
            if re.search(r"^\s*class\s+.*currency", text, re.MULTILINE):
                return "Currency"
            return None

        show_line = rule_lines[0].lower() if rule_lines else ""
        has_currency_class = bool(
            re.search(r"^\s*class\s+.*currency", text, re.MULTILINE)
        )
        has_fragment_class = bool(
            re.search(r"^\s*class\s+.*(?:map fragments|misc map items)", text, re.MULTILINE)
        )
        if "$type->fragments->scarabs" in show_line or (
            has_fragment_class
            and re.search(r"^\s*basetype\s+.*\bscarab\b", text, re.MULTILINE)
        ):
            return "Scarabs"
        if (
            "$type->currency->essence" in show_line
            or "$tier->essence" in show_line
            or re.search(r"^\s*class\s+.*\bessences?\b", text, re.MULTILINE)
            or (
                has_currency_class
                and re.search(
                    r"^\s*basetype\s+.*(?:\bessence of\b|\bremnant of corruption\b)",
                    text,
                    re.MULTILINE,
                )
            )
        ):
            return "Essences"
        if "$type->divination" in show_line or re.search(
            r"^\s*class\s+.*divination", text, re.MULTILINE
        ):
            return "Divination Cards"
        if any(marker in text for marker in ("map fragments", "fragment", "splinter", "breachstone", "invitation")):
            return "Fragments"
        if re.search(r"^\s*(maptier|waystonetier)\b", text, re.MULTILINE) or re.search(
            r"^\s*class\s+.*\b(maps?|waystones?)\b", text, re.MULTILINE
        ):
            return "Maps"
        if re.search(r"^\s*class\s+.*\bgems?\b", text, re.MULTILINE) or re.search(
            r"^\s*(gemlevel|transfiguredgem|alternatequality)\b", text, re.MULTILINE
        ):
            return "Gems"
        if has_currency_class:
            return "Currency"
        return None

    @staticmethod
    def _indent_for(block: FilterBlock) -> str:
        for line in block.lines[1:]:
            if line.strip() and not line.lstrip().startswith("#"):
                return line[: len(line) - len(line.lstrip())] or "    "
        return "    "

    @staticmethod
    def _escape_sound_reference(reference: str) -> str:
        if any(char in reference for char in ('"', "\n", "\r")):
            raise ValueError("O nome do som contém caracteres não permitidos.")
        return reference.replace("\\", "/")

    def apply_mappings(
        self,
        content: str,
        mappings: Iterable[SoundMapping],
        game_version: str = "poe1",
        managed_sound_prefixes: Iterable[str] = (),
    ) -> EditResult:
        valid, reason = self.validate_content(content)
        if not valid:
            raise ValueError(reason)

        allowed_categories = categories_for_game(game_version)
        mapping_by_category = {
            mapping.category: mapping
            for mapping in mappings
            if mapping.active and mapping.sound_path.strip() and mapping.category in allowed_categories
        }
        if not mapping_by_category:
            raise ValueError("Ative ao menos um mapeamento com um arquivo de som.")

        prefix, blocks = self.parse_blocks(content)
        changes: list[FilterChange] = []
        matched_categories: set[str] = set()
        output = list(prefix)
        normalized_prefixes = tuple(
            prefix.strip().replace("\\", "/").strip("/").lower() + "/"
            for prefix in managed_sound_prefixes
            if prefix.strip().strip("/\\")
        )

        for block in blocks:
            category = self.classify_block(block.text, game_version)
            mapping = mapping_by_category.get(category or "")
            if not mapping:
                stale_commands: list[str] = []
                cleaned_lines: list[str] = []
                stale_reference = ""
                for line in block.lines:
                    custom_match = CUSTOM_SOUND_REFERENCE.match(line)
                    reference = (
                        custom_match.group(1).replace("\\", "/").lower()
                        if custom_match
                        else ""
                    )
                    if reference and any(reference.startswith(prefix) for prefix in normalized_prefixes):
                        stale_commands.append(line.strip())
                        stale_reference = custom_match.group(1)
                    else:
                        cleaned_lines.append(line)
                output.extend(cleaned_lines)
                if stale_commands:
                    changes.append(
                        FilterChange(
                            category="Limpeza fora do mapeamento",
                            block_line=block.start + 1,
                            sound_reference=stale_reference,
                            replaced_commands=stale_commands,
                        )
                    )
                continue

            reference = self._escape_sound_reference(mapping.sound_path)
            command_name = "CustomAlertSoundOptional" if mapping.optional else "CustomAlertSound"
            command = f'{self._indent_for(block)}{command_name} "{reference}" 300'
            replaced: list[str] = []
            kept: list[str] = []
            insertion_index: int | None = None

            for index, line in enumerate(block.lines):
                match = SOUND_COMMAND.match(line)
                if match:
                    if insertion_index is None:
                        insertion_index = len(kept)
                    replaced.append(line.strip())
                    continue
                kept.append(line)

            if insertion_index is None:
                insertion_index = 1
                while insertion_index < len(kept) and kept[insertion_index].lstrip().startswith("#"):
                    insertion_index += 1
            kept.insert(insertion_index, command)
            output.extend(kept)
            matched_categories.add(mapping.category)
            changes.append(
                FilterChange(
                    category=mapping.category,
                    block_line=block.start + 1,
                    sound_reference=reference,
                    replaced_commands=replaced,
                )
            )

        return EditResult(
            content="\n".join(output).rstrip() + "\n",
            changes=changes,
            unmatched_categories=[category for category in mapping_by_category if category not in matched_categories],
        )

    @staticmethod
    def sound_lines(content: str) -> list[tuple[int, str]]:
        return [
            (number, line.strip())
            for number, line in enumerate(content.splitlines(), start=1)
            if SOUND_COMMAND.match(line)
        ]
