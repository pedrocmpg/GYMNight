"""
ui/screens/dashboard.py
Tela Dashboard: hero banner, stat cards, atividade semanal, treinos recentes.
"""
from __future__ import annotations
import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea,
    QVBoxLayout, QWidget,
)

from database import DatabaseConnection
from ui.theme import C_BORDER, C_CARD, C_GREEN, C_TEXT, C_TEXT3, card, label, separator
from ui.widgets import StatCard, WeekDayDot


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
        self._stat_treinos   = StatCard("⚡", "Treinos esta semana", "0", "Meta: 5")
        self._stat_volume    = StatCard("🎯", "Volume total", "0 kg", "kg levantados")
        self._stat_sequencia = StatCard("📈", "Sequência", "0", "dias seguidos")
        self._stat_duracao   = StatCard("⏱", "Duração média", "0 min", "por treino")
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
        today = datetime.datetime.now().weekday()
        for i, d in enumerate(["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]):
            days_row.addWidget(WeekDayDot(d, i <= today))
        act_lay.addLayout(days_row)
        lay.addWidget(act_card)

        # Treinos recentes
        rec_card = card()
        self._rec_lay = QVBoxLayout(rec_card)
        self._rec_lay.setContentsMargins(16, 16, 16, 16)
        self._rec_lay.setSpacing(0)
        self._rec_lay.addWidget(label("TREINOS RECENTES", "h3"))
        self._rec_lay.addSpacing(10)
        lay.addWidget(rec_card)
        lay.addStretch()

        scroll.setWidget(content)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def refresh(self):
        """Atualiza todos os dados do dashboard. Seguro chamar do main thread."""
        self._refresh_stats()
        self._refresh_recent()

    def on_workout_finished(self, payload: dict):
        """
        Slot conectado ao sinal finished do ActiveWorkoutScreen.
        Atualiza o dashboard imediatamente sem reload completo.
        payload: {session_id, volume_total, duration_seconds, routine_name}
        """
        if not payload:
            return
        # Atualiza stats e lista de recentes reativamente
        self._refresh_stats()
        self._refresh_recent()

    def _refresh_stats(self):
        row = self._db.fetchone(
            "SELECT COUNT(*) AS c FROM workout_sessions WHERE started_at >= strftime('%s','now','-7 days')"
        )
        self._stat_treinos.set_value(str(row["c"] if row else 0))

        row2 = self._db.fetchone("SELECT COALESCE(SUM(weight_kg*reps),0) AS v FROM workout_logs")
        vol = float(row2["v"]) if row2 else 0.0
        self._stat_volume.set_value(f"{vol/1000:.1f}k" if vol >= 1000 else f"{vol:.0f}")

        row3 = self._db.fetchone(
            "SELECT COALESCE(AVG(duration_seconds),0) AS d FROM workout_sessions WHERE duration_seconds IS NOT NULL"
        )
        avg_dur = int(row3["d"] if row3 else 0)
        self._stat_duracao.set_value(f"{avg_dur//60} min")

    def _refresh_recent(self):
        # Limpa itens antigos (mantém cabeçalho + spacing = 2 itens)
        while self._rec_lay.count() > 2:
            item = self._rec_lay.takeAt(2)
            if item.widget():
                item.widget().deleteLater()

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
                dt   = datetime.datetime.fromtimestamp(row["started_at"])
                diff = (datetime.datetime.now() - dt).days
                when = "Hoje" if diff == 0 else "Ontem" if diff == 1 else f"{diff} dias atrás"
                left = QVBoxLayout()
                left.addWidget(label(row["rname"] or "Treino livre", "h3"))
                left.addWidget(label(when, "sub"))
                item_lay.addLayout(left)
                item_lay.addStretch()
                dur = row["duration_seconds"] or 0
                item_lay.addWidget(label(f"{dur//60} min", "sub"))
                self._rec_lay.addWidget(item_w)
                self._rec_lay.addWidget(separator())
        else:
            self._rec_lay.addWidget(label("Nenhum treino registrado ainda.", "sub"))
