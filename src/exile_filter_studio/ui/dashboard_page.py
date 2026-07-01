from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from exile_filter_studio.manager import ApplicationManager
from exile_filter_studio.models import GAME_LABELS
from exile_filter_studio.ui.widgets import PageHeader, StatusCard


class DashboardPage(QWidget):
    download_requested = Signal()
    import_requested = Signal()
    import_online_requested = Signal()
    export_share_requested = Signal()
    apply_requested = Signal()
    open_folder_requested = Signal()
    settings_requested = Signal()

    def __init__(self, manager: ApplicationManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        layout.addWidget(
            PageHeader(
                "Visão geral",
                "Seu filtro, seus sons e os backups importantes em um único lugar.",
            )
        )

        cards = QGridLayout()
        cards.setSpacing(12)
        self.folder_card = StatusCard("Pasta do Path of Exile")
        self.filter_card = StatusCard("Último filtro")
        self.pack_card = StatusCard("Pacote ativo")
        self.update_card = StatusCard("Última atualização")
        for index, card in enumerate(
            (self.folder_card, self.filter_card, self.pack_card, self.update_card)
        ):
            cards.addWidget(card, index // 2, index % 2)
        layout.addLayout(cards)

        section = QLabel("AÇÕES RÁPIDAS")
        section.setObjectName("CardTitle")
        layout.addWidget(section)
        actions = QGridLayout()
        actions.setSpacing(10)
        download = QPushButton("↓  Baixar de URL")
        download.setProperty("primary", True)
        download.clicked.connect(self.download_requested)
        import_button = QPushButton("＋  Importar .filter")
        import_button.clicked.connect(self.import_requested)
        online_button = QPushButton("☁  Importar filtro online")
        online_button.clicked.connect(self.import_online_requested)
        apply_button = QPushButton("♫  Aplicar sons")
        apply_button.clicked.connect(self.apply_requested)
        folder_button = QPushButton("▣  Abrir pasta do filtro")
        folder_button.clicked.connect(self.open_folder_requested)
        settings_button = QPushButton("⚙  Configurações")
        settings_button.clicked.connect(self.settings_requested)
        export_button = QPushButton("⇧  Exportar ZIP surpresa")
        export_button.clicked.connect(self.export_share_requested)
        for index, button in enumerate(
            (
                download,
                import_button,
                online_button,
                apply_button,
                export_button,
                folder_button,
                settings_button,
            )
        ):
            button.setMinimumHeight(46)
            actions.addWidget(button, index // 3, index % 3)
        layout.addLayout(actions)

        note = QLabel(
            "Dica: a importação manual é o caminho mais estável para exports do FilterBlade. "
            "O app só usa URLs diretas e nunca depende de endpoints privados."
        )
        note.setObjectName("PageSubtitle")
        note.setWordWrap(True)
        layout.addWidget(note)
        layout.addStretch()
        self.refresh()

    def refresh(self) -> None:
        settings = self.manager.settings.all()
        filter_directory = Path(settings.get("filter_directory", ""))
        self.folder_card.set_value(
            f"{filter_directory}\n{'Detectada' if filter_directory.is_dir() else 'Precisa ser configurada'}"
        )
        history = self.manager.repository.list_history(1)
        if history:
            latest = history[0]
            self.filter_card.set_value(str(latest["name"]))
            self.update_card.set_value(str(latest["downloaded_at"]))
        else:
            current = settings.get("current_filter_path", "")
            self.filter_card.set_value(Path(current).name if current else "Nenhum filtro")
            self.update_card.set_value("Ainda não atualizado")
        game_label = GAME_LABELS.get(settings.get("game_version", "poe2"), "Path of Exile 2")
        self.pack_card.set_value(f"{settings.get('active_sound_pack', 'Padrão')}\n{game_label}")
