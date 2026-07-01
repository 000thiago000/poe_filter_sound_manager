from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFileDialog,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from exile_filter_studio.manager import ApplicationManager


class OnlineFilterDialog(QDialog):
    def __init__(self, manager: ApplicationManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Importar filtro online do Path of Exile 2")
        self.resize(820, 500)

        layout = QVBoxLayout(self)
        title = QLabel("Filtros online encontrados")
        title.setObjectName("PageTitle")
        help_text = QLabel(
            "O cache original não será alterado. O filtro escolhido será copiado como .filter "
            "para a pasta principal do Path of Exile 2."
        )
        help_text.setObjectName("PageSubtitle")
        help_text.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(help_text)

        path_row = QHBoxLayout()
        self.directory = QLineEdit(manager.settings.get("online_filter_directory"))
        browse = QPushButton("Escolher pasta…")
        browse.clicked.connect(self.browse)
        refresh = QPushButton("Atualizar lista")
        refresh.clicked.connect(self.refresh)
        path_row.addWidget(self.directory, 1)
        path_row.addWidget(browse)
        path_row.addWidget(refresh)
        layout.addLayout(path_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Nome", "Versão", "Versão do filtro", "Realm", "ID local"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.doubleClicked.connect(self.accept_selected)
        layout.addWidget(self.table, 1)

        self.status = QLabel()
        self.status.setObjectName("PageSubtitle")
        buttons = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        choose = QPushButton("Importar selecionado")
        choose.setProperty("primary", True)
        choose.clicked.connect(self.accept_selected)
        buttons.addWidget(self.status, 1)
        buttons.addWidget(cancel)
        buttons.addWidget(choose)
        layout.addLayout(buttons)
        self.refresh()

    def browse(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "Pasta OnlineFilters", self.directory.text().strip()
        )
        if directory:
            self.directory.setText(directory)
            self.refresh()

    def refresh(self) -> None:
        root = Path(self.directory.text().strip()).expanduser()
        entries = self.manager.list_online_filters(root)
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            values = [
                entry["name"],
                entry["version"],
                entry["filterVersion"],
                entry["realm"],
                entry["id"],
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.UserRole, entry["path"])
                self.table.setItem(row, column, item)
        if entries:
            self.table.selectRow(0)
            self.status.setText(f"{len(entries)} filtro(s) encontrado(s)")
        elif root.is_dir():
            self.status.setText("Nenhum filtro online válido encontrado")
        else:
            self.status.setText("A pasta OnlineFilters não foi encontrada")

    def selected_path(self) -> Path | None:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return Path(str(item.data(Qt.UserRole))) if item else None

    def accept_selected(self) -> None:
        if not self.selected_path():
            QMessageBox.information(self, "Filtro online", "Selecione um filtro da lista.")
            return
        self.manager.settings.set("online_filter_directory", self.directory.text().strip())
        self.accept()
