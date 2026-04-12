"""
ui/screens/results.py
Tela de Resultados: gráficos de volume levantado, tempo de treino e km percorridos.
"""
from __future__ import annotations
import datetime

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel,
    QScrollArea, QVBoxLayout, QWidget,
)

from database import DatabaseConnection
from ui.theme import C_BORDER, C_CARD, C_GREEN, C_TEXT, C_TEXT2, C_TEXT3, label, RADIUS_MD, RADIUS_SM


# Paleta de cores alinhada ao tema escuro
_BG      = "#1a1a1a"
_CARD_BG = "#1e1e1e"
_GREEN   = "#a3e635"
_BLUE    = "#38bdf8"
_ORANGE  = "#fb923c"
_GRID    = "#2a2a2a"
_AXIS    = "#555555"


def _apply_dark_style(ax: plt.Axes, fig: Figure):
    """Aplica estilo escuro consistente a um eixo matplotlib."""
    fig.patch.set_facecolor(_BG)
    ax.set_facecolor(_BG)
    ax.tick_params(colors="#9ca3af", labelsize=9)
    ax.xaxis.label.set_color("#9ca3af")
    ax.yaxis.label.set_color("#9ca3af")
    ax.title.set_color("#ffffff")
    for spine in ax.spines.values():
        spine.set_edgecolor(_GRID)
    ax.grid(True, color=_GRID, linewidth=0.8, linestyle="--", alpha=0.7)
    ax.set_axisbelow(True)


class _ChartCard(QWidget):
    """Card com título e canvas matplotlib embutido."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"QWidget {{ background:{_CARD_BG}; border:1px solid {C_BORDER};"
            f"border-radius:{RADIUS_MD}px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color:#ffffff; font-size:13px; font-weight:700;"
            "background:transparent; border:none; border-radius:0;"
        )
        lay.addWidget(lbl)

        self.fig = Figure(figsize=(5, 2.4), dpi=96)
        self.fig.subplots_adjust(left=0.10, right=0.97, top=0.92, bottom=0.25)
        self.ax  = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setStyleSheet(
            "background:transparent; border:none; border-radius:0;"
        )
        lay.addWidget(self.canvas)

    def redraw(self):
        self.canvas.draw()


class ResultsTab(QWidget):
    """Tela de Resultados com três gráficos de evolução."""

    _PERIODS = {
        "7 dias":  7,
        "30 dias": 30,
        "90 dias": 90,
        "1 ano":   365,
    }

    def __init__(self, db: DatabaseConnection, parent=None):
        super().__init__(parent)
        self._db = db
        self._build()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:transparent; border:none;")

        content = QWidget()
        content.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(20)

        # Cabeçalho + filtro de período
        header = QHBoxLayout()
        title_lbl = QLabel("Resultados")
        title_lbl.setStyleSheet(
            "color:#ffffff; font-size:22px; font-weight:800;"
            "background:transparent; border:none;"
        )
        header.addWidget(title_lbl)
        header.addStretch()

        self._period_combo = QComboBox()
        self._period_combo.addItems(list(self._PERIODS.keys()))
        self._period_combo.setCurrentIndex(1)  # 30 dias padrão
        self._period_combo.setFixedWidth(110)
        self._period_combo.setStyleSheet(
            f"background:{_CARD_BG}; color:#ffffff; border:1px solid {C_BORDER};"
            f"border-radius:{RADIUS_MD}px; padding:4px 10px; font-size:12px;"
        )
        self._period_combo.currentIndexChanged.connect(self.refresh)
        header.addWidget(self._period_combo)
        lay.addLayout(header)

        # Três cards de gráfico
        self._card_volume  = _ChartCard("Volume Levantado (kg)")
        self._card_tempo   = _ChartCard("Tempo de Treino (min)")
        self._card_km      = _ChartCard("Distância Percorrida (km)")

        for c in (self._card_volume, self._card_tempo, self._card_km):
            c.setFixedHeight(280)
            lay.addWidget(c)

        lay.addStretch()
        scroll.setWidget(content)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def _days(self) -> int:
        return self._PERIODS[self._period_combo.currentText()]

    def _fetch_volume(self, days: int):
        """Retorna lista de (date, volume_kg) agrupado por dia, apenas dias com volume > 0."""
        rows = self._db.fetchall(
            """
            SELECT date(ws.started_at, 'unixepoch') AS day,
                   COALESCE(SUM(wl.weight_kg * wl.reps), 0) AS vol
            FROM workout_sessions ws
            LEFT JOIN workout_logs wl ON wl.session_id = ws.id AND wl.set_type != 'W'
            WHERE ws.started_at >= strftime('%s','now',?)
            GROUP BY day
            HAVING vol > 0
            ORDER BY day
            """,
            (f"-{days} days",),
        )
        dates = [datetime.date.fromisoformat(r["day"]) for r in rows]
        vals  = [float(r["vol"]) for r in rows]
        return dates, vals

    def _fetch_tempo(self, days: int):
        """Retorna lista de (date, duration_min) por dia, apenas dias com tempo > 0."""
        rows = self._db.fetchall(
            """
            SELECT date(ws.started_at, 'unixepoch') AS day,
                   SUM(
                       COALESCE(
                           ws.duration_seconds,
                           (SELECT MAX(wl.timestamp) - MIN(wl.timestamp)
                            FROM workout_logs wl WHERE wl.session_id = ws.id)
                       )
                   ) / 60.0 AS mins
            FROM workout_sessions ws
            WHERE ws.started_at >= strftime('%s','now',?)
            GROUP BY day
            HAVING mins > 0
            ORDER BY day
            """,
            (f"-{days} days",),
        )
        dates = [datetime.date.fromisoformat(r["day"]) for r in rows]
        vals  = [max(0.0, float(r["mins"] or 0)) for r in rows]
        return dates, vals

    def _fetch_km(self, days: int):
        """Retorna lista de (date, km) de cardio por dia."""
        rows = self._db.fetchall(
            """
            SELECT date(ws.started_at, 'unixepoch') AS day,
                   COALESCE(SUM(cl.distance_km), 0) AS km
            FROM cardio_logs cl
            JOIN workout_sessions ws ON cl.session_id = ws.id
            WHERE ws.started_at >= strftime('%s','now',?)
              AND cl.distance_km IS NOT NULL
            GROUP BY day
            ORDER BY day
            """,
            (f"-{days} days",),
        )
        dates = [datetime.date.fromisoformat(r["day"]) for r in rows]
        vals  = [float(r["km"]) for r in rows]
        return dates, vals

    # ------------------------------------------------------------------
    # Renderização
    # ------------------------------------------------------------------

    def _plot_bar(self, card: _ChartCard, dates, vals, color: str, ylabel: str):
        ax = card.ax
        ax.clear()
        _apply_dark_style(ax, card.fig)

        # Filtra apenas dias com valor > 0
        pairs = [(d, v) for d, v in zip(dates, vals) if v > 0]

        if pairs:
            import numpy as np
            fdates, fvals = zip(*pairs)
            x = np.arange(len(fdates))

            # Largura proporcional: mais pontos = barras mais finas
            bar_w = min(0.55, max(0.15, 0.55 - len(fdates) * 0.01))
            ax.bar(x, fvals, width=bar_w, color=color, alpha=0.88, zorder=3)

            # Linha de tendência só com 2+ pontos
            if len(fdates) > 1:
                z = np.polyfit(x, fvals, 1)
                ax.plot(x, np.poly1d(z)(x), color=color,
                        linewidth=1.5, linestyle="--", alpha=0.5, zorder=4)

            # Ticks: máximo 8 labels
            step = max(1, len(fdates) // 8)
            ax.set_xticks(x[::step])
            ax.set_xticklabels(
                [fdates[i].strftime("%d/%m") for i in range(0, len(fdates), step)],
                rotation=30, ha="right", fontsize=8,
            )
            ax.set_xlim(-0.6, len(fdates) - 0.4)
        else:
            ax.text(0.5, 0.5, "Sem dados no período",
                    transform=ax.transAxes, ha="center", va="center",
                    color="#6b7280", fontsize=11)
            ax.set_xticks([])
            ax.set_yticks([])

        ax.set_ylabel(ylabel, fontsize=9)
        card.redraw()

    def refresh(self):
        days = self._days()

        dates_v, vals_v = self._fetch_volume(days)
        self._plot_bar(self._card_volume, dates_v, vals_v, _GREEN, "kg")

        dates_t, vals_t = self._fetch_tempo(days)
        self._plot_bar(self._card_tempo, dates_t, vals_t, _BLUE, "min")

        dates_k, vals_k = self._fetch_km(days)
        self._plot_bar(self._card_km, dates_k, vals_k, _ORANGE, "km")
