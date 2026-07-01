from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRegularExpression, Qt, Signal
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from exile_filter_studio.manager import ApplicationManager
from exile_filter_studio.services.file_utils import read_text_flexible
from exile_filter_studio.ui.widgets import PageHeader


class FilterHighlighter(QSyntaxHighlighter):
    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self.rules: list[tuple[QRegularExpression, QTextCharFormat]] = []
        self._add(r"^\s*(Show|Hide|Minimal)\b", "#f3c969", bold=True)
        self._add(r"^\s*(CustomAlertSoundOptional|CustomAlertSound|PlayAlertSoundPositional|PlayAlertSound)\b.*$", "#72d6a0", bold=True)
        self._add(r"^\s*#.*$", "#6e7a8d")
        self._add(r'"[^"\n]*"', "#8fc7ff")

    def _add(self, pattern: str, color: str, bold: bool = False) -> None:
        style = QTextCharFormat()
        style.setForeground(QColor(color))
        if bold:
            style.setFontWeight(700)
        self.rules.append((QRegularExpression(pattern), style))

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for expression, style in self.rules:
            iterator = expression.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), style)


class EditorPage(QWidget):
    open_reports_requested = Signal()

    def __init__(self, manager: ApplicationManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.current_path: Path | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)
        layout.addWidget(PageHeader("Editor e prévia", "Visualização somente leitura com busca, destaque de áudio e comparação."))

        toolbar = QHBoxLayout()
        self.path_label = QLabel("Nenhum filtro")
        self.path_label.setObjectName("PageSubtitle")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Localizar no filtro…")
        self.search.returnPressed.connect(self.find_next)
        reload_button = QPushButton("Recarregar")
        reload_button.clicked.connect(self.reload)
        validate_button = QPushButton("Validar filtro")
        validate_button.clicked.connect(self.validate)
        compare_button = QPushButton("Comparar original × alterado")
        compare_button.clicked.connect(self.compare)
        reports_button = QPushButton("Abrir relatórios")
        reports_button.clicked.connect(self.open_reports_requested)
        toolbar.addWidget(self.path_label, 1)
        toolbar.addWidget(self.search)
        toolbar.addWidget(reload_button)
        toolbar.addWidget(validate_button)
        toolbar.addWidget(compare_button)
        toolbar.addWidget(reports_button)
        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Horizontal)
        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.editor.setPlaceholderText("Baixe ou importe um filtro para ver a prévia.")
        self.highlighter = FilterHighlighter(self.editor.document())
        self.sounds = QPlainTextEdit()
        self.sounds.setReadOnly(True)
        self.sounds.setMaximumWidth(390)
        self.sounds.setPlaceholderText("Comandos de som encontrados")
        splitter.addWidget(self.editor)
        splitter.addWidget(self.sounds)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)
        self.reload(quiet=True)

    def reload(self, quiet: bool = False) -> None:
        try:
            self.current_path = self.manager.current_filter()
            content = self.manager.read_filter(self.current_path)
            self.path_label.setText(str(self.current_path))
            self.editor.setPlainText(content)
            lines = self.manager.editor.sound_lines(content)
            self.sounds.setPlainText(
                "\n".join(f"Linha {number}\n{line}\n" for number, line in lines)
                or "Nenhum comando de som encontrado."
            )
        except Exception as exc:  # noqa: BLE001
            self.current_path = None
            self.path_label.setText("Nenhum filtro ativo")
            self.editor.clear()
            self.sounds.clear()
            if not quiet:
                QMessageBox.information(self, "Prévia", str(exc))

    def find_next(self) -> None:
        query = self.search.text()
        if query and not self.editor.find(query):
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.Start)
            self.editor.setTextCursor(cursor)
            self.editor.find(query)

    def validate(self) -> None:
        try:
            message = self.manager.validate_filter(self.current_path)
            QMessageBox.information(self, "Filtro válido", message)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Filtro inválido", str(exc))

    def compare(self) -> None:
        history = self.manager.repository.list_history()
        candidate = next(
            (
                row
                for row in history
                if row.get("modified_path") and Path(str(row["modified_path"])).is_file()
            ),
            None,
        )
        if not candidate:
            QMessageBox.information(self, "Comparação", "Ainda não há uma versão modificada para comparar.")
            return
        original_path = Path(str(candidate["original_path"]))
        modified_path = Path(str(candidate["modified_path"]))
        if not original_path.is_file() or not modified_path.is_file():
            QMessageBox.warning(self, "Comparação", "Uma das cópias do histórico não está mais disponível.")
            return
        original, _ = read_text_flexible(original_path)
        modified, _ = read_text_flexible(modified_path)
        dialog = QDialog(self)
        dialog.setWindowTitle("Original × filtro alterado")
        dialog.resize(1150, 720)
        layout = QVBoxLayout(dialog)
        labels = QHBoxLayout()
        labels.addWidget(QLabel(f"Original — {original_path.name}"))
        labels.addWidget(QLabel(f"Alterado — {modified_path.name}"))
        layout.addLayout(labels)
        splitter = QSplitter()
        for content in (original, modified):
            view = QPlainTextEdit(content)
            view.setReadOnly(True)
            view.setLineWrapMode(QPlainTextEdit.NoWrap)
            FilterHighlighter(view.document()).setParent(view)
            splitter.addWidget(view)
        layout.addWidget(splitter)
        dialog.exec()
