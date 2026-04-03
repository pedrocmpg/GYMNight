"""
main.py - GYMNight Desktop
Design inspirado no site gymnightweb.lovable.app
"""
from __future__ import annotations
import datetime, sys
from typing import Any

from PySide6.QtCore import Qt, QThread, QTimer, Signal, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QLinearGradient, QBrush, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFormLayout, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPushButton,
    QScrollArea, QSizePolicy, QSpinBox, QStackedWidget, QTabWidget,
    QTableView, QVBoxLayout, QWidget, QComboBox, QGridLayout,
    QGraphicsDropShadowEffect,
)

from database import DatabaseConnection, seed_muscle_map
from engine import Exercise, NormalizationEngine, PerformanceAnalyzer, Routine, RoutineManager
from models import (
    COL_EXERCISE, COL_REPS, COL_WEIGHT,
    ExerciseSearchDelegate, GhostValueDelegate, SuggestionRole, WorkoutEntryModel,
)

# ---------------------------------------------------------------------------
# Paleta de cores (baseada no site)
# ---------------------------------------------------------------------------
C_BG        = "#0a0a0a"
C_SURFACE   = "#141414"
C_CARD      = "#1a1a1a"
C_CARD2     = "#1e1e1e"
C_BORDER    = "#2a2a2a"
C_GREEN     = "#a3e635"   # lime neon do site
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
QTabBar::tab:selected {{
    color: {C_TEXT};
    border-bottom: 2px solid {C_GREEN};
}}
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

QPushButton#icon_btn {{
    background-color: {C_GREEN_BG};
    color: {C_GREEN};
    border: none;
    border-radius: 10px;
    padding: 10px;
    font-size: 16px;
    font-weight: 700;
}}

QLineEdit, QSpinBox, QComboBox {{
    background-color: {C_CARD};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border-color: {C_GREEN};
    outline: none;
}}
QLineEdit::placeholder {{ color: {C_TEXT3}; }}

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
    text-transform: uppercase;
    letter-spacing: 1px;
}}

QListWidget {{
    background: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: 8px;
}}
QListWidget::item {{ padding: 10px 14px; border-bottom: 1px solid {C_BORDER}; color: {C_TEXT2}; }}
QListWidget::item:selected {{ background: {C_GREEN_BG}; color: {C_GREEN}; }}
QListWidget::item:hover {{ background: #1e1e1e; color: {C_TEXT}; }}

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
QFrame#card_green {{
    background: {C_GREEN_BG};
    border: 1px solid {C_GREEN};
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

def shadow(widget: QWidget, radius=20, opacity=80):
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(radius)
    eff.setColor(QColor(0, 0, 0, opacity))
    eff.setOffset(0, 4)
    widget.setGraphicsEffect(eff)
    return widget


# ---------------------------------------------------------------------------
# StatCard — card de estatística (Dashboard)
# ---------------------------------------------------------------------------

class StatCard(QFrame):
    def __init__(self, icon: str, title: str, value: str, sub: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumWidth(160)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(6)

        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"color:{C_GREEN}; font-size:16px;")
        top.addWidget(icon_lbl)
        top.addStretch()
        top.addWidget(label(title, "stat_lbl"))
        lay.addLayout(top)

        self._val = label(value, "stat_val")
        lay.addWidget(self._val)
        if sub:
            lay.addWidget(label(sub, "sub"))

    def set_value(self, v: str):
        self._val.setText(v)


# ---------------------------------------------------------------------------
# WeekDayDot — bolinha de atividade semanal
# ---------------------------------------------------------------------------

class WeekDayDot(QWidget):
    def __init__(self, day: str, active: bool, parent=None):
        super().__init__(parent)
        self._active = active
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignCenter)

        dot = QLabel("⚡" if active else "—")
        dot.setAlignment(Qt.AlignCenter)
        dot.setFixedSize(40, 40)
        if active:
            dot.setStyleSheet(f"background:{C_GREEN}; color:#000; border-radius:10px; font-size:16px; font-weight:700;")
        else:
            dot.setStyleSheet(f"background:{C_CARD}; color:{C_TEXT3}; border-radius:10px; font-size:14px; border:1px solid {C_BORDER};")
        lay.addWidget(dot)

        d = label(day, "sub")
        d.setAlignment(Qt.AlignCenter)
        lay.addWidget(d)


# ---------------------------------------------------------------------------
# RoutineCard — card expansível de rotina (aba Treinos)
# ---------------------------------------------------------------------------

class RoutineCard(QFrame):
    start_clicked = Signal(object)  # Routine

    def __init__(self, routine: Routine, exercises: list, parent=None):
        super().__init__(parent)
        self._routine   = routine
        self._exercises = exercises
        self._expanded  = False
        self.setObjectName("card")
        self.setCursor(Qt.PointingHandCursor)
        self._build()

    def _build(self):
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setStyleSheet("background:transparent;")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(16, 14, 16, 14)

        icon = QLabel("⚡")
        icon.setFixedSize(36, 36)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"background:{C_GREEN_BG}; color:{C_GREEN}; border-radius:8px; font-size:16px; font-weight:700;")
        hdr_lay.addWidget(icon)
        hdr_lay.addSpacing(10)

        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = label(self._routine.name.upper(), "h3")
        info.addWidget(name_lbl)
        ex_names = ", ".join(e.canonical_name for e in self._exercises[:3])
        if len(self._exercises) > 3:
            ex_names += f" +{len(self._exercises)-3}"
        info.addWidget(label(ex_names, "sub"))
        hdr_lay.addLayout(info)
        hdr_lay.addStretch()

        # Botão iniciar
        self._start_btn = QPushButton("▶")
        self._start_btn.setFixedSize(32, 32)
        self._start_btn.setStyleSheet(f"background:{C_GREEN}; color:#000; border-radius:8px; font-size:14px; font-weight:700; padding:0;")
        self._start_btn.clicked.connect(lambda: self.start_clicked.emit(self._routine))
        hdr_lay.addWidget(self._start_btn)

        self._arrow = QLabel("›")
        self._arrow.setStyleSheet(f"color:{C_TEXT3}; font-size:20px; padding-left:8px;")
        hdr_lay.addWidget(self._arrow)

        self._root.addWidget(hdr)

        # Conteúdo expansível
        self._content = QWidget()
        self._content.hide()
        content_lay = QVBoxLayout(self._content)
        content_lay.setContentsMargins(16, 0, 16, 14)
        content_lay.setSpacing(0)

        content_lay.addWidget(separator())
        content_lay.addSpacing(10)

        # Cabeçalho da tabela
        hdr_row = QHBoxLayout()
        for txt, stretch in [("Exercício", 4), ("Séries", 1), ("Reps", 1), ("Descanso", 1)]:
            l = label(txt, "sub")
            hdr_row.addWidget(l, stretch)
        content_lay.addLayout(hdr_row)
        content_lay.addSpacing(6)

        for ex in self._exercises:
            row = QHBoxLayout()
            name = QLabel(ex.canonical_name.title())
            name.setStyleSheet(f"color:{C_TEXT}; font-weight:600;")
            row.addWidget(name, 4)
            for val in ["3", "8-12", "60s"]:
                row.addWidget(label(val, "sub"), 1)
            content_lay.addLayout(row)
            content_lay.addSpacing(4)

        self._root.addWidget(self._content)

        # Clique no header expande
        hdr.mousePressEvent = lambda e: self._toggle()

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._arrow.setText("∨" if self._expanded else "›")


# ---------------------------------------------------------------------------
# Diálogo: Criar Treino (estilo site)
# ---------------------------------------------------------------------------

class CreateWorkoutDialog(QDialog):
    def __init__(self, norm: NormalizationEngine, parent=None):
        super().__init__(parent)
        self._norm = norm
        self._ex_widgets: list[dict] = []
        self.setWindowTitle("Criar Treino")
        self.setMinimumWidth(500)
        self.setMaximumHeight(700)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        # Título
        lay.addWidget(label("CRIAR TREINO", "h2"))
        lay.addWidget(label("Monte seu treino personalizado com exercícios, séries e repetições.", "sub"))

        sep = separator()
        lay.addWidget(sep)

        # Scroll area para o formulário
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        form_w = QWidget()
        self._form_lay = QVBoxLayout(form_w)
        self._form_lay.setSpacing(14)
        scroll.setWidget(form_w)
        lay.addWidget(scroll)

        # Nome
        self._form_lay.addWidget(label("Nome do treino", "h3"))
        self._name = QLineEdit()
        self._name.setPlaceholderText("Ex: Treino D — Ombro")
        self._form_lay.addWidget(self._name)

        # Dia + Músculos
        row = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(label("Dia(s)", "h3"))
        self._days = QLineEdit()
        self._days.setPlaceholderText("Ex: Segunda")
        col1.addWidget(self._days)
        row.addLayout(col1)

        col2 = QVBoxLayout()
        col2.addWidget(label("Músculos", "h3"))
        self._muscles = QLineEdit()
        self._muscles.setPlaceholderText("Ex: Ombro & Trapézio")
        col2.addWidget(self._muscles)
        row.addLayout(col2)
        self._form_lay.addLayout(row)

        # Exercícios
        self._form_lay.addWidget(label("Exercícios", "h3"))
        self._ex_container = QVBoxLayout()
        self._ex_container.setSpacing(10)
        self._form_lay.addLayout(self._ex_container)
        self._add_exercise_block()

        # Botão adicionar exercício
        add_ex = QPushButton("+ Adicionar exercício")
        add_ex.setObjectName("ghost")
        add_ex.clicked.connect(self._add_exercise_block)
        self._form_lay.addWidget(add_ex)

        # Salvar
        save = QPushButton("Salvar Treino")
        save.setMinimumHeight(44)
        save.clicked.connect(self.accept)
        lay.addWidget(save)

    def _add_exercise_block(self):
        idx = len(self._ex_widgets) + 1
        block = QFrame()
        block.setObjectName("card")
        block_lay = QVBoxLayout(block)
        block_lay.setContentsMargins(12, 12, 12, 12)
        block_lay.setSpacing(8)

        block_lay.addWidget(label(f"Exercício {idx}", "sub"))
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("Nome do exercício")
        block_lay.addWidget(name_edit)

        row = QHBoxLayout()
        series = QSpinBox()
        series.setRange(1, 20)
        series.setValue(3)
        reps = QLineEdit("10-12")
        rest = QLineEdit("60s")
        for w, lbl in [(series, "Séries"), (reps, "Reps"), (rest, "Descanso")]:
            col = QVBoxLayout()
            col.addWidget(label(lbl, "sub"))
            col.addWidget(w)
            row.addLayout(col)
        block_lay.addLayout(row)

        self._ex_container.addWidget(block)
        self._ex_widgets.append({"name": name_edit, "series": series, "reps": reps, "rest": rest})

    def get_data(self) -> dict:
        exercises = []
        for w in self._ex_widgets:
            n = w["name"].text().strip()
            if n:
                exercises.append({
                    "name": n,
                    "series": w["series"].value(),
                    "reps": w["reps"].text(),
                    "rest": w["rest"].text(),
                })
        return {
            "name": self._name.text().strip(),
            "days": self._days.text().strip(),
            "muscles": self._muscles.text().strip(),
            "exercises": exercises,
        }



# ---------------------------------------------------------------------------
# Tela de Treino Ativo — tabs por exercício + card de séries
# ---------------------------------------------------------------------------

class ActiveWorkoutScreen(QWidget):
    finished = Signal()

    def __init__(self, db: DatabaseConnection, rm: RoutineManager,
                 analyzer: PerformanceAnalyzer, norm: NormalizationEngine, parent=None):
        super().__init__(parent)
        self._db       = db
        self._rm       = rm
        self._analyzer = analyzer
        self._norm     = norm
        self._session_id: int | None = None
        self._exercises: list[Exercise] = []
        self._current_ex_idx = 0
        self._series_data: list[list[dict]] = []  # [ex_idx][serie_idx] = {weight, reps, done}
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        back_btn = QPushButton("‹ Voltar")
        back_btn.setObjectName("ghost")
        back_btn.setFixedWidth(90)
        back_btn.clicked.connect(self._confirm_back)
        hdr.addWidget(back_btn)
        hdr.addStretch()
        self._series_counter = label("0/0 séries", "sub")
        hdr.addWidget(self._series_counter)
        lay.addLayout(hdr)

        # Título do treino
        self._title = label("TREINO", "h1")
        lay.addWidget(self._title)

        # Barra de progresso
        self._progress_bar = QFrame()
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setStyleSheet(f"background:{C_BORDER}; border-radius:2px;")
        self._progress_fill = QFrame(self._progress_bar)
        self._progress_fill.setFixedHeight(4)
        self._progress_fill.setStyleSheet(f"background:{C_GREEN}; border-radius:2px;")
        self._progress_fill.setFixedWidth(0)
        lay.addWidget(self._progress_bar)

        # Tabs de exercícios (scroll horizontal)
        self._ex_tabs_scroll = QScrollArea()
        self._ex_tabs_scroll.setFixedHeight(48)
        self._ex_tabs_scroll.setWidgetResizable(True)
        self._ex_tabs_scroll.setFrameShape(QFrame.NoFrame)
        self._ex_tabs_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._ex_tabs_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._ex_tabs_w = QWidget()
        self._ex_tabs_lay = QHBoxLayout(self._ex_tabs_w)
        self._ex_tabs_lay.setContentsMargins(0, 0, 0, 0)
        self._ex_tabs_lay.setSpacing(8)
        self._ex_tabs_lay.addStretch()
        self._ex_tabs_scroll.setWidget(self._ex_tabs_w)
        lay.addWidget(self._ex_tabs_scroll)

        # Card do exercício atual
        self._ex_card = card()
        ex_card_lay = QVBoxLayout(self._ex_card)
        ex_card_lay.setContentsMargins(20, 20, 20, 20)
        ex_card_lay.setSpacing(14)

        # Header do card
        card_hdr = QHBoxLayout()
        self._ex_icon = QLabel("⚡")
        self._ex_icon.setFixedSize(44, 44)
        self._ex_icon.setAlignment(Qt.AlignCenter)
        self._ex_icon.setStyleSheet(f"background:{C_GREEN_BG}; color:{C_GREEN}; border-radius:10px; font-size:20px;")
        card_hdr.addWidget(self._ex_icon)
        card_hdr.addSpacing(12)

        card_info = QVBoxLayout()
        card_info.setSpacing(2)
        self._ex_name_lbl = label("", "h2")
        self._ex_meta_lbl = label("", "sub")
        card_info.addWidget(self._ex_name_lbl)
        card_info.addWidget(self._ex_meta_lbl)
        card_hdr.addLayout(card_info)
        card_hdr.addStretch()
        self._ex_progress_lbl = label("0/4", "green")
        self._ex_progress_lbl.setStyleSheet(f"color:{C_GREEN}; font-size:18px; font-weight:800;")
        card_hdr.addWidget(self._ex_progress_lbl)
        ex_card_lay.addLayout(card_hdr)

        # Cabeçalho das séries
        series_hdr = QHBoxLayout()
        for txt, stretch in [("Série", 1), ("Peso (kg)", 3), ("Reps", 3), ("", 1)]:
            l = label(txt, "sub")
            series_hdr.addWidget(l, stretch)
        ex_card_lay.addLayout(series_hdr)

        # Container das séries
        self._series_container = QVBoxLayout()
        self._series_container.setSpacing(8)
        ex_card_lay.addLayout(self._series_container)

        lay.addWidget(self._ex_card)
        lay.addStretch()

        # Botões Anterior / Próximo
        nav = QHBoxLayout()
        self._prev_btn = QPushButton("Anterior")
        self._prev_btn.setObjectName("ghost")
        self._prev_btn.setMinimumHeight(44)
        self._prev_btn.clicked.connect(self._prev_exercise)

        self._next_btn = QPushButton("Próximo")
        self._next_btn.setMinimumHeight(44)
        self._next_btn.clicked.connect(self._next_exercise)

        nav.addWidget(self._prev_btn, 1)
        nav.addWidget(self._next_btn, 2)
        lay.addLayout(nav)

    def load_routine(self, routine: Routine, session_id: int):
        self._session_id = session_id
        self._exercises  = self._rm.get_routine_exercises(routine.id)
        self._current_ex_idx = 0
        self._title.setText(routine.name.upper())

        # Inicializa dados de séries (4 séries por exercício por padrão)
        self._series_data = []
        for _ in self._exercises:
            self._series_data.append([
                {"weight": "", "reps": "", "done": False} for _ in range(4)
            ])

        self._build_ex_tabs()
        self._show_exercise(0)

    def _build_ex_tabs(self):
        # Limpa tabs antigas
        while self._ex_tabs_lay.count() > 1:
            item = self._ex_tabs_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, ex in enumerate(self._exercises):
            short = ex.canonical_name.title()
            if len(short) > 16:
                short = short[:14] + "…"
            btn = QPushButton(f"{i+1}. {short}")
            btn.setCheckable(True)
            btn.setFixedHeight(34)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {C_CARD};
                    color: {C_TEXT3};
                    border: 1px solid {C_BORDER};
                    border-radius: 17px;
                    padding: 0 14px;
                    font-size: 12px;
                    font-weight: 600;
                }}
                QPushButton:checked {{
                    background: {C_GREEN};
                    color: #000;
                    border-color: {C_GREEN};
                }}
            """)
            btn.clicked.connect(lambda _, idx=i: self._show_exercise(idx))
            self._ex_tabs_lay.insertWidget(i, btn)

    def _show_exercise(self, idx: int):
        if not self._exercises:
            return
        self._current_ex_idx = idx
        ex = self._exercises[idx]

        # Atualiza tabs
        for i in range(len(self._exercises)):
            item = self._ex_tabs_lay.itemAt(i)
            if item and item.widget():
                item.widget().setChecked(i == idx)

        # Atualiza card
        self._ex_name_lbl.setText(ex.canonical_name.upper())
        self._ex_meta_lbl.setText(f"4 séries × 8-12 reps — Descanso: 60s")

        series = self._series_data[idx]
        done_count = sum(1 for s in series if s["done"])
        self._ex_progress_lbl.setText(f"{done_count}/{len(series)}")

        # Reconstrói linhas de séries
        while self._series_container.count():
            item = self._series_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for s_idx, s in enumerate(series):
            row_w = QWidget()
            row_lay = QHBoxLayout(row_w)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(8)

            num = label(str(s_idx + 1), "sub")
            num.setFixedWidth(30)
            row_lay.addWidget(num, 1)

            weight_edit = QLineEdit(s["weight"])
            weight_edit.setPlaceholderText("0")
            weight_edit.setAlignment(Qt.AlignCenter)
            weight_edit.textChanged.connect(lambda v, i=idx, j=s_idx: self._update_series(i, j, "weight", v))
            row_lay.addWidget(weight_edit, 3)

            reps_edit = QLineEdit(s["reps"])
            reps_edit.setPlaceholderText("0")
            reps_edit.setAlignment(Qt.AlignCenter)
            reps_edit.textChanged.connect(lambda v, i=idx, j=s_idx: self._update_series(i, j, "reps", v))
            row_lay.addWidget(reps_edit, 3)

            check_btn = QPushButton("✓")
            check_btn.setFixedSize(40, 40)
            check_btn.setCheckable(True)
            check_btn.setChecked(s["done"])
            self._style_check_btn(check_btn, s["done"])
            check_btn.clicked.connect(lambda checked, i=idx, j=s_idx, b=check_btn: self._toggle_done(i, j, checked, b))
            row_lay.addWidget(check_btn, 1)

            self._series_container.addWidget(row_w)

        # Atualiza progresso geral
        self._update_progress()
        self._prev_btn.setEnabled(idx > 0)
        self._next_btn.setText("Finalizar" if idx == len(self._exercises) - 1 else "Próximo")

    def _style_check_btn(self, btn: QPushButton, done: bool):
        if done:
            btn.setStyleSheet(f"background:{C_GREEN}; color:#000; border-radius:10px; font-size:16px; font-weight:700; border:none;")
        else:
            btn.setStyleSheet(f"background:{C_CARD2}; color:{C_TEXT3}; border-radius:10px; font-size:16px; border:1px solid {C_BORDER};")

    def _update_series(self, ex_idx: int, s_idx: int, key: str, val: str):
        self._series_data[ex_idx][s_idx][key] = val

    def _toggle_done(self, ex_idx: int, s_idx: int, checked: bool, btn: QPushButton):
        self._series_data[ex_idx][s_idx]["done"] = checked
        self._style_check_btn(btn, checked)
        series = self._series_data[ex_idx]
        done_count = sum(1 for s in series if s["done"])
        self._ex_progress_lbl.setText(f"{done_count}/{len(series)}")
        self._update_progress()
        # Commit no banco
        if checked:
            s = self._series_data[ex_idx][s_idx]
            try:
                w = float(s["weight"]) if s["weight"] else 0.0
                r = int(s["reps"]) if s["reps"] else 0
                if w > 0 and r > 0 and self._session_id:
                    ex = self._exercises[ex_idx]
                    self._db.execute_write(
                        "INSERT INTO workout_logs (exercise_id, session_id, weight_kg, reps) VALUES (?,?,?,?)",
                        (ex.id, self._session_id, w, r),
                    )
            except (ValueError, TypeError):
                pass

    def _update_progress(self):
        total = sum(len(s) for s in self._series_data)
        done  = sum(sum(1 for x in s if x["done"]) for s in self._series_data)
        self._series_counter.setText(f"{done}/{total} séries")
        if total > 0:
            w = int(self._progress_bar.width() * done / total)
            self._progress_fill.setFixedWidth(w)

    def _prev_exercise(self):
        if self._current_ex_idx > 0:
            self._show_exercise(self._current_ex_idx - 1)

    def _next_exercise(self):
        if self._current_ex_idx < len(self._exercises) - 1:
            self._show_exercise(self._current_ex_idx + 1)
        else:
            self._finish()

    def _finish(self):
        if QMessageBox.question(self, "Finalizar", "Encerrar sessão?",
                                QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        duration = self._rm.end_session(self._session_id) if self._session_id else 0
        row = self._db.fetchone(
            "SELECT COALESCE(SUM(weight_kg*reps),0) AS v FROM workout_logs WHERE session_id=?",
            (self._session_id,),
        )
        vol = float(row["v"]) if row else 0.0
        mins, secs = divmod(duration, 60)
        QMessageBox.information(self, "Treino Finalizado",
            f"Volume Total: {vol:.0f} kg\nDuração: {mins:02d}:{secs:02d}")
        self._session_id = None
        self.finished.emit()

    def _confirm_back(self):
        if QMessageBox.question(self, "Voltar", "Abandonar o treino atual?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self._session_id = None
            self.finished.emit()



# ---------------------------------------------------------------------------
# Aba Dashboard
# ---------------------------------------------------------------------------

class DashboardTab(QWidget):
    def __init__(self, db: DatabaseConnection, parent=None):
        super().__init__(parent)
        self._db = db
        self._build()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)

        # Hero banner
        hero = QFrame()
        hero.setFixedHeight(140)
        hero.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #0a1a0a, stop:0.5 #0d2010, stop:1 #0a0a0a);
            border-radius: 12px;
            border: 1px solid {C_BORDER};
        """)
        hero_lay = QVBoxLayout(hero)
        hero_lay.setContentsMargins(24, 20, 24, 20)
        hero_lay.setSpacing(4)
        hero_title = QLabel("BOM TREINO, <span style='color:#a3e635'>PEDRO</span>")
        hero_title.setTextFormat(Qt.RichText)
        hero_title.setStyleSheet("font-size:28px; font-weight:800; color:#fff;")
        hero_lay.addWidget(hero_title)
        hero_lay.addWidget(label("75kg · 175cm · Meta: Hipertrofia", "sub"))
        lay.addWidget(hero)

        # Stat cards
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self._stat_treinos  = StatCard("⚡", "Treinos esta semana", "0", "Meta: 5")
        self._stat_volume   = StatCard("🎯", "Volume total", "0 kg", "kg levantados")
        self._stat_sequencia = StatCard("📈", "Sequência", "0", "dias seguidos")
        self._stat_duracao  = StatCard("⏱", "Duração média", "0 min", "por treino")
        for s in [self._stat_treinos, self._stat_volume, self._stat_sequencia, self._stat_duracao]:
            stats_row.addWidget(s)
        lay.addLayout(stats_row)

        # Atividade semanal
        act_card = card()
        act_lay = QVBoxLayout(act_card)
        act_lay.setContentsMargins(16, 16, 16, 16)
        act_lay.setSpacing(12)
        act_lay.addWidget(label("ATIVIDADE SEMANAL", "h3"))
        days_row = QHBoxLayout()
        days_row.setSpacing(8)
        today = datetime.datetime.now().weekday()  # 0=seg
        day_names = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
        for i, d in enumerate(day_names):
            days_row.addWidget(WeekDayDot(d, i <= today))
        act_lay.addLayout(days_row)
        lay.addWidget(act_card)

        # Treinos recentes
        rec_card = card()
        rec_lay = QVBoxLayout(rec_card)
        rec_lay.setContentsMargins(16, 16, 16, 16)
        rec_lay.setSpacing(0)
        rec_lay.addWidget(label("TREINOS RECENTES", "h3"))
        rec_lay.addSpacing(10)

        rows = self._db.fetchall(
            """SELECT ws.id, ws.started_at, ws.duration_seconds, r.name AS rname
               FROM workout_sessions ws
               LEFT JOIN routines r ON ws.routine_id = r.id
               ORDER BY ws.started_at DESC LIMIT 5"""
        )
        if rows:
            for row in rows:
                item_w = QWidget()
                item_lay = QHBoxLayout(item_w)
                item_lay.setContentsMargins(0, 10, 0, 10)
                dt = datetime.datetime.fromtimestamp(row["started_at"])
                diff = (datetime.datetime.now() - dt).days
                when = "Hoje" if diff == 0 else "Ontem" if diff == 1 else f"{diff} dias atrás"
                left = QVBoxLayout()
                left.addWidget(label(row["rname"] or "Treino livre", "h3"))
                left.addWidget(label(when, "sub"))
                item_lay.addLayout(left)
                item_lay.addStretch()
                dur = row["duration_seconds"] or 0
                item_lay.addWidget(label(f"{dur//60} min", "sub"))
                rec_lay.addWidget(item_w)
                rec_lay.addWidget(separator())
        else:
            rec_lay.addWidget(label("Nenhum treino registrado ainda.", "sub"))

        lay.addWidget(rec_card)
        lay.addStretch()

        scroll.setWidget(content)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def refresh(self):
        # Atualiza stats
        row = self._db.fetchone(
            "SELECT COUNT(*) AS c FROM workout_sessions WHERE started_at >= strftime('%s','now','-7 days')"
        )
        self._stat_treinos.set_value(str(row["c"] if row else 0))
        row2 = self._db.fetchone(
            "SELECT COALESCE(SUM(weight_kg*reps),0) AS v FROM workout_logs"
        )
        vol = float(row2["v"]) if row2 else 0.0
        self._stat_volume.set_value(f"{vol/1000:.1f}k" if vol >= 1000 else f"{vol:.0f}")


# ---------------------------------------------------------------------------
# Aba Treinos
# ---------------------------------------------------------------------------

class WorkoutsTab(QWidget):
    start_workout = Signal(object, int)  # (Routine, session_id)

    def __init__(self, db: DatabaseConnection, rm: RoutineManager,
                 norm: NormalizationEngine, parent=None):
        super().__init__(parent)
        self._db   = db
        self._rm   = rm
        self._norm = norm
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        # Header
        hdr = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(2)
        h = QLabel("SEUS <span style='color:#a3e635'>TREINOS</span>")
        h.setTextFormat(Qt.RichText)
        h.setStyleSheet("font-size:26px; font-weight:800; color:#fff;")
        left.addWidget(h)
        left.addWidget(label("Divisão ABC + seus treinos personalizados", "sub"))
        hdr.addLayout(left)
        hdr.addStretch()
        new_btn = QPushButton("+ Novo Treino")
        new_btn.setFixedHeight(38)
        new_btn.clicked.connect(self._create_workout)
        hdr.addWidget(new_btn)
        lay.addLayout(hdr)

        # Lista de rotinas (scroll)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self._list_w = QWidget()
        self._list_lay = QVBoxLayout(self._list_w)
        self._list_lay.setContentsMargins(0, 0, 0, 0)
        self._list_lay.setSpacing(10)
        self._list_lay.addStretch()
        scroll.setWidget(self._list_w)
        lay.addWidget(scroll)

        self.reload()

    def reload(self):
        while self._list_lay.count() > 1:
            item = self._list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        routines = self._rm.list_routines()
        if not routines:
            empty = label("Nenhum treino criado ainda.\nClique em '+ Novo Treino' para começar.", "sub")
            empty.setAlignment(Qt.AlignCenter)
            self._list_lay.insertWidget(0, empty)
            return

        for i, r in enumerate(routines):
            exs = self._rm.get_routine_exercises(r.id)
            card_w = RoutineCard(r, exs)
            card_w.start_clicked.connect(self._on_start)
            self._list_lay.insertWidget(i, card_w)

    def _on_start(self, routine: Routine):
        session_id = self._db.execute_write(
            "INSERT INTO workout_sessions (routine_id) VALUES (?)", (routine.id,)
        )
        self.start_workout.emit(routine, session_id)

    def _create_workout(self):
        dlg = CreateWorkoutDialog(self._norm, parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.get_data()
        if not data["name"] or not data["exercises"]:
            QMessageBox.warning(self, "Atenção", "Informe nome e ao menos um exercício.")
            return
        # Cria exercícios e rotina
        ex_ids = []
        for ex_data in data["exercises"]:
            ex = self._norm.get_or_create(ex_data["name"])
            ex_ids.append(ex.id)
        self._rm.create_routine(data["name"], ex_ids)
        self.reload()


# ---------------------------------------------------------------------------
# Janela Principal
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GYMNight")
        self.setMinimumSize(900, 620)
        self.resize(1100, 720)

        # Motor
        self._db       = DatabaseConnection("gymnight.db")
        self._rm       = RoutineManager(self._db)
        self._norm     = NormalizationEngine(self._db)
        self._analyzer = PerformanceAnalyzer(self._db)

        # Seed automático
        try:
            n = seed_muscle_map(self._db, "muscle_usage_map.md")
            if n > 0:
                print(f"[GYMNight] {n} exercícios importados")
        except FileNotFoundError:
            pass

        # Worker thread
        self._worker = QThread(self)
        self._analyzer.moveToThread(self._worker)
        self._worker.start()

        # Widget central
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Topbar ──────────────────────────────────────────────────────
        topbar = QWidget()
        topbar.setFixedHeight(52)
        topbar.setStyleSheet(f"background:{C_SURFACE}; border-bottom:1px solid {C_BORDER};")
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(20, 0, 20, 0)

        logo_icon = QLabel("⚡")
        logo_icon.setStyleSheet(f"color:{C_GREEN}; font-size:18px;")
        logo_text = QLabel("GYMNight")
        logo_text.setStyleSheet(f"color:{C_TEXT}; font-size:15px; font-weight:800; letter-spacing:1px;")
        tb.addWidget(logo_icon)
        tb.addWidget(logo_text)
        tb.addStretch()

        self._btn_dash     = QPushButton("⌂  Dashboard")
        self._btn_workouts = QPushButton("⚡  Treinos")
        for btn in [self._btn_dash, self._btn_workouts]:
            btn.setFixedHeight(34)
        self._btn_dash.setObjectName("ghost")
        self._btn_workouts.setObjectName("ghost")
        self._btn_dash.clicked.connect(lambda: self._navigate(0))
        self._btn_workouts.clicked.connect(lambda: self._navigate(1))
        tb.addWidget(self._btn_dash)
        tb.addWidget(self._btn_workouts)
        root.addWidget(topbar)

        # ── Stack ────────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._dash_tab    = DashboardTab(self._db)
        self._workout_tab = WorkoutsTab(self._db, self._rm, self._norm)
        self._active_tab  = ActiveWorkoutScreen(self._db, self._rm, self._analyzer, self._norm)

        self._stack.addWidget(self._dash_tab)    # 0
        self._stack.addWidget(self._workout_tab) # 1
        self._stack.addWidget(self._active_tab)  # 2

        self._workout_tab.start_workout.connect(self._go_active)
        self._active_tab.finished.connect(self._go_workouts)

        self._navigate(0)

    def _navigate(self, idx: int):
        self._btn_dash.setStyleSheet(
            f"background:{C_GREEN}; color:#000; border:none; border-radius:8px; padding:0 14px; font-weight:700;"
            if idx == 0 else
            f"background:transparent; color:{C_TEXT2}; border:1px solid {C_BORDER}; border-radius:8px; padding:0 14px;"
        )
        self._btn_workouts.setStyleSheet(
            f"background:{C_GREEN}; color:#000; border:none; border-radius:8px; padding:0 14px; font-weight:700;"
            if idx == 1 else
            f"background:transparent; color:{C_TEXT2}; border:1px solid {C_BORDER}; border-radius:8px; padding:0 14px;"
        )
        if idx == 0:
            self._dash_tab.refresh()
        self._stack.setCurrentIndex(idx)

    def _go_active(self, routine: Routine, session_id: int):
        self._active_tab.load_routine(routine, session_id)
        self._btn_dash.setEnabled(False)
        self._btn_workouts.setEnabled(False)
        self._stack.setCurrentIndex(2)

    def _go_workouts(self):
        self._btn_dash.setEnabled(True)
        self._btn_workouts.setEnabled(True)
        self._workout_tab.reload()
        self._navigate(1)

    def closeEvent(self, event):
        self._worker.quit()
        self._worker.wait()
        self._db.close()
        super().closeEvent(event)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_QSS)
    MainWindow().show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
