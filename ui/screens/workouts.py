"""
ui/screens/workouts.py
Tela de Treinos: lista de rotinas com cards expansíveis.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from database import DatabaseConnection
from engine import NormalizationEngine, Routine, RoutineManager
from ui.dialogs import CreateWorkoutDialog
from ui.theme import label
from ui.widgets import RoutineCard


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

        # Lista de rotinas
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
            c = RoutineCard(r, exs)
            c.start_clicked.connect(self._on_start)
            self._list_lay.insertWidget(i, c)

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
        ex_ids = [self._norm.get_or_create(e["name"]).id for e in data["exercises"]]
        self._rm.create_routine(data["name"], ex_ids)
        self.reload()
