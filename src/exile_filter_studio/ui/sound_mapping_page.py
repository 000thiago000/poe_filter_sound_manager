from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from exile_filter_studio.manager import ApplicationManager
from exile_filter_studio.models import GAME_LABELS, SoundMapping, categories_for_game
from exile_filter_studio.ui.widgets import PageHeader


class MappingRow(QFrame):
    play_requested = Signal()

    def __init__(self, category: str, parent=None):
        super().__init__(parent)
        self.category = category
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(94)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(8)
        header = QHBoxLayout()
        self.active = QCheckBox("Ativo")
        category_label = QLabel(category)
        category_label.setObjectName("CardValue")
        self.optional = QCheckBox("Opcional")
        self.optional.setChecked(True)
        self.optional.setToolTip("Ignorar este comando se o arquivo de som estiver ausente")
        play = QPushButton("▶")
        play.setFixedWidth(44)
        play.setToolTip("Testar o som selecionado")
        play.clicked.connect(self.play_requested)
        header.addWidget(self.active)
        header.addWidget(category_label)
        header.addStretch()
        header.addWidget(self.optional)
        header.addWidget(play)

        self.sound = QComboBox()
        self.sound.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.sound.setMinimumContentsLength(8)
        self.sound.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.sound.setToolTip("Selecione o arquivo de áudio para esta categoria")
        self.sound.currentTextChanged.connect(self.sound.setToolTip)
        layout.addLayout(header)
        layout.addWidget(self.sound)


class SoundMappingPage(QWidget):
    apply_requested = Signal()
    mappings_saved = Signal()

    def __init__(self, manager: ApplicationManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.8)
        self.player.setAudioOutput(self.audio_output)
        self._sound_paths: list[Path] = []
        self.mapping_rows: list[MappingRow] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(13)
        layout.addWidget(
            PageHeader(
                "Mapeamento de sons",
                "Cada seletor ocupa uma linha inteira. Escolha o pacote, a pasta e depois um áudio por categoria.",
            )
        )

        controls = QFrame()
        controls.setObjectName("Card")
        controls_grid = QGridLayout(controls)
        controls_grid.setContentsMargins(14, 12, 14, 12)
        controls_grid.setHorizontalSpacing(8)
        controls_grid.setVerticalSpacing(9)
        controls_grid.addWidget(QLabel("Jogo"), 0, 0)
        self.game_combo = QComboBox()
        for game_id, label in GAME_LABELS.items():
            self.game_combo.addItem(label, game_id)
        game_index = self.game_combo.findData(self.manager.game_version())
        self.game_combo.setCurrentIndex(max(0, game_index))
        self.game_combo.currentIndexChanged.connect(self.change_game)
        controls_grid.addWidget(self.game_combo, 0, 1, 1, 3)

        controls_grid.addWidget(QLabel("Pacote"), 1, 0)
        self.pack_combo = QComboBox()
        self.pack_combo.currentTextChanged.connect(self.load_pack)
        controls_grid.addWidget(self.pack_combo, 1, 1)
        add_pack = QPushButton("Novo")
        add_pack.clicked.connect(self.add_pack)
        remove_pack = QPushButton("Remover")
        remove_pack.clicked.connect(self.remove_pack)
        controls_grid.addWidget(add_pack, 1, 2)
        controls_grid.addWidget(remove_pack, 1, 3)

        controls_grid.addWidget(QLabel("Pasta de sons"), 2, 0)
        self.directory_edit = QComboBox()
        self.directory_edit.setEditable(True)
        self.directory_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        controls_grid.addWidget(self.directory_edit, 2, 1)
        browse = QPushButton("Procurar…")
        browse.clicked.connect(self.browse_directory)
        scan = QPushButton("Atualizar")
        scan.clicked.connect(self.scan_sounds)
        controls_grid.addWidget(browse, 2, 2)
        controls_grid.addWidget(scan, 2, 3)
        controls_grid.setColumnStretch(1, 1)
        layout.addWidget(controls)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        list_widget = QWidget()
        list_widget.setMinimumWidth(0)
        self.list_layout = QVBoxLayout(list_widget)
        self.list_layout.setContentsMargins(0, 0, 8, 0)
        self.list_layout.setSpacing(9)
        scroll.setWidget(list_widget)
        layout.addWidget(scroll, 1)

        note = QLabel("WAV e MP3 • volume do comando: 300 • backup sempre criado")
        note.setObjectName("PageSubtitle")
        layout.addWidget(note)
        foot = QHBoxLayout()
        foot.addStretch()
        save = QPushButton("Salvar mapeamentos")
        save.clicked.connect(self.save)
        apply_button = QPushButton("Aplicar ao filtro ativo")
        apply_button.setProperty("primary", True)
        apply_button.clicked.connect(self.save_and_apply)
        foot.addWidget(save)
        foot.addWidget(apply_button)
        layout.addLayout(foot)
        self.rebuild_mapping_rows()
        self.load_packs()

    def rebuild_mapping_rows(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.hide()
                widget.deleteLater()
        self.mapping_rows.clear()
        for index, category in enumerate(categories_for_game(self.manager.game_version())):
            row = MappingRow(category)
            row.play_requested.connect(lambda index=index: self.play_sound(index))
            self.mapping_rows.append(row)
            self.list_layout.addWidget(row)
            row.show()
        self.list_layout.addStretch()
        self.list_layout.invalidate()
        self.list_layout.activate()

    def change_game(self) -> None:
        game_version = str(self.game_combo.currentData())
        self.manager.set_game_version(game_version)
        self.rebuild_mapping_rows()
        self.load_pack(self.pack_combo.currentText())

    def sync_game(self, game_version: str) -> None:
        index = self.game_combo.findData(game_version)
        self.game_combo.blockSignals(True)
        self.game_combo.setCurrentIndex(max(0, index))
        self.game_combo.blockSignals(False)
        self.rebuild_mapping_rows()
        self.load_pack(self.pack_combo.currentText())

    def load_packs(self) -> None:
        current = self.manager.settings.get("active_sound_pack", "Padrão")
        self.pack_combo.blockSignals(True)
        self.pack_combo.clear()
        self.pack_combo.addItems([str(pack["name"]) for pack in self.manager.repository.list_sound_packs()])
        index = self.pack_combo.findText(current)
        self.pack_combo.setCurrentIndex(max(0, index))
        self.pack_combo.blockSignals(False)
        self.load_pack(self.pack_combo.currentText())

    def load_pack(self, name: str) -> None:
        if not name:
            return
        packs = {str(pack["name"]): pack for pack in self.manager.repository.list_sound_packs()}
        directory = str(packs.get(name, {}).get("directory", ""))
        if not directory:
            directory = self.manager.settings.get("sound_source_directory")
        self.directory_edit.setCurrentText(directory)
        mappings = {
            mapping.category: mapping
            for mapping in self.manager.repository.get_mappings(name, self.manager.game_version())
        }
        self.scan_sounds(show_warning=False)
        for row in self.mapping_rows:
            mapping = mappings[row.category]
            row.active.setChecked(mapping.active)
            row.optional.setChecked(mapping.optional)
            index = row.sound.findData(mapping.sound_path)
            if index < 0 and mapping.sound_path:
                row.sound.addItem(Path(mapping.sound_path).name, mapping.sound_path)
                index = row.sound.count() - 1
            row.sound.setCurrentIndex(max(0, index))
        self.manager.settings.set("active_sound_pack", name)

    def add_pack(self) -> None:
        name, accepted = QInputDialog.getText(self, "Novo pacote", "Nome do pacote")
        if not accepted or not name.strip():
            return
        try:
            self.manager.repository.ensure_sound_pack(name.strip(), self.directory_edit.currentText().strip())
            self.manager.settings.set("active_sound_pack", name.strip())
            self.load_packs()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Pacote", str(exc))

    def remove_pack(self) -> None:
        name = self.pack_combo.currentText()
        if QMessageBox.question(self, "Remover pacote", f"Remover o pacote '{name}' e seus mapeamentos?") != QMessageBox.Yes:
            return
        try:
            self.manager.repository.delete_sound_pack(name)
            self.manager.settings.set("active_sound_pack", "Padrão")
            self.load_packs()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Pacote", str(exc))

    def browse_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Selecionar pasta de sons", self.directory_edit.currentText()
        )
        if directory:
            self.directory_edit.setCurrentText(directory)
            self.scan_sounds()

    def scan_sounds(self, show_warning: bool = True) -> None:
        root = Path(self.directory_edit.currentText().strip()).expanduser()
        self._sound_paths = self.manager.sounds.list_sounds(root)
        for row in self.mapping_rows:
            selected = row.sound.currentData()
            row.sound.clear()
            row.sound.addItem("Selecione um arquivo de áudio…", "")
            for path in self._sound_paths:
                try:
                    relative = str(path.resolve().relative_to(root.resolve()))
                except ValueError:
                    relative = str(path)
                row.sound.addItem(relative, relative)
            index = row.sound.findData(selected)
            row.sound.setCurrentIndex(max(0, index))
        if show_warning and not self._sound_paths:
            QMessageBox.information(self, "Sons", "Nenhum arquivo WAV ou MP3 foi encontrado nessa pasta.")

    def play_sound(self, index: int) -> None:
        selected = str(self.mapping_rows[index].sound.currentData() or "")
        if not selected:
            return
        path = Path(selected)
        if not path.is_absolute():
            path = Path(self.directory_edit.currentText()) / path
        if not path.is_file():
            QMessageBox.warning(self, "Testar som", f"Arquivo não encontrado: {path}")
            return
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(str(path.resolve())))
        self.player.play()

    def collect(self) -> list[SoundMapping]:
        return [
            SoundMapping(
                category=row.category,
                sound_path=str(row.sound.currentData() or ""),
                active=row.active.isChecked(),
                optional=row.optional.isChecked(),
            )
            for row in self.mapping_rows
        ]

    def save(self) -> bool:
        try:
            self.manager.save_sound_mappings(
                self.pack_combo.currentText(),
                self.directory_edit.currentText().strip(),
                self.collect(),
            )
            self.mappings_saved.emit()
            return True
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Mapeamentos", str(exc))
            return False

    def save_and_apply(self) -> None:
        if self.save():
            self.apply_requested.emit()
