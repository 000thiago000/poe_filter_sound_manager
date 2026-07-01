from __future__ import annotations

import json

from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QHBoxLayout, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from exile_filter_studio.manager import ApplicationManager
from exile_filter_studio.ui.widgets import PageHeader


class LogPage(QWidget):
    def __init__(self, manager: ApplicationManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)
        layout.addWidget(PageHeader("Logs", "Eventos de download, cópias, alterações, backups e erros."))
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout.addWidget(self.view, 1)
        buttons = QHBoxLayout()
        refresh = QPushButton("Atualizar")
        refresh.clicked.connect(self.refresh)
        clear = QPushButton("Limpar registros")
        clear.clicked.connect(self.clear)
        buttons.addWidget(refresh)
        buttons.addWidget(clear)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.refresh()

    def refresh(self) -> None:
        lines: list[str] = []
        for entry in self.manager.repository.list_logs():
            details = str(entry["details"] or "")
            if details:
                try:
                    details = json.dumps(json.loads(details), ensure_ascii=False)
                except (json.JSONDecodeError, TypeError):
                    pass
            lines.append(
                f'{entry["created_at"]} | {entry["level"]:<7} | {entry["event"]} | {entry["message"]}'
                + (f" | {details}" if details else "")
            )
        self.view.setPlainText("\n".join(lines) or "Nenhum evento registrado.")
        cursor = self.view.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.view.setTextCursor(cursor)

    def clear(self) -> None:
        if QMessageBox.question(self, "Limpar logs", "Remover todos os logs do banco local?") == QMessageBox.Yes:
            self.manager.repository.clear_logs()
            self.refresh()
