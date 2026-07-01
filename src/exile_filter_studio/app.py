from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from exile_filter_studio.config import APP_NAME
from exile_filter_studio.manager import ApplicationManager
from exile_filter_studio.ui.main_window import MainWindow


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setOrganizationName("Local Tools")
    application.setStyle("Fusion")
    try:
        manager = ApplicationManager()
        window = MainWindow(manager)
        window.show()
        return application.exec()
    except Exception as exc:  # noqa: BLE001 - top-level crash boundary
        QMessageBox.critical(None, "Falha ao iniciar", str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

