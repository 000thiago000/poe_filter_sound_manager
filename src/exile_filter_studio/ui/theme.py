from __future__ import annotations


DARK_THEME = """
QWidget {
    background: #11151d;
    color: #e9edf5;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog { background: #11151d; }
#Sidebar { background: #0b0f16; border-right: 1px solid #252c38; }
#Brand { font-size: 19px; font-weight: 700; color: #f3c969; }
#BrandSub { color: #7f8ba0; font-size: 11px; }
QPushButton {
    background: #222936; border: 1px solid #303949; border-radius: 8px;
    padding: 9px 13px; color: #edf1f8;
}
QPushButton:hover { background: #2b3443; border-color: #d6a84d; }
QPushButton:pressed { background: #1a202b; }
QPushButton:disabled { color: #687285; background: #171c25; border-color: #242b36; }
QPushButton[primary="true"] { background: #d6a84d; color: #15120d; border: none; font-weight: 700; }
QPushButton[primary="true"]:hover { background: #e7bc61; }
QPushButton[nav="true"] { text-align: left; border: none; background: transparent; padding: 11px 14px; }
QPushButton[nav="true"]:checked { background: #29271e; color: #f3c969; border-left: 3px solid #e0b34f; }
QLineEdit, QComboBox, QSpinBox, QPlainTextEdit, QTextEdit {
    background: #171c25; border: 1px solid #303949; border-radius: 7px; padding: 7px;
    selection-background-color: #735c2b;
}
QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus { border-color: #d6a84d; }
QComboBox::drop-down { border: none; width: 28px; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QGroupBox { border: 1px solid #2b3340; border-radius: 10px; margin-top: 13px; padding: 14px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #f3c969; }
QTableWidget { background: #151a22; border: 1px solid #29313e; border-radius: 9px; gridline-color: #252d38; }
QHeaderView::section { background: #202733; border: none; border-bottom: 1px solid #333d4d; padding: 8px; font-weight: 600; }
QTableWidget::item { padding: 6px; }
QTableWidget::item:selected { background: #514323; }
QScrollBar:vertical { background: transparent; width: 11px; }
QScrollBar::handle:vertical { background: #394353; border-radius: 5px; min-height: 28px; }
QProgressBar { background: #171c25; border: 1px solid #303949; border-radius: 5px; text-align: center; }
QProgressBar::chunk { background: #d6a84d; border-radius: 4px; }
#Card { background: #181e28; border: 1px solid #29323f; border-radius: 12px; }
#CardTitle { color: #8f9bad; font-size: 11px; font-weight: 600; }
#CardValue { color: #f3f5f8; font-size: 15px; font-weight: 650; }
#PageTitle { font-size: 25px; font-weight: 750; }
#PageSubtitle { color: #8f9bad; }
#Success { color: #72d6a0; }
#Warning { color: #f3c969; }
#Danger { color: #ff7d83; }
QTabWidget::pane { border: 1px solid #2c3441; border-radius: 8px; }
QTabBar::tab { background: #171c25; padding: 9px 16px; margin-right: 3px; border-radius: 6px; }
QTabBar::tab:selected { background: #39311f; color: #f3c969; }
"""


LIGHT_THEME = DARK_THEME.replace("#11151d", "#f4f6fa").replace("#0b0f16", "#e9edf3").replace(
    "#e9edf5", "#202633"
).replace("#edf1f8", "#202633").replace("#f3f5f8", "#202633").replace(
    "#171c25", "#ffffff"
).replace("#181e28", "#ffffff").replace("#151a22", "#ffffff").replace(
    "#222936", "#e5eaf1"
).replace("#2b3443", "#dce3ec").replace("#202733", "#e7ecf3").replace(
    "#29313e", "#ccd4df"
).replace("#29323f", "#d5dce6").replace("#303949", "#c4cdd9").replace(
    "#2b3340", "#cfd7e2"
).replace("#252c38", "#d2d9e3").replace("#8f9bad", "#657185").replace(
    "#7f8ba0", "#657185"
).replace("#f3c969", "#9a6810").replace("#e0b34f", "#b57b16").replace(
    "#29271e", "#fff4d9"
).replace("#39311f", "#fff0ca").replace("#242b36", "#d8dee7").replace(
    "#687285", "#929dac"
)


def stylesheet(theme: str) -> str:
    return LIGHT_THEME if theme == "light" else DARK_THEME

