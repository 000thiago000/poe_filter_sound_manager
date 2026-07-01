from __future__ import annotations

from datetime import datetime
from pathlib import Path

from exile_filter_studio.models import FilterChange
from exile_filter_studio.services.file_utils import atomic_write_text, safe_stem, timestamp


class ReportService:
    def __init__(self, report_directory: Path):
        self.report_directory = Path(report_directory)

    def create(
        self,
        filter_path: Path,
        sound_pack: str,
        changes: list[FilterChange],
        copied_sounds: list[Path],
        unmatched_categories: list[str],
    ) -> Path:
        destination = self.report_directory / f"{safe_stem(filter_path.stem)}-{timestamp()}.md"
        lines = [
            "# Relatório de alterações",
            "",
            f"- Filtro: `{filter_path}`",
            f"- Pacote: `{sound_pack}`",
            f"- Data: {datetime.now().astimezone().isoformat(timespec='seconds')}",
            f"- Blocos alterados: {len(changes)}",
            "",
            "## Alterações",
            "",
        ]
        if changes:
            for change in changes:
                replaced = ", ".join(f"`{item}`" for item in change.replaced_commands) or "nenhum comando anterior"
                lines.append(
                    f"- Linha {change.block_line}: **{change.category}** → "
                    f"`{change.sound_reference}` (substituído: {replaced})"
                )
        else:
            lines.append("Nenhum bloco foi alterado.")
        lines.extend(["", "## Arquivos copiados", ""])
        lines.extend(f"- `{path}`" for path in copied_sounds)
        if not copied_sounds:
            lines.append("Nenhum arquivo novo precisou ser copiado.")
        if unmatched_categories:
            lines.extend(["", "## Categorias sem bloco compatível", ""])
            lines.extend(f"- {category}" for category in unmatched_categories)
        atomic_write_text(destination, "\n".join(lines) + "\n")
        return destination

