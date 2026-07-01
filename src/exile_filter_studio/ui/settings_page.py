from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from exile_filter_studio.manager import ApplicationManager
from exile_filter_studio.models import GAME_LABELS
from exile_filter_studio.ui.widgets import PageHeader


class PathField(QWidget):
    def __init__(self, choose_file: bool = False, parent=None):
        super().__init__(parent)
        self.choose_file = choose_file
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)
        self.edit = QLineEdit()
        button = QPushButton("Procurar…")
        button.clicked.connect(self.browse)
        layout.addWidget(self.edit, 1)
        layout.addWidget(button)

    def browse(self) -> None:
        if self.choose_file:
            value, _ = QFileDialog.getOpenFileName(self, "Selecionar arquivo", self.edit.text())
        else:
            value = QFileDialog.getExistingDirectory(self, "Selecionar pasta", self.edit.text())
        if value:
            self.edit.setText(value)

    def text(self) -> str:
        return self.edit.text().strip()

    def setText(self, value: str) -> None:  # noqa: N802 - Qt naming convention
        self.edit.setText(value)


class SettingsPage(QWidget):
    settings_saved = Signal()
    test_requested = Signal(str)
    theme_changed = Signal(str)
    game_changed = Signal(str)

    def __init__(self, manager: ApplicationManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 24)
        outer.addWidget(PageHeader("Configurações", "Ajuste caminhos, segurança e comportamento do aplicativo."))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 10, 12)
        layout.setSpacing(14)

        locations = QGroupBox("Pastas e FilterBlade")
        form = QFormLayout(locations)
        form.setSpacing(11)
        self.game_combo = QComboBox()
        for game_id, label in GAME_LABELS.items():
            self.game_combo.addItem(label, game_id)
        self.filter_directory_poe1 = PathField()
        self.filter_directory_poe2 = PathField()
        self.online_filter_directory = PathField()
        self.download_url = QLineEdit()
        self.download_url.setPlaceholderText("URL direta que retorna texto de um arquivo .filter")
        self.base_name = QLineEdit()
        self.sound_directory = PathField()
        self.sound_subdirectory = QLineEdit()
        self.sound_subdirectory.setPlaceholderText("ExileFilterStudio")
        form.addRow("Jogo ativo", self.game_combo)
        form.addRow("Pasta de filtros do PoE 1", self.filter_directory_poe1)
        form.addRow("Pasta de filtros do PoE 2", self.filter_directory_poe2)
        form.addRow("Filtros online do PoE 2", self.online_filter_directory)
        form.addRow("URL direta do filtro", self.download_url)
        form.addRow("Nome base", self.base_name)
        form.addRow("Pasta local dos sons", self.sound_directory)
        form.addRow("Subpasta de sons no jogo", self.sound_subdirectory)
        layout.addWidget(locations)

        behavior = QGroupBox("Segurança e histórico")
        behavior_layout = QVBoxLayout(behavior)
        self.backup = QCheckBox("Criar backup antes de alterar qualquer filtro (obrigatório)")
        self.backup.setChecked(True)
        self.backup.setEnabled(False)
        self.overwrite = QCheckBox("Sobrescrever arquivos existentes")
        self.validate_sounds = QCheckBox("Validar todos os sons antes de aplicar")
        self.keep_history = QCheckBox("Manter histórico de versões")
        self.optional_sounds = QCheckBox("Usar CustomAlertSoundOptional por padrão")
        for checkbox in (
            self.backup,
            self.overwrite,
            self.validate_sounds,
            self.keep_history,
            self.optional_sounds,
        ):
            behavior_layout.addWidget(checkbox)
        layout.addWidget(behavior)

        appearance = QGroupBox("Aparência")
        appearance_form = QFormLayout(appearance)
        self.theme = QComboBox()
        self.theme.addItem("Escuro", "dark")
        self.theme.addItem("Claro", "light")
        appearance_form.addRow("Tema", self.theme)
        layout.addWidget(appearance)

        buttons = QHBoxLayout()
        test_button = QPushButton("Testar permissão de escrita")
        test_button.clicked.connect(
            lambda: self.test_requested.emit(self.active_filter_directory())
        )
        save_button = QPushButton("Salvar configurações")
        save_button.setProperty("primary", True)
        save_button.clicked.connect(self.save)
        buttons.addWidget(test_button)
        buttons.addStretch()
        buttons.addWidget(save_button)
        layout.addLayout(buttons)
        layout.addStretch()
        scroll.setWidget(body)
        outer.addWidget(scroll)
        self.load()

    def load(self) -> None:
        values = self.manager.settings.all()
        game_index = self.game_combo.findData(values.get("game_version", "poe2"))
        self.game_combo.setCurrentIndex(max(0, game_index))
        self.filter_directory_poe1.setText(values.get("filter_directory_poe1", ""))
        self.filter_directory_poe2.setText(values.get("filter_directory_poe2", ""))
        self.online_filter_directory.setText(values.get("online_filter_directory", ""))
        self.download_url.setText(values.get("download_url", ""))
        self.base_name.setText(values.get("base_filter_name", "MeuFiltro"))
        self.sound_directory.setText(values.get("sound_source_directory", ""))
        self.sound_subdirectory.setText(values.get("sound_subdirectory", "ExileFilterStudio"))
        self.overwrite.setChecked(values.get("overwrite_existing") == "1")
        self.validate_sounds.setChecked(values.get("validate_sounds", "1") == "1")
        self.keep_history.setChecked(values.get("keep_history", "1") == "1")
        self.optional_sounds.setChecked(values.get("use_optional_sounds", "1") == "1")
        index = self.theme.findData(values.get("theme", "dark"))
        self.theme.setCurrentIndex(max(0, index))

    def refresh(self) -> None:
        self.load()

    def save(self) -> None:
        game_version = str(self.game_combo.currentData())
        active_directory = (
            self.filter_directory_poe1.text()
            if game_version == "poe1"
            else self.filter_directory_poe2.text()
        )
        values = {
            "game_version": game_version,
            "filter_directory": active_directory,
            "filter_directory_poe1": self.filter_directory_poe1.text(),
            "filter_directory_poe2": self.filter_directory_poe2.text(),
            "online_filter_directory": self.online_filter_directory.text(),
            "download_url": self.download_url.text().strip(),
            "base_filter_name": self.base_name.text().strip() or "MeuFiltro",
            "sound_source_directory": self.sound_directory.text(),
            "sound_subdirectory": self.sound_subdirectory.text().strip(),
            "backup_before_apply": True,
            "overwrite_existing": self.overwrite.isChecked(),
            "validate_sounds": self.validate_sounds.isChecked(),
            "keep_history": self.keep_history.isChecked(),
            "use_optional_sounds": self.optional_sounds.isChecked(),
            "theme": self.theme.currentData(),
        }
        self.manager.settings.update(values)
        self.manager.set_game_version(game_version)
        self.theme_changed.emit(str(self.theme.currentData()))
        self.game_changed.emit(game_version)
        self.settings_saved.emit()

    def active_filter_directory(self) -> str:
        return (
            self.filter_directory_poe1.text()
            if self.game_combo.currentData() == "poe1"
            else self.filter_directory_poe2.text()
        )
