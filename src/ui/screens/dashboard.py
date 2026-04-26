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
from src.ui.theme import C_GREEN, RADIUS_LG
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
        
        from src.ui.theme import neon_glow
        neon_glow(self, "#a2ff00", blur=20, opacity=60)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(8)
        
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        
        icon_container = QLabel()
        icon_container.setFixedSize(18, 18)
        icon_container.setAlignment(Qt.AlignCenter)
        icon_container.setPixmap(qta.icon(icon_name, color=C_GREEN).pixmap(16, 16))
        hdr.addWidget(icon_container)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color:#6b7280; font-size:12px; font-weight:500; background:transparent; border:none;")
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        
        lay.addLayout(hdr)
        
        self._val = QLabel(value)
        self._val.setStyleSheet("color:#fff; font-size:32px; font-weight:800; background:transparent; border:none;")
        lay.addWidget(self._val)
        
        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet("color:#6b7280; font-size:11px; background:transparent; border:none;")
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
            from src.ui.theme import neon_glow
            icon.setPixmap(qta.icon("fa5s.bolt", color="#1a1a1a").pixmap(24, 24))
            icon.setStyleSheet(f"background:{C_GREEN}; border-radius:12px;")
            # Efeito neon mais forte para o ícone ativo
            neon_glow(icon, C_GREEN, blur=60, opacity=400)
        else:
            icon.setText("—")
            icon.setStyleSheet("background:#1a1a1a; color:#3a3a3a; border:1px solid #2a2a2a; border-radius:12px; font-size:20px;")
        
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
        self._stat_sequencia = _StatCard("fa5s.chart-line", "Streak", "0", "dias seguidos")
        
        for s in [self._stat_treinos, self._stat_calorias, self._stat_volume, self._stat_sequencia]:
            stats_row.addWidget(s)
        
        lay.addLayout(stats_row)

        act_card = QFrame()
        act_card.setStyleSheet(f"QFrame {{ background:#1a1a1a; border:1px solid #2a2a2a; border-radius:{RADIUS_LG}px; }}")
        from src.ui.theme import neon_glow
        neon_glow(act_card, "#a2ff00", blur=20, opacity=60)
        
        self._act_lay = QVBoxLayout(act_card)
        self._act_lay.setContentsMargins(24, 24, 24, 24)
        self._act_lay.setSpacing(20)
        
        act_title = QLabel("ATIVIDADE SEMANAL")
        act_title.setStyleSheet("color:#fff; font-size:15px; font-weight:700; background:transparent; border:none;")
        self._act_lay.addWidget(act_title)
        
        # Container para os dias da semana (será recriado no refresh)
        self._days_container = QWidget()
        self._days_layout = QHBoxLayout(self._days_container)
        self._days_layout.setSpacing(12)
        self._days_layout.setContentsMargins(0, 0, 0, 0)
        self._act_lay.addWidget(self._days_container)
        
        lay.addWidget(act_card)

        rec_card = QFrame()
        rec_card.setStyleSheet(f"QFrame {{ background:#1a1a1a; border:1px solid #2a2a2a; border-radius:{RADIUS_LG}px; }}")
        from src.ui.theme import neon_glow
        neon_glow(rec_card, "#a2ff00", blur=20, opacity=60)
        
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
        self._refresh_weekly_activity()
        self._refresh_recent()
    
    def _refresh_weekly_activity(self):
        """Atualiza os ícones da atividade semanal."""
        # Remove todos os widgets do container
        while self._days_layout.count():
            item = self._days_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Busca os dias com treinos na semana atual
        active_rows = self._db.fetchall(
            "SELECT CAST(strftime('%w', datetime(started_at, 'unixepoch')) AS INTEGER) AS dow "
            "FROM workout_sessions "
            "WHERE started_at >= strftime('%s', 'now', 'weekday 0', '-7 days')"
        )
        active_dow = {r["dow"] for r in active_rows} if active_rows else set()
        loop_to_dow = [1, 2, 3, 4, 5, 6, 0]
        
        # Recria os ícones
        for i, d in enumerate(["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]):
            self._days_layout.addWidget(_WeekDayIcon(d, loop_to_dow[i] in active_dow))

    def on_workout_finished(self, payload: dict):
        if not payload:
            return
        self._refresh_stats()
        self._refresh_weekly_activity()
        self._refresh_recent()

    def _refresh_stats(self):
        row = self._db.fetchone(
            "SELECT COUNT(*) AS c FROM workout_sessions WHERE started_at >= strftime('%s','now','-7 days')"
        )
        self._stat_treinos.set_value(str(row["c"] if row else 0))

        row2 = self._db.fetchone("SELECT COALESCE(SUM(weight_kg*reps),0) AS v FROM workout_logs")
        vol = float(row2["v"]) if row2 else 0.0
        self._stat_volume.set_value(f"{vol/1000:.1f}k" if vol >= 1000 else f"{vol:.0f}")

        # Calcula calorias usando a fórmula MET correta
        # Busca todas as sessões da semana e soma as calorias
        session_rows = self._db.fetchall(
            "SELECT id FROM workout_sessions WHERE started_at >= strftime('%s','now','-7 days')"
        )
        
        total_calories = 0.0
        for session_row in session_rows:
            session_id = session_row["id"]
            
            # Busca peso do usuário (se disponível no user_data.json)
            user_weight = 70.0  # padrão
            try:
                import json
                from pathlib import Path
                user_data_path = Path("user_data.json")
                if user_data_path.exists():
                    with open(user_data_path, "r", encoding="utf-8") as f:
                        user_data = json.load(f)
                        user_weight = float(user_data.get("weight", 70.0))
            except:
                pass
            
            # Calcula calorias da sessão usando fórmula MET
            log_rows = self._db.fetchall(
                """
                SELECT wl.reps, emv.met_value
                FROM workout_logs wl
                LEFT JOIN exercise_met_values emv ON wl.exercise_id = emv.exercise_id
                WHERE wl.session_id = ? AND wl.set_type != 'W'
                """,
                (session_id,),
            )
            
            for log_row in log_rows:
                reps = log_row["reps"]
                met_value = log_row["met_value"] if log_row["met_value"] else 5.0
                
                # Fórmula MET: (MET × Peso_kg × Tempo_min) / 60
                # Tempo: 4 segundos por rep = 0.0667 min/rep
                time_min = reps * 4.0 / 60.0
                calories = (met_value * user_weight * time_min) / 60.0
                total_calories += calories
        
        self._stat_calorias.set_value(f"{int(total_calories):,}".replace(",", "."))

        # Calcula a streak (sequência de dias seguidos)
        streak = self._calculate_streak()
        self._stat_sequencia.set_value(str(streak))
    
    def _calculate_streak(self) -> int:
        """Calcula quantos dias seguidos o usuário treinou."""
        # Busca todas as datas únicas de treinos, ordenadas da mais recente para a mais antiga
        rows = self._db.fetchall(
            """SELECT DISTINCT date(started_at, 'unixepoch') AS workout_date
               FROM workout_sessions
               ORDER BY workout_date DESC"""
        )
        
        if not rows:
            return 0
        
        # Converte para lista de datas
        workout_dates = [datetime.datetime.strptime(r["workout_date"], "%Y-%m-%d").date() for r in rows]
        today = datetime.datetime.now().date()
        
        # Se não treinou hoje nem ontem, streak é 0
        if workout_dates[0] < today - datetime.timedelta(days=1):
            return 0
        
        # Conta dias consecutivos
        streak = 0
        expected_date = today if workout_dates[0] == today else today - datetime.timedelta(days=1)
        
        for workout_date in workout_dates:
            if workout_date == expected_date:
                streak += 1
                expected_date -= datetime.timedelta(days=1)
            elif workout_date < expected_date:
                # Quebrou a sequência
                break
        
        return streak

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
