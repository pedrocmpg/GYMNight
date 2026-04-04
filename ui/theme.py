"""
ui/theme.py
Paleta de cores e QSS global do GYMNight.
"""

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------

C_BG        = "#161616"
C_SURFACE   = "#1e1e1e"
C_CARD      = "#242424"
C_CARD2     = "#2a2a2a"
C_BORDER    = "#383838"
C_GREEN     = "#a3e635"
C_GREEN_DK  = "#65a30d"
C_GREEN_BG  = "#1a2e0a"
C_TEXT      = "#ffffff"
C_TEXT2     = "#9ca3af"
C_TEXT3     = "#6b7280"
C_RED       = "#ef4444"
C_RED_BG    = "#2a0a0a"

# ---------------------------------------------------------------------------
# QSS global
# ---------------------------------------------------------------------------

DARK_QSS = f"""
* {{ font-family: 'Inter', 'Segoe UI', sans-serif; }}

QMainWindow, QDialog, QWidget {{
    background-color: {C_BG};
    color: {C_TEXT};
    font-size: 13px;
}}

QTabWidget::pane {{ border: none; background: {C_BG}; }}
QTabBar::tab {{
    background: transparent;
    color: {C_TEXT3};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 24px;
    font-weight: 600;
    font-size: 13px;
}}
QTabBar::tab:selected {{ color: {C_TEXT}; border-bottom: 2px solid {C_GREEN}; }}
QTabBar::tab:hover {{ color: {C_TEXT2}; }}

QPushButton {{
    background-color: {C_GREEN};
    color: #000000;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 700;
    font-size: 13px;
}}
QPushButton:hover {{ background-color: #b5f542; }}
QPushButton:pressed {{ background-color: {C_GREEN_DK}; }}
QPushButton:disabled {{ background-color: #2a2a2a; color: {C_TEXT3}; }}

QPushButton#ghost {{
    background-color: transparent;
    color: {C_TEXT2};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
}}
QPushButton#ghost:hover {{ border-color: {C_GREEN}; color: {C_TEXT}; }}

QPushButton#danger {{
    background-color: transparent;
    color: {C_RED};
    border: 1px solid {C_RED};
    border-radius: 8px;
}}
QPushButton#danger:hover {{ background-color: {C_RED_BG}; }}

QLineEdit, QSpinBox, QComboBox {{
    background-color: {C_CARD};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {C_GREEN}; }}

QScrollBar:vertical {{
    background: {C_SURFACE};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: #3a3a3a;
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QTableView {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    gridline-color: {C_BORDER};
    selection-background-color: {C_GREEN_BG};
    selection-color: {C_GREEN};
}}
QHeaderView::section {{
    background: {C_CARD2};
    color: {C_TEXT3};
    border: none;
    border-bottom: 1px solid {C_BORDER};
    padding: 8px 12px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
}}

QListWidget {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
}}
QListWidget::item {{ padding: 10px 14px; border-bottom: 1px solid {C_BORDER}; color: {C_TEXT2}; }}
QListWidget::item:selected {{ background: {C_GREEN_BG}; color: {C_GREEN}; }}
QListWidget::item:hover {{ background: {C_CARD2}; color: {C_TEXT}; }}

QLabel#h1 {{ font-size: 28px; font-weight: 800; color: {C_TEXT}; }}
QLabel#h2 {{ font-size: 20px; font-weight: 700; color: {C_TEXT}; }}
QLabel#h3 {{ font-size: 15px; font-weight: 700; color: {C_TEXT}; }}
QLabel#sub {{ font-size: 12px; color: {C_TEXT3}; }}
QLabel#green {{ color: {C_GREEN}; font-weight: 700; }}
QLabel#stat_val {{ font-size: 26px; font-weight: 800; color: {C_TEXT}; }}
QLabel#stat_lbl {{ font-size: 11px; color: {C_TEXT3}; }}

QFrame#card {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 12px;
}}
QFrame#sep {{
    background: {C_BORDER};
    max-height: 1px;
}}
"""

# ---------------------------------------------------------------------------
# Helpers de UI
# ---------------------------------------------------------------------------

from PySide6.QtWidgets import QFrame, QLabel, QWidget
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect


def card(parent=None) -> QFrame:
    f = QFrame(parent)
    f.setObjectName("card")
    return f


def separator(parent=None) -> QFrame:
    f = QFrame(parent)
    f.setObjectName("sep")
    f.setFrameShape(QFrame.HLine)
    return f


def label(text: str, obj: str = "", parent=None) -> QLabel:
    l = QLabel(text, parent)
    if obj:
        l.setObjectName(obj)
    return l


def shadow(widget: QWidget, radius: int = 20, opacity: int = 80) -> QWidget:
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(radius)
    eff.setColor(QColor(0, 0, 0, opacity))
    eff.setOffset(0, 4)
    widget.setGraphicsEffect(eff)
    return widget
