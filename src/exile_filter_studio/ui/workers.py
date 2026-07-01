from __future__ import annotations

import traceback
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThread, Signal


class TaskThread(QThread):
    progress = Signal(int)
    succeeded = Signal(object)
    failed = Signal(str, str)

    def __init__(self, function: Callable[..., Any], with_progress: bool = False, parent=None):
        super().__init__(parent)
        self.function = function
        self.with_progress = with_progress

    def run(self) -> None:
        try:
            if self.with_progress:
                result = self.function(progress=self.progress.emit)
            else:
                result = self.function()
            self.succeeded.emit(result)
        except Exception as exc:  # noqa: BLE001 - boundary between worker and UI
            self.failed.emit(str(exc), traceback.format_exc())

