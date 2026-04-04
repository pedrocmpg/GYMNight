"""
ui/widgets.py
Widgets reutilizáveis: StatCard, WeekDayDot, MuscleBar, RoutineCard.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from engine import Exercise, Routine
from ui.theme import (
    C_BG, C_BORDER, C_CARD, C_CARD2, C_GREEN, C_GREEN_BG,
    C_TEXT, C_TEXT2, C_TEXT3, card, label, separator,
)


# ---------------------------------------------------------------------------
# StatCard
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
# WeekDayDot
# ---------------------------------------------------------------------------

class WeekDayDot(QWidget):
    def __init__(self, day: str, active: bool, parent=None):
        super().__init__(parent)
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
# MuscleBar (Heat Map)
# ---------------------------------------------------------------------------

class MuscleBar(QWidget):
    def __init__(self, name: str, value: float, max_value: float, parent=None):
        super().__init__(parent)
        self._name  = name
        self._value = value
        self._max   = max_value if max_value > 0 else 1
        self.setFixedHeight(38)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        ratio = self._value / self._max
        p.fillRect(0, 0, w, h, QColor(C_CARD))
        bar_w = int((w - 130) * ratio)
        if bar_w > 0:
            c = QColor(C_GREEN)
            c.setAlpha(int(70 + 185 * ratio))
            p.fillRect(130, 5, bar_w, h - 10, c)
        p.setPen(QColor(C_TEXT2))
        p.setFont(QFont("Consolas", 10))
        p.drawText(4, 0, 122, h, Qt.AlignVCenter | Qt.AlignLeft, self._name)
        p.setPen(QColor(C_GREEN))
        p.drawText(w - 90, 0, 86, h, Qt.AlignVCenter | Qt.AlignRight, f"{self._value:.0f} kg")


# ---------------------------------------------------------------------------
# RoutineCard
# ---------------------------------------------------------------------------

class RoutineCard(QFrame):
    start_clicked = Signal(object)  # Routine

    def __init__(self, routine: Routine, exercises: list[Exercise], parent=None):
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
        info.addWidget(label(self._routine.name.upper(), "h3"))
        ex_names = ", ".join(e.canonical_name for e in self._exercises[:3])
        if len(self._exercises) > 3:
            ex_names += f" +{len(self._exercises)-3}"
        info.addWidget(label(ex_names, "sub"))
        hdr_lay.addLayout(info)
        hdr_lay.addStretch()

        start_btn = QPushButton("▶")
        start_btn.setFixedSize(32, 32)
        start_btn.setStyleSheet(f"background:{C_GREEN}; color:#000; border-radius:8px; font-size:14px; font-weight:700; padding:0;")
        start_btn.clicked.connect(lambda: self.start_clicked.emit(self._routine))
        hdr_lay.addWidget(start_btn)

        self._arrow = QLabel("›")
        self._arrow.setStyleSheet(f"color:{C_TEXT3}; font-size:20px; padding-left:8px;")
        hdr_lay.addWidget(self._arrow)

        self._root.addWidget(hdr)

        # Conteúdo expansível
        self._content = QWidget()
        self._content.hide()
        c_lay = QVBoxLayout(self._content)
        c_lay.setContentsMargins(16, 0, 16, 14)
        c_lay.setSpacing(0)
        c_lay.addWidget(separator())
        c_lay.addSpacing(10)

        hdr_row = QHBoxLayout()
        for txt, stretch in [("Exercício", 4), ("Séries", 1), ("Reps", 1), ("Descanso", 1)]:
            hdr_row.addWidget(label(txt, "sub"), stretch)
        c_lay.addLayout(hdr_row)
        c_lay.addSpacing(6)

        for ex in self._exercises:
            row = QHBoxLayout()
            name = QLabel(ex.canonical_name.title())
            name.setStyleSheet(f"color:{C_TEXT}; font-weight:600;")
            row.addWidget(name, 4)
            for val in ["3", "8-12", "60s"]:
                row.addWidget(label(val, "sub"), 1)
            c_lay.addLayout(row)
            c_lay.addSpacing(4)

        self._root.addWidget(self._content)
        hdr.mousePressEvent = lambda e: self._toggle()

    def _toggle(self):
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._arrow.setText("∨" if self._expanded else "›")
