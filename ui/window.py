"""
ui/window.py
MainWindow: frameless window com titlebar customizada + navegação + QStackedWidget.
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, QThread
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from database import DatabaseConnection, seed_muscle_map
from engine import NormalizationEngine, PerformanceAnalyzer, Routine, RoutineManager
from ui.theme import C_BORDER, C_GREEN, C_SURFACE, C_TEXT2
from ui.titlebar import make_wm_buttons
from ui.screens.dashboard import DashboardTab
from ui.screens.workouts import WorkoutsTab
from ui.screens.active_workout import ActiveWorkoutScreen


# ---------------------------------------------------------------------------
# TitleBar da MainWindow
# ---------------------------------------------------------------------------

class _TitleBar(QWidget):
    """Topbar com logo, navegação e controles de janela."""

    def __init__(self, parent: QMainWindow):
        super().__init__(parent)
        self._win = parent

        self.setFixedHeight(52)
        self.setStyleSheet(
            f"background:{C_SURFACE}; border-bottom:1px solid {C_BORDER};"
        )
        # Permite que eventos de mouse passem para a MainWindow
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 12, 0)
        lay.setSpacing(8)

        logo_icon = QLabel("⚡")
        logo_icon.setStyleSheet(
            f"color:{C_GREEN}; font-size:18px; font-weight:900;"
            "background:transparent; border:none;"
        )
        logo_icon.setAttribute(Qt.WA_TransparentForMouseEvents)

        logo_text = QLabel("GYMNight")
        logo_text.setStyleSheet(
            "color:#fff; font-size:15px; font-weight:800; letter-spacing:1px;"
            "background:transparent; border:none;"
        )
        logo_text.setAttribute(Qt.WA_TransparentForMouseEvents)

        lay.addWidget(logo_icon)
        lay.addWidget(logo_text)
        lay.addStretch()

        self._nav_area = QHBoxLayout()
        self._nav_area.setSpacing(8)
        lay.addLayout(self._nav_area)
        lay.addStretch()

        lay.addWidget(make_wm_buttons(parent, show_minimize=True))

    def add_nav_button(self, btn: QPushButton):
        self._nav_area.addWidget(btn)


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GYMNight")
        self.setMinimumSize(900, 620)
        self.resize(1100, 720)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self._drag_pos: QPoint | None = None

        # Motor
        self._db       = DatabaseConnection("gymnight.db")
        self._rm       = RoutineManager(self._db)
        self._norm     = NormalizationEngine(self._db)
        self._analyzer = PerformanceAnalyzer(self._db)

        try:
            n = seed_muscle_map(self._db, "muscle_usage_map.md")
            if n > 0:
                print(f"[GYMNight] {n} exercícios importados")
        except FileNotFoundError:
            pass

        self._worker = QThread(self)
        self._analyzer.moveToThread(self._worker)
        self._worker.start()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._titlebar = _TitleBar(self)

        self._btn_dash     = QPushButton("Dashboard")
        self._btn_workouts = QPushButton("Treinos")
        for btn in (self._btn_dash, self._btn_workouts):
            btn.setFixedHeight(34)
        self._btn_dash.clicked.connect(lambda: self._navigate(0))
        self._btn_workouts.clicked.connect(lambda: self._navigate(1))
        self._titlebar.add_nav_button(self._btn_dash)
        self._titlebar.add_nav_button(self._btn_workouts)

        root.addWidget(self._titlebar)

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
        self._active_tab.finished.connect(self._dash_tab.on_workout_finished)

        self._navigate(0)

    # ------------------------------------------------------------------
    # Drag da janela — tratado na MainWindow para capturar todos os cliques
    # na área da titlebar independente dos widgets filhos
    # ------------------------------------------------------------------

    def _in_titlebar(self, pos: QPoint) -> bool:
        """Retorna True se a posição (em coords da janela) está na titlebar."""
        return pos.y() <= self._titlebar.height()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._in_titlebar(event.pos()):
            self._drag_pos = QCursor.pos() - self.pos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(QCursor.pos() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton and self._in_titlebar(event.pos()):
            if self.isMaximized():
                self.showNormal()
            else:
                self.showMaximized()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    # ------------------------------------------------------------------

    def _navigate(self, idx: int):
        active_style = (
            f"background:{C_GREEN}; color:#000; border:none;"
            f" border-radius:8px; padding:0 14px; font-weight:700;"
        )
        inactive_style = (
            f"background:transparent; color:{C_TEXT2};"
            f" border:1px solid {C_BORDER}; border-radius:8px; padding:0 14px;"
        )
        self._btn_dash.setStyleSheet(active_style if idx == 0 else inactive_style)
        self._btn_workouts.setStyleSheet(active_style if idx == 1 else inactive_style)
        if idx == 0:
            self._dash_tab.refresh()
        self._stack.setCurrentIndex(idx)

    def _go_active(self, routine: Routine, session_id: int):
        self._active_tab.load_routine(routine, session_id)
        self._btn_dash.setEnabled(False)
        self._btn_workouts.setEnabled(False)
        self._stack.setCurrentIndex(2)

    def _go_workouts(self, payload: dict = None):
        self._btn_dash.setEnabled(True)
        self._btn_workouts.setEnabled(True)
        self._workout_tab.reload()
        self._navigate(1)

    def closeEvent(self, event):
        self._worker.quit()
        self._worker.wait()
        self._db.close()
        super().closeEvent(event)
