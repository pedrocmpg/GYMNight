"""
ui/window.py
MainWindow: topbar com navegação + QStackedWidget.
"""
from __future__ import annotations

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from database import DatabaseConnection, seed_muscle_map
from engine import NormalizationEngine, PerformanceAnalyzer, Routine, RoutineManager
from ui.theme import C_BORDER, C_GREEN, C_SURFACE, C_TEXT2
from ui.screens.dashboard import DashboardTab
from ui.screens.workouts import WorkoutsTab
from ui.screens.active_workout import ActiveWorkoutScreen


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

        # Layout raiz
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Topbar
        topbar = QWidget()
        topbar.setFixedHeight(52)
        topbar.setStyleSheet(f"background:{C_SURFACE}; border-bottom:1px solid {C_BORDER};")
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(20, 0, 20, 0)
        tb.setSpacing(8)

        logo_icon = QLabel("⚡")
        logo_icon.setStyleSheet(f"color:{C_GREEN}; font-size:18px;")
        logo_text = QLabel("GYMNight")
        logo_text.setStyleSheet("color:#fff; font-size:15px; font-weight:800; letter-spacing:1px;")
        tb.addWidget(logo_icon)
        tb.addWidget(logo_text)
        tb.addStretch()

        self._btn_dash     = QPushButton("⌂  Dashboard")
        self._btn_workouts = QPushButton("⚡  Treinos")
        for btn in [self._btn_dash, self._btn_workouts]:
            btn.setFixedHeight(34)
        self._btn_dash.clicked.connect(lambda: self._navigate(0))
        self._btn_workouts.clicked.connect(lambda: self._navigate(1))
        tb.addWidget(self._btn_dash)
        tb.addWidget(self._btn_workouts)
        root.addWidget(topbar)

        # Stack
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
        # Reatividade: ao finalizar treino, atualiza dashboard imediatamente
        self._active_tab.finished.connect(self._dash_tab.on_workout_finished)

        self._navigate(0)

    def _navigate(self, idx: int):
        active_style   = f"background:{C_GREEN}; color:#000; border:none; border-radius:8px; padding:0 14px; font-weight:700;"
        inactive_style = f"background:transparent; color:{C_TEXT2}; border:1px solid {C_BORDER}; border-radius:8px; padding:0 14px;"
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
