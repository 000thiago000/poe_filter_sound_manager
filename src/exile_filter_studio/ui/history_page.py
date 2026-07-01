from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from exile_filter_studio.manager import ApplicationManager
from exile_filter_studio.ui.widgets import PageHeader


class HistoryPage(QWidget):
    restore_requested = Signal(str)
    open_path_requested = Signal(str)

    def __init__(self, manager: ApplicationManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)
        layout.addWidget(PageHeader("Histórico e backups", "Rastreie versões locais e reverta com segurança."))
        tabs = QTabWidget()
        tabs.addTab(self._history_tab(), "Versões")
        tabs.addTab(self._backups_tab(), "Backups")
        layout.addWidget(tabs, 1)
        self.refresh()

    @staticmethod
    def _setup_table(columns: list[str]) -> QTableWidget:
        table = QTableWidget(0, len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    def _history_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.history_table = self._setup_table(["ID", "Filtro", "Data", "Origem", "Pacote", "Destino"])
        layout.addWidget(self.history_table)
        buttons = QHBoxLayout()
        open_button = QPushButton("Abrir arquivo selecionado")
        open_button.clicked.connect(self.open_history)
        remove_button = QPushButton("Remover do histórico")
        remove_button.clicked.connect(self.remove_history)
        refresh_button = QPushButton("Atualizar")
        refresh_button.clicked.connect(self.refresh)
        buttons.addWidget(open_button)
        buttons.addWidget(remove_button)
        buttons.addStretch()
        buttons.addWidget(refresh_button)
        layout.addLayout(buttons)
        return page

    def _backups_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.backup_table = self._setup_table(["ID", "Filtro", "Data", "Motivo", "Arquivo"])
        layout.addWidget(self.backup_table)
        buttons = QHBoxLayout()
        restore_button = QPushButton("Restaurar selecionado")
        restore_button.setProperty("primary", True)
        restore_button.clicked.connect(self.restore_backup)
        open_button = QPushButton("Abrir backup")
        open_button.clicked.connect(self.open_backup)
        buttons.addWidget(restore_button)
        buttons.addWidget(open_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        return page

    def refresh(self) -> None:
        history = self.manager.repository.list_history()
        self.history_table.setRowCount(len(history))
        for row, item in enumerate(history):
            values = [
                item["id"],
                item["name"],
                item["downloaded_at"],
                item["source_type"],
                item["sound_pack"] or "—",
                item["final_path"],
            ]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setData(Qt.UserRole, item)
                self.history_table.setItem(row, column, cell)
        self.history_table.resizeColumnsToContents()

        backups = self.manager.repository.list_backups()
        self.backup_table.setRowCount(len(backups))
        for row, item in enumerate(backups):
            values = [item["id"], item["filter_name"], item["created_at"], item["reason"], item["backup_path"]]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                cell.setData(Qt.UserRole, item)
                self.backup_table.setItem(row, column, cell)
        self.backup_table.resizeColumnsToContents()

    @staticmethod
    def _selected_data(table: QTableWidget) -> dict | None:
        row = table.currentRow()
        item = table.item(row, 0) if row >= 0 else None
        return item.data(Qt.UserRole) if item else None

    def open_history(self) -> None:
        data = self._selected_data(self.history_table)
        if data:
            self.open_path_requested.emit(str(data["final_path"]))

    def open_backup(self) -> None:
        data = self._selected_data(self.backup_table)
        if data:
            self.open_path_requested.emit(str(data["backup_path"]))

    def remove_history(self) -> None:
        data = self._selected_data(self.history_table)
        if not data:
            return
        if QMessageBox.question(
            self,
            "Remover histórico",
            "Remover somente este registro? Os arquivos e o filtro instalado serão preservados.",
        ) != QMessageBox.Yes:
            return
        self.manager.remove_history(int(data["id"]))
        self.refresh()

    def restore_backup(self) -> None:
        data = self._selected_data(self.backup_table)
        if not data:
            QMessageBox.information(self, "Backup", "Selecione um backup primeiro.")
            return
        if QMessageBox.question(
            self,
            "Restaurar backup",
            "O filtro atual também será copiado para um novo backup antes da restauração. Continuar?",
        ) == QMessageBox.Yes:
            self.restore_requested.emit(str(data["backup_path"]))

