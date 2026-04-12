"""
ui/theme.py
Paleta de cores e QSS global do GYMNight.
"""

# ---------------------------------------------------------------------------
# Paleta – hierarquia de superfície
# ---------------------------------------------------------------------------

C_BG            = "#181818"
C_SURFACE       = "#1e1e1e"
C_CARD          = "#242424"
C_CARD2         = "#2c2c2c"

C_BORDER        = "#383838"

C_GREEN         = "#a2ff00"
C_GREEN_ACTIVE  = "#b5f542"   # hover / destaque
C_GREEN_DK      = "#65a30d"
C_GREEN_BG      = "#1a2e0a"
C_ACCENT_MUTED  = "#1a3a00"   # seleção suave

C_TEXT          = "#ffffff"
C_TEXT2         = "#9ca3af"
C_TEXT3         = "#6b7280"

C_RED           = "#ef4444"
C_RED_BG        = "#2a0a0a"

# ---------------------------------------------------------------------------
# Tokens de espaçamento / raio
# ---------------------------------------------------------------------------

RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 16

# ---------------------------------------------------------------------------
# QSS global
# ---------------------------------------------------------------------------

DARK_QSS = f"""
* {{
    font-family: 'Inter', 'Segoe UI', sans-serif;
    letter-spacing: 0px;
    word-spacing: 0px;
}}

QMainWindow, QDialog, QWidget {{
    background-color: {C_BG};
    color: {C_TEXT};
    font-size: 15px;
}}

QMainWindow {{
    background-color: transparent;
}}

/* ── Tabs ─────────────────────────────────────────────────────────────── */
QTabWidget::pane {{ border: none; background: {C_BG}; }}
QTabBar::tab {{
    background: transparent;
    color: {C_TEXT3};
    border: none;
    border-bottom: 3px solid transparent;
    padding: 15px 36px;
    font-weight: 600;
    font-size: 15px;
}}
QTabBar::tab:selected {{ color: {C_TEXT}; border-bottom: 3px solid {C_GREEN}; }}
QTabBar::tab:hover    {{ color: {C_TEXT2}; }}

/* ── Botões ───────────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {C_GREEN};
    color: #000000;
    border: none;
    border-radius: {RADIUS_MD}px;
    padding: 12px 27px;
    font-weight: 700;
    font-size: 15px;
}}
QPushButton:hover    {{ background-color: {C_GREEN_ACTIVE}; }}
QPushButton:pressed  {{ background-color: {C_GREEN_DK}; }}
QPushButton:disabled {{ background-color: {C_CARD2}; color: {C_TEXT3}; }}

QPushButton#ghost {{
    background-color: transparent;
    color: {C_TEXT2};
    border: 2px solid {C_BORDER};
    border-radius: {RADIUS_MD}px;
}}
QPushButton#ghost:hover {{ border-color: {C_GREEN}; color: {C_TEXT}; }}

QPushButton#danger {{
    background-color: transparent;
    color: {C_RED};
    border: 2px solid {C_RED};
    border-radius: {RADIUS_MD}px;
}}
QPushButton#danger:hover {{ background-color: {C_RED_BG}; }}

/* ── Inputs ───────────────────────────────────────────────────────────── */
QLineEdit, QSpinBox, QComboBox {{
    background-color: {C_CARD};
    color: {C_TEXT};
    border: 2px solid {C_BORDER};
    border-radius: {RADIUS_MD}px;
    padding: 12px 18px;
    font-size: 15px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {C_GREEN}; }}

/* ── Scrollbar ────────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: {C_SURFACE};
    width: 9px;
    border-radius: {RADIUS_SM}px;
}}
QScrollBar::handle:vertical {{
    background: #3a3a3a;
    border-radius: {RADIUS_SM}px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* ── Tabela ───────────────────────────────────────────────────────────── */
QTableView {{
    background: {C_CARD};
    border: 2px solid {C_BORDER};
    border-radius: {RADIUS_MD}px;
    gridline-color: {C_BORDER};
    selection-background-color: {C_ACCENT_MUTED};
    selection-color: {C_GREEN};
}}
QHeaderView::section {{
    background: {C_CARD2};
    color: {C_TEXT3};
    border: none;
    border-bottom: 2px solid {C_BORDER};
    padding: 12px 18px;
    font-size: 13px;
    font-weight: 600;
}}

/* ── Lista ────────────────────────────────────────────────────────────── */
QListWidget {{
    background: {C_CARD};
    border: 2px solid {C_BORDER};
    border-radius: {RADIUS_MD}px;
}}
QListWidget::item          {{ padding: 15px 21px; border-bottom: 1px solid {C_BORDER}; color: {C_TEXT2}; }}
QListWidget::item:selected {{ background: {C_ACCENT_MUTED}; color: {C_GREEN}; }}
QListWidget::item:hover    {{ background: {C_CARD2}; color: {C_TEXT}; }}

/* ── Labels tipográficos ──────────────────────────────────────────────── */
QLabel#h1       {{ font-size: 36px; font-weight: 800; color: {C_TEXT}; }}
QLabel#h2       {{ font-size: 26px; font-weight: 700; color: {C_TEXT}; }}
QLabel#h3       {{ font-size: 18px; font-weight: 700; color: {C_TEXT}; }}
QLabel#sub      {{ font-size: 14px; color: {C_TEXT3}; }}
QLabel#green    {{ color: {C_GREEN}; font-weight: 700; }}
QLabel#stat_val {{ font-size: 36px; font-weight: 800; color: {C_TEXT}; }}
QLabel#stat_lbl {{ font-size: 13px; color: {C_TEXT3}; }}

/* ── Frames ───────────────────────────────────────────────────────────── */
QFrame#card {{
    background: {C_CARD};
    border: 2px solid #555555;
    border-radius: {RADIUS_LG}px;
}}
QFrame#sep {{
    background: {C_BORDER};
    max-height: 2px;
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
    shadow(f, blur=24, opacity=140, offset_y=4)
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


def shadow(widget: QWidget, blur: int = 20, opacity: int = 80, offset_y: int = 4) -> QWidget:
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setColor(QColor(0, 0, 0, opacity))
    eff.setOffset(0, offset_y)
    widget.setGraphicsEffect(eff)
    return widget
