"""
ui/screens/workouts.py
Tela de Treinos: barra de pesquisa, lista de rotinas, botão + Cardio avulso.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from database import DatabaseConnection
from engine import NormalizationEngine, Routine, RoutineManager
from ui.dialogs import CreateWorkoutDialog
from ui.theme import (
    C_BORDER, C_CARD, C_CARD2, C_GREEN, C_GREEN_BG,
    C_TEXT, C_TEXT2, C_TEXT3, label,
)
from ui.widgets import RoutineCard


class WorkoutsTab(QWidget):
    start_workout  = Signal(object, int)   # (Routine, session_id)
    add_cardio_req = Signal()              # abre diálogo de cardio avulso

    def __init__(self, db: DatabaseConnection, rm: RoutineManager,
                 norm: NormalizationEngine, parent=None):
        super().__init__(parent)
        self._db       = db
        self._rm       = rm
        self._norm     = norm
        self._all_cards: list[tuple[Routine, RoutineCard]] = []
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        # ── Cabeçalho ────────────────────────────────────────────────────
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

        # Botão + Cardio (avulso, fora do treino)
        cardio_btn = QPushButton("+ Cardio")
        cardio_btn.setFixedHeight(38)
        cardio_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C_GREEN};
                border: 1px solid {C_GREEN};
                border-radius: 8px;
                padding: 0 16px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {C_GREEN_BG}; }}
            QPushButton:pressed {{ background: {C_GREEN}; color: #000; }}
        """)
        cardio_btn.clicked.connect(self._open_cardio)
        hdr.addWidget(cardio_btn)

        new_btn = QPushButton("+ Novo Treino")
        new_btn.setFixedHeight(38)
        new_btn.clicked.connect(self._create_workout)
        hdr.addWidget(new_btn)
        lay.addLayout(hdr)

        # ── Barra de pesquisa ─────────────────────────────────────────────
        search_row = QHBoxLayout()
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet(f"color:{C_TEXT3}; font-size:14px; padding-right:4px;")
        self._search = QLineEdit()
        self._search.setPlaceholderText("Pesquisar treino...")
        self._search.setFixedHeight(40)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {C_CARD};
                color: {C_TEXT};
                border: 1px solid {C_BORDER};
                border-radius: 10px;
                padding: 0 14px 0 36px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {C_GREEN};
            }}
        """)
        self._search.textChanged.connect(self._filter_routines)

        # Ícone de lupa sobreposto ao campo
        search_container = QWidget()
        search_container.setFixedHeight(40)
        sc_lay = QHBoxLayout(search_container)
        sc_lay.setContentsMargins(0, 0, 0, 0)
        sc_lay.setSpacing(0)
        sc_lay.addWidget(self._search)
        lay.addWidget(search_container)

        # ── Lista de rotinas ──────────────────────────────────────────────
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

    # ------------------------------------------------------------------
    # Pesquisa
    # ------------------------------------------------------------------

    def _filter_routines(self, query: str):
        """Filtra os cards de rotina pelo nome em tempo real."""
        q = query.strip().lower()
        for routine, card in self._all_cards:
            visible = q == "" or q in routine.name.lower()
            card.setVisible(visible)

    # ------------------------------------------------------------------
    # Cardio avulso
    # ------------------------------------------------------------------

    def _open_cardio(self):
        """Abre o diálogo de cardio sem precisar iniciar um treino."""
        from ui.screens.cardio_widget import CardioPickerDialog
        from PySide6.QtWidgets import QMessageBox as QMB
        dlg = CardioPickerDialog(parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        data = dlg.get_data()
        if not data:
            return
        # Cria sessão avulsa de cardio
        session_id = self._db.execute_write(
            "INSERT INTO workout_sessions DEFAULT VALUES"
        )
        self._db.execute_write(
            "INSERT INTO cardio_logs (session_id, cardio_type, duration_min, distance_km, pse) VALUES (?,?,?,?,?)",
            (session_id, data["cardio_type"], data["duration_min"],
             data.get("distance_km"), data.get("pse")),
        )
        # Encerra sessão imediatamente
        import time
        self._db.execute_write(
            "UPDATE workout_sessions SET duration_seconds=? WHERE id=?",
            (int(data["duration_min"] * 60), session_id),
        )
        QMB.information(
            self, "Cardio Registrado",
            f"✅ {data['cardio_type']}\n"
            f"⏱ {int(data['duration_min'])} min"
            + (f" · {data['distance_km']:.1f} km" if data.get("distance_km") else "")
            + f"\n💪 PSE {data['pse']}/10",
        )

    # ------------------------------------------------------------------
    # Reload e criação
    # ------------------------------------------------------------------

    def reload(self):
        self._all_cards.clear()
        while self._list_lay.count() > 1:
            item = self._list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        routines = self._rm.list_routines()
        if not routines:
            empty = label(
                "Nenhum treino criado ainda.\nClique em '+ Novo Treino' para começar.",
                "sub",
            )
            empty.setAlignment(Qt.AlignCenter)
            self._list_lay.insertWidget(0, empty)
            return

        for i, r in enumerate(routines):
            exs = self._rm.get_routine_exercises(r.id)
            c = RoutineCard(r, exs)
            c.start_clicked.connect(self._on_start)
            c.edit_clicked.connect(self._on_edit)
            self._list_lay.insertWidget(i, c)
            self._all_cards.append((r, c))

        # Reaplica filtro se houver texto na busca
        if self._search.text():
            self._filter_routines(self._search.text())

    def _on_start(self, routine: Routine):
        session_id = self._db.execute_write(
            "INSERT INTO workout_sessions (routine_id) VALUES (?)", (routine.id,)
        )
        self.start_workout.emit(routine, session_id)

    def _on_edit(self, routine: Routine):
        """Abre diálogo para editar nome e exercícios da rotina."""
        from ui.screens.edit_routine_dialog import EditRoutineDialog
        dlg = EditRoutineDialog(routine, self._rm, self._norm, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.reload()

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
