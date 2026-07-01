from __future__ import annotations

from functools import partial
from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from exile_filter_studio.manager import ApplicationManager
from exile_filter_studio.ui.dashboard_page import DashboardPage
from exile_filter_studio.ui.editor_page import EditorPage
from exile_filter_studio.ui.history_page import HistoryPage
from exile_filter_studio.ui.log_page import LogPage
from exile_filter_studio.ui.online_filter_dialog import OnlineFilterDialog
from exile_filter_studio.ui.settings_page import SettingsPage
from exile_filter_studio.ui.sound_mapping_page import SoundMappingPage
from exile_filter_studio.ui.theme import stylesheet
from exile_filter_studio.ui.workers import TaskThread


class MainWindow(QMainWindow):
    def __init__(self, manager: ApplicationManager):
        super().__init__()
        self.manager = manager
        self._worker: TaskThread | None = None
        self.setWindowTitle("Exile Filter Studio")
        self.resize(1220, 780)
        self.setMinimumSize(980, 650)
        self._build_ui()
        self.apply_theme(self.manager.settings.get("theme", "dark"))
        self._connect_pages()

    def _build_ui(self) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(218)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 22, 14, 18)
        brand = QLabel("EXILE FILTER")
        brand.setObjectName("Brand")
        sub = QLabel("STUDIO  •  local & seguro")
        sub.setObjectName("BrandSub")
        side.addWidget(brand)
        side.addWidget(sub)
        side.addSpacing(24)

        self.stack = QStackedWidget()
        self.dashboard = DashboardPage(self.manager)
        self.sounds = SoundMappingPage(self.manager)
        self.editor = EditorPage(self.manager)
        self.history = HistoryPage(self.manager)
        self.logs = LogPage(self.manager)
        self.settings = SettingsPage(self.manager)
        self.pages = [self.dashboard, self.sounds, self.editor, self.history, self.logs, self.settings]
        for page in self.pages:
            self.stack.addWidget(page)

        self.nav_buttons: list[QPushButton] = []
        labels = ["⌂  Visão geral", "♫  Sons", "{ }  Editor", "↶  Histórico", "≡  Logs", "⚙  Configurações"]
        for index, text in enumerate(labels):
            button = QPushButton(text)
            button.setProperty("nav", True)
            button.setCheckable(True)
            button.clicked.connect(partial(self.navigate, index))
            side.addWidget(button)
            self.nav_buttons.append(button)
        self.nav_buttons[0].setChecked(True)
        side.addStretch()
        safety = QLabel("ORIGINAIS PRESERVADOS\nBACKUPS AUTOMÁTICOS")
        safety.setObjectName("BrandSub")
        safety.setAlignment(Qt.AlignCenter)
        side.addWidget(safety)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.stack, 1)
        status_bar = QWidget()
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(16, 7, 16, 7)
        self.status_label = QLabel("Pronto")
        self.status_label.setObjectName("PageSubtitle")
        self.progress = QProgressBar()
        self.progress.setFixedWidth(220)
        self.progress.setRange(0, 100)
        self.progress.hide()
        status_layout.addWidget(self.status_label, 1)
        status_layout.addWidget(self.progress)
        content_layout.addWidget(status_bar)

        root.addWidget(sidebar)
        root.addWidget(content, 1)
        self.setCentralWidget(central)

    def _connect_pages(self) -> None:
        self.dashboard.download_requested.connect(self.download_filter)
        self.dashboard.import_requested.connect(self.import_filter)
        self.dashboard.import_online_requested.connect(self.import_online_filter)
        self.dashboard.export_share_requested.connect(self.export_share_zip)
        self.dashboard.apply_requested.connect(self.apply_sounds)
        self.dashboard.open_folder_requested.connect(lambda: self.open_path(str(self.manager.filter_directory())))
        self.dashboard.settings_requested.connect(lambda: self.navigate(5))
        self.settings.settings_saved.connect(lambda: self.notify("Configurações salvas."))
        self.settings.settings_saved.connect(self.dashboard.refresh)
        self.settings.test_requested.connect(self.test_permissions)
        self.settings.theme_changed.connect(self.apply_theme)
        self.settings.game_changed.connect(self.sounds.sync_game)
        self.settings.game_changed.connect(lambda _: self.dashboard.refresh())
        self.sounds.apply_requested.connect(self.apply_sounds)
        self.sounds.mappings_saved.connect(lambda: self.notify("Mapeamentos salvos."))
        self.editor.open_reports_requested.connect(lambda: self.open_path(str(self.manager.paths.reports)))
        self.history.restore_requested.connect(self.restore_backup)
        self.history.open_path_requested.connect(self.open_path)

    def navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for position, button in enumerate(self.nav_buttons):
            button.setChecked(position == index)
        page = self.pages[index]
        refresh = getattr(page, "refresh", None)
        if callable(refresh):
            refresh()
        elif isinstance(page, EditorPage):
            page.reload(quiet=True)

    def apply_theme(self, theme: str) -> None:
        QApplication.instance().setStyleSheet(stylesheet(theme))

    def notify(self, message: str) -> None:
        self.status_label.setText(message)

    def set_busy(self, busy: bool, message: str = "") -> None:
        self.stack.setEnabled(not busy)
        for button in self.nav_buttons:
            button.setEnabled(not busy)
        self.progress.setVisible(busy)
        if busy:
            self.progress.setValue(0)
            self.status_label.setText(message or "Processando…")

    def run_task(self, function, *, title: str, on_success=None, with_progress: bool = False) -> None:
        if self._worker and self._worker.isRunning():
            self.notify("Aguarde a operação atual terminar.")
            return
        self.set_busy(True, title)
        worker = TaskThread(function, with_progress=with_progress, parent=self)
        self._worker = worker
        worker.progress.connect(self.progress.setValue)

        def success(result) -> None:
            self.set_busy(False)
            self.notify("Operação concluída.")
            if on_success:
                on_success(result)
            self.refresh_all()
            worker.deleteLater()
            self._worker = None

        def failure(message: str, trace: str) -> None:
            self.set_busy(False)
            self.manager.report_error("ui.task.failed", RuntimeError(message))
            self.status_label.setText("A operação falhou.")
            QMessageBox.warning(self, "Não foi possível concluir", message)
            worker.deleteLater()
            self._worker = None

        worker.succeeded.connect(success)
        worker.failed.connect(failure)
        worker.start()

    def refresh_all(self) -> None:
        self.dashboard.refresh()
        self.sounds.sync_game(self.manager.game_version())
        self.history.refresh()
        self.logs.refresh()
        self.editor.reload(quiet=True)

    def download_filter(self) -> None:
        url = self.manager.settings.get("download_url").strip()
        if not url:
            QMessageBox.information(
                self,
                "URL não configurada",
                "Informe uma URL direta nas Configurações ou use 'Importar .filter'.",
            )
            self.navigate(5)
            return
        self.run_task(
            self.manager.download_filter,
            title="Baixando e validando filtro…",
            with_progress=True,
            on_success=lambda result: QMessageBox.information(
                self, "Filtro instalado", f"Filtro salvo em:\n{result.final_path}"
            ),
        )

    def import_filter(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Importar filtro", str(Path.home()), "Filtros do Path of Exile (*.filter)"
        )
        if not filename:
            return
        self.run_task(
            partial(self.manager.import_filter, Path(filename)),
            title="Importando e validando filtro…",
            on_success=lambda result: QMessageBox.information(
                self, "Filtro importado", f"Filtro salvo em:\n{result.final_path}"
            ),
        )

    def import_online_filter(self) -> None:
        dialog = OnlineFilterDialog(self.manager, self)
        if dialog.exec() != QDialog.Accepted:
            return
        source = dialog.selected_path()
        if not source:
            return
        self.run_task(
            partial(self.manager.import_online_filter, source),
            title="Importando filtro online do PoE 2…",
            on_success=lambda result: QMessageBox.information(
                self,
                "Filtro online importado",
                f"Cópia local criada em:\n{result.final_path}\n\nO arquivo de OnlineFilters foi preservado.",
            ),
        )

    def export_share_zip(self) -> None:
        try:
            current_filter = self.manager.current_filter()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.information(self, "Exportar ZIP", str(exc))
            return
        downloads = Path.home() / "Downloads"
        initial_directory = downloads if downloads.is_dir() else Path.home()
        suggested = initial_directory / f"{current_filter.stem}-surpresa.zip"
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar pacote para amigo",
            str(suggested),
            "Arquivo ZIP (*.zip)",
        )
        if not filename:
            return
        self.run_task(
            partial(self.manager.export_share_zip, Path(filename)),
            title="Criando ZIP e ocultando nomes dos sons…",
            with_progress=True,
            on_success=lambda result: QMessageBox.information(
                self,
                "ZIP pronto para enviar",
                f"Arquivo criado em:\n{result.zip_path}\n\n"
                f"{result.sound_count} som(ns) receberam nomes aleatórios. "
                "Envie o ZIP inteiro ao seu amigo.",
            ),
        )

    def apply_sounds(self) -> None:
        if QMessageBox.question(
            self,
            "Aplicar sons",
            "O filtro atual será preservado em backup antes das alterações. Continuar?",
        ) != QMessageBox.Yes:
            return
        self.run_task(
            self.manager.apply_sounds,
            title="Copiando sons e atualizando filtro…",
            with_progress=True,
            on_success=lambda result: QMessageBox.information(
                self,
                "Sons aplicados",
                f"{len(result.changes)} bloco(s) alterado(s).\nRelatório: {result.report_path}",
            ),
        )

    def restore_backup(self, backup_path: str) -> None:
        self.run_task(
            partial(self.manager.restore_backup, Path(backup_path)),
            title="Restaurando backup…",
            on_success=lambda path: QMessageBox.information(self, "Backup restaurado", f"Restaurado em:\n{path}"),
        )

    def test_permissions(self, directory: str) -> None:
        self.run_task(
            partial(self.manager.test_write_permission, Path(directory)),
            title="Testando permissão…",
            on_success=lambda message: QMessageBox.information(self, "Permissão", str(message)),
        )

    @staticmethod
    def open_path(path: str) -> None:
        target = Path(path).expanduser()
        if target.is_file():
            url = QUrl.fromLocalFile(str(target.resolve()))
        else:
            target.mkdir(parents=True, exist_ok=True)
            url = QUrl.fromLocalFile(str(target.resolve()))
        QDesktopServices.openUrl(url)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt API
        if self._worker and self._worker.isRunning():
            event.ignore()
            self.notify("Aguarde a operação atual terminar antes de fechar.")
            return
        self.manager.close()
        event.accept()
