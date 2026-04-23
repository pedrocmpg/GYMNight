"""
ui/screens/dashboard.py
Tela Dashboard: hero banner, stat cards, atividade semanal, treinos recentes.
"""
from __future__ import annotations
import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPixmap, QLinearGradient, QColor
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea,
    QVBoxLayout, QWidget,
)

from database import DatabaseConnection
from ui.theme import C_GREEN, RADIUS_LG
import qtawesome as qta


class _HeroBanner(QWidget):
    """Widget com imagem de fundo e degradê."""

    _IMG_PATH = "assets/images/FUNDO HEADER.png"
    _RADIUS   = 16

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap(self._IMG_PATH)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainterPath
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        r = self._RADIUS
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), r, r)
        painter.setClipPath(path)

        if not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            x = (scaled.width()  - self.width())  // 2
            y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, self.width(), self.height())
        else:
            painter.fillRect(self.rect(), QColor("#1a1a1a"))

        for grad_args, rect in [
            ((0, 0, 100, 0), (0, 0, 100, self.height())),
            ((self.width(), 0, self.width() - 100, 0), (self.width() - 100, 0, 100, self.height())),
            ((0, 0, 0, 80), (0, 0, self.width(), 80)),
            ((0, self.height(), 0, self.height() - 80), (0, self.height() - 80, self.width(), 80)),
        ]:
            grad = QLinearGradient(*grad_args)
            grad.setColorAt(0, QColor(0, 0, 0, 180))
            grad.setColorAt(1, QColor(0, 0, 0, 0))
            painter.fillRect(*rect, grad)

        painter.end()


class _StatCard(QFrame):
    def __init__(self, icon_name: str, title: str, value: str, subtitle: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { background:#1a1a1a; border:1px solid #2a2a2a; border-radius:12px; }")
        self.setMinimumWidth(200)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        
        hdr = QHBoxLayout()
        hdr.setSpacing(10)
        
        icon = QLabel()
        icon.setPixmap(qta.icon(icon_name, color=C_GREEN).pixmap(20, 20))
        hdr.addWidget(icon)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color:#6b7280; font-size:13px; font-weight:600; background:transparent; border:none;")
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        
        lay.addLayout(hdr)
        
        self._val = QLabel(value)
        self._val.setStyleSheet("color:#fff; font-size:36px; font-weight:800; background:transparent; border:none;")
        lay.addWidget(self._val)
        
        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet("color:#6b7280; font-size:12px; background:transparent; border:none;")
            lay.addWidget(sub_lbl)
    
    def set_value(self, v: str):
        self._val.setText(v)


class _WeekDayIcon(QWidget):
    def __init__(self, day: str, active: bool, parent=None):
        super().__init__(parent)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignCenter)
        
        icon = QLabel()
        icon.setFixedSize(48, 48)
        icon.setAlignment(Qt.AlignCenter)
        
        if active:
            icon.setPixmap(qta.icon("fa5s.bolt", color="#000").pixmap(24, 24))
            icon.setStyleSheet(f"background:{C_GREEN}; border-radius:24px;")
        else:
            icon.setText("—")
            icon.setStyleSheet("background:#1a1a1a; color:#3a3a3a; border:1px solid #2a2a2a; border-radius:24px; font-size:20px;")
        
        lay.addWidget(icon)
        
        day_lbl = QLabel(day)
        day_lbl.setAlignment(Qt.AlignCenter)
        day_lbl.setStyleSheet("color:#6b7280; font-size:12px; background:transparent; border:none;")
        lay.addWidget(day_lbl)


class _WorkoutItem(QWidget):
    def __init__(self, name: str, subtitle: str, duration: str, parent=None):
        super().__init__(parent)
        
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 16, 0, 16)
        lay.setSpacing(16)
        
        info = QVBoxLayout()
        info.setSpacing(4)
        
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet("color:#fff; font-size:15px; font-weight:700; background:transparent; border:none;")
        info.addWidget(name_lbl)
        
        sub_lbl = QLabel(subtitle)
        sub_lbl.setStyleSheet("color:#6b7280; font-size:13px; background:transparent; border:none;")
        info.addWidget(sub_lbl)
        
        lay.addLayout(info)
        lay.addStretch()
        
        dur_lbl = QLabel(duration)
        dur_lbl.setStyleSheet("color:#6b7280; font-size:13px; background:transparent; border:none;")
        lay.addWidget(dur_lbl)


class DashboardTab(QWidget):
    def __init__(self, db: DatabaseConnection, parent=None):
        super().__init__(parent)
        self._db = db
        self._build()

    def update_user(self, data: dict):
        name = data.get("name", "").upper()
        self.banner_label.setText(f"BOM TREINO, <span style='color:{C_GREEN}'>{name}</span>")
        weight = data.get("weight", "")
        height = data.get("height", "")
        goal   = data.get("goal", "")
        self._sub_label.setText(f"{int(weight)}kg · {height}cm · Meta: {goal}")

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background:transparent; border:none; }")
        
        content = QWidget()
        content.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(32, 32, 32, 32)
        lay.setSpacing(24)

        hero = _HeroBanner()
        hero.setFixedHeight(200)
        hero_lay = QVBoxLayout(hero)
        hero_lay.setContentsMargins(32, 28, 32, 28)
        hero_lay.setSpacing(6)
        
        self.banner_label = QLabel("BOM TREINO, <span style='color:#a3e635'>...</span>")
        self.banner_label.setTextFormat(Qt.RichText)
        self.banner_label.setStyleSheet("font-size:40px; font-weight:800; color:#fff; background:transparent; border:none;")
        hero_lay.addWidget(self.banner_label)
        
        self._sub_label = QLabel("")
        self._sub_label.setStyleSheet("font-size:13px; color:#9ca3af; background:transparent; border:none;")
        hero_lay.addWidget(self._sub_label)
        hero_lay.addStretch()
        
        lay.addWidget(hero)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(16)
        
        self._stat_treinos   = _StatCard("fa5s.dumbbell", "Treinos esta semana", "0", "Meta: 5")
        self._stat_calorias  = _StatCard("fa5s.fire", "Calorias queimadas", "0", "kcal")
        self._stat_volume    = _StatCard("fa5s.weight", "Volume total", "0k", "kg levantados")
        self._stat_sequencia = _StatCard("fa5s.chart-line", "Sequência", "0", "dias seguidos")
        
        for s in [self._stat_treinos, self._stat_calorias, self._stat_volume, self._stat_sequencia]:
            stats_row.addWidget(s)
        
        lay.addLayout(stats_row)

        act_card = QFrame()
        act_card.setStyleSheet(f"QFrame {{ background:#1a1a1a; border:1px solid #2a2a2a; border-radius:{RADIUS_LG}px; }}")
        act_lay = QVBoxLayout(act_card)
        act_lay.setContentsMargins(24, 24, 24, 24)
        act_lay.setSpacing(20)
        
        act_title = QLabel("ATIVIDADE SEMANAL")
        act_title.setStyleSheet("color:#fff; font-size:15px; font-weight:700; background:transparent; border:none;")
        act_lay.addWidget(act_title)
        
        days_row = QHBoxLayout()
        days_row.setSpacing(12)
        
        active_rows = self._db.fetchall(
            "SELECT CAST(strftime('%w', datetime(started_at, 'unixepoch')) AS INTEGER) AS dow "
            "FROM workout_sessions "
            "WHERE started_at >= strftime('%s', 'now', 'weekday 0', '-7 days')"
        )
        active_dow = {r["dow"] for r in active_rows} if active_rows else set()
        loop_to_dow = [1, 2, 3, 4, 5, 6, 0]
        
        for i, d in enumerate(["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]):
            days_row.addWidget(_WeekDayIcon(d, loop_to_dow[i] in active_dow))
        
        act_lay.addLayout(days_row)
        lay.addWidget(act_card)

        rec_card = QFrame()
        rec_card.setStyleSheet(f"QFrame {{ background:#1a1a1a; border:1px solid #2a2a2a; border-radius:{RADIUS_LG}px; }}")
        self._rec_lay = QVBoxLayout(rec_card)
        self._rec_lay.setContentsMargins(24, 24, 24, 24)
        self._rec_lay.setSpacing(0)
        
        rec_title = QLabel("TREINOS RECENTES")
        rec_title.setStyleSheet("color:#fff; font-size:15px; font-weight:700; background:transparent; border:none;")
        self._rec_lay.addWidget(rec_title)
        
        lay.addWidget(rec_card)
        lay.addStretch()

        scroll.setWidget(content)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    def refresh(self):
        self._refresh_stats()
        self._refresh_recent()

    def on_workout_finished(self, payload: dict):
        if not payload:
            return
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

        calorias = int(vol * 5)
        self._stat_calorias.set_value(f"{calorias:,}".replace(",", "."))

        self._stat_sequencia.set_value("0")

    def _refresh_recent(self):
        while self._rec_lay.count() > 1:
            item = self._rec_lay.takeAt(1)
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
                dt   = datetime.datetime.fromtimestamp(row["started_at"])
                diff = (datetime.datetime.now() - dt).days
                when = "Hoje" if diff == 0 else "Ontem" if diff == 1 else f"{diff} dias atrás"
                
                cardio_row = self._db.fetchone(
                    "SELECT COALESCE(SUM(duration_min),0) AS total FROM cardio_logs WHERE session_id=?",
                    (row["id"],),
                )
                cardio_min = int(cardio_row["total"]) if cardio_row else 0
                
                vol_row = self._db.fetchone(
                    "SELECT COALESCE(SUM(weight_kg*reps),0) AS v FROM workout_logs WHERE session_id=?",
                    (row["id"],),
                )
                volume = float(vol_row["v"]) if vol_row else 0.0
                
                subtitle = when
                if cardio_min > 0:
                    subtitle += f" · {cardio_min} min cardio"
                
                dur = row["duration_seconds"] or 0
                duration = f"{dur//60} min"
                if volume > 0:
                    duration = f"{int(volume)} kg"
                
                item = _WorkoutItem(row["rname"] or "Treino livre", subtitle, duration)
                self._rec_lay.addWidget(item)
                
                sep = QFrame()
                sep.setFrameShape(QFrame.HLine)
                sep.setStyleSheet("background:#2a2a2a; max-height:1px; border:none;")
                self._rec_lay.addWidget(sep)
        else:
            empty = QLabel("Nenhum treino registrado ainda.")
            empty.setStyleSheet("color:#6b7280; font-size:13px; padding:20px 0; background:transparent; border:none;")
            empty.setAlignment(Qt.AlignCenter)
            self._rec_lay.addWidget(empty)
