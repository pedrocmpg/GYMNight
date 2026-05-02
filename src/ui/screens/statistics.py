"""
ui/screens/statistics.py
Tela de Estatísticas: Dashboard Moderno com Radar Chart e Grid de Métricas
"""
from __future__ import annotations
import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea,
    QVBoxLayout, QWidget, QComboBox, QGridLayout,
)
from PySide6.QtGui import QPixmap
import qtawesome as qta

from database import DatabaseConnection
from src.ui.theme import C_GREEN, C_BG, RADIUS_LG, neon_glow
from loguru import logger

# Matplotlib imports para o gráfico
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import numpy as np


class _MetricCard(QFrame):
    """Card de métrica individual para o grid 2x2 - Design Moderno."""
    
    def __init__(self, title: str, value: str, growth: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background:#151515; border:none; border-radius:12px; }"
        )
        self.setMinimumHeight(120)
        self.setMinimumWidth(200)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(8)
        
        # Título pequeno no topo
        title_label = QLabel(title.upper())
        title_label.setStyleSheet(
            "color:#6b7280; font-size:11px; font-weight:600; letter-spacing:1px; "
            "font-family:'Inter', 'Roboto', sans-serif; background:transparent; border:none;"
        )
        title_label.setAlignment(Qt.AlignLeft)
        lay.addWidget(title_label)
        
        # Valor grande
        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(
            "color:#FFFFFF; font-size:36px; font-weight:700; "
            "font-family:'Inter', 'Roboto', sans-serif; background:transparent; border:none;"
        )
        self._value_label.setAlignment(Qt.AlignLeft)
        lay.addWidget(self._value_label)
        
        # Indicador de crescimento (se fornecido)
        if growth:
            self._growth_label = QLabel(f"↑ {growth}")
            self._growth_label.setStyleSheet(
                f"color:{C_GREEN}; font-size:12px; font-weight:600; "
                "font-family:'Inter', 'Roboto', sans-serif; background:transparent; border:none;"
            )
            self._growth_label.setAlignment(Qt.AlignLeft)
            lay.addWidget(self._growth_label)
        else:
            self._growth_label = None
        
        lay.addStretch()
    
    def set_value(self, value: str):
        """Atualiza o valor exibido no card."""
        self._value_label.setText(value)
    
    def set_growth(self, growth: str):
        """Atualiza o indicador de crescimento."""
        if self._growth_label:
            self._growth_label.setText(f"↑ {growth}")


class _RadarChart(QWidget):
    """Widget com gráfico de radar (spider plot) para distribuição muscular - Design Neon."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuração do Matplotlib
        self.figure = Figure(figsize=(10, 10), facecolor='#0f0f0f')
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setStyleSheet("background:#0f0f0f; border:none;")
        
        # Size Policy: Expandir em ambas as direções
        from PySide6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Minimum Size: Garantir altura mínima
        self.setMinimumHeight(500)
        self.setMinimumWidth(500)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.canvas)
    
    def update_chart(self, muscle_data: dict[str, float]):
        """
        Atualiza o gráfico de radar com os dados de distribuição muscular.
        
        Args:
            muscle_data: Dicionário {nome_musculo: volume_total}
        """
        self.figure.clear()
        
        # Define os 6 grupos musculares principais
        categories = ['Costas', 'Peito', 'Core', 'Ombros', 'Braços', 'Pernas']
        
        # Mapeia os dados recebidos para as categorias
        values = []
        for cat in categories:
            # Busca o valor correspondente (case-insensitive)
            value = 0
            for key, val in muscle_data.items():
                if key.lower() == cat.lower():
                    value = val
                    break
            values.append(value)
        
        # Se não há dados, exibe mensagem
        if not any(values):
            ax = self.figure.add_subplot(111)
            ax.text(
                0.5, 0.5, 'Nenhum treino registrado ainda',
                ha='center', va='center',
                color='#6b7280', fontsize=16, fontweight='500',
                transform=ax.transAxes
            )
            ax.set_facecolor('#0f0f0f')
            ax.axis('off')
            self.canvas.draw()
            return
        
        # Normaliza os valores para porcentagem (0-100)
        max_value = max(values) if max(values) > 0 else 1
        normalized_values = [(v / max_value) * 100 for v in values]
        
        # Número de variáveis
        num_vars = len(categories)
        
        # Calcula os ângulos para cada eixo
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
        
        # Fecha o polígono
        normalized_values += normalized_values[:1]
        angles += angles[:1]
        
        # Cria o subplot polar (radar)
        ax = self.figure.add_subplot(111, projection='polar', facecolor='#0f0f0f')
        
        # Remove margens da figura e ativa tight layout
        self.figure.subplots_adjust(left=0, right=1, bottom=0, top=1)
        self.figure.set_tight_layout(True)
        
        # Posicionamento absoluto do eixo: 80% da área, 10% de margem em cada lado
        ax.set_position([0.1, 0.1, 0.8, 0.8])
        
        # Plota a área preenchida (Verde Neon com transparência)
        ax.plot(angles, normalized_values, 'o-', linewidth=2.5, color='#b5ff00', zorder=3)
        ax.fill(angles, normalized_values, alpha=0.3, color='#b5ff00', zorder=2)
        
        # Configura a escala fixa de 0 a 100
        ax.set_ylim(0, 100)
        
        # Configura as labels dos músculos com fonte menor e posiciona fora do eixo
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=9, color='#FFFFFF', weight='600')
        
        # Usa set_thetagrids para empurrar as labels para fora (frac > 1)
        ax.set_thetagrids(np.degrees(angles[:-1]), categories, frac=1.2, 
                          fontsize=9, color='#FFFFFF', weight='600')
        
        # Remove completamente os números de porcentagem do centro
        ax.set_yticklabels([])
        
        # Estiliza a grade (grid) - linhas da teia em cinza escuro
        ax.grid(True, color='#2a2a2a', linewidth=1, linestyle='-', zorder=1)
        
        # Remove o círculo externo (spine)
        ax.spines['polar'].set_visible(False)
        
        self.canvas.draw()


class _TrophyCard(QFrame):
    """Card de troféu para Streak ou Tempo Total - Design Profissional."""
    
    def __init__(self, icon_name: str, title: str, value: str, unit: str = "", parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background:#1a1a1a; border:1px solid #222222; border-radius:12px; }"
        )
        self.setMinimumHeight(140)
        
        # Efeito neon
        neon_glow(self, C_GREEN, blur=25, opacity=70)
        
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(12)
        
        # Container horizontal: ícone + valor + unidade (alinhados à esquerda)
        top_row = QHBoxLayout()
        top_row.setSpacing(16)
        top_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # Ícone à esquerda
        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setPixmap(qta.icon(icon_name, color=C_GREEN).pixmap(36, 36))
        top_row.addWidget(icon_label)
        
        # Container para valor + unidade
        value_container = QHBoxLayout()
        value_container.setSpacing(6)
        value_container.setAlignment(Qt.AlignLeft | Qt.AlignBaseline)
        
        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(
            f"color:{C_GREEN}; font-size:48px; font-weight:500; "
            "font-family:'Inter', 'Roboto', sans-serif; background:transparent; border:none;"
        )
        value_container.addWidget(self._value_label)
        
        if unit:
            self._unit_label = QLabel(unit)
            self._unit_label.setStyleSheet(
                "color:#6b7280; font-size:24px; font-weight:500; "
                "font-family:'Inter', 'Roboto', sans-serif; background:transparent; border:none;"
            )
            value_container.addWidget(self._unit_label)
        else:
            self._unit_label = None
        
        top_row.addLayout(value_container)
        top_row.addStretch()
        
        lay.addLayout(top_row)
        
        # Título abaixo (alinhado à esquerda)
        title_label = QLabel(title.upper())
        title_label.setStyleSheet(
            "color:#aaaaaa; font-size:12px; font-weight:600; letter-spacing:1.2px; "
            "font-family:'Inter', 'Roboto', sans-serif; background:transparent; border:none;"
        )
        title_label.setAlignment(Qt.AlignLeft)
        lay.addWidget(title_label)
        
        lay.addStretch()
    
    def set_value(self, value: str):
        """Atualiza o valor exibido no card."""
        self._value_label.setText(value)


class _MuscleDistributionChart(QWidget):
    """Widget com gráfico de teia (radar chart) para distribuição muscular - DEPRECATED."""
    pass


class StatisticsTab(QWidget):
    """Tela principal de Estatísticas."""
    
    def __init__(self, db: DatabaseConnection, parent=None):
        super().__init__(parent)
        logger.info("Inicializando StatisticsTab")
        self._db = db
        try:
            self._build()
            logger.info("StatisticsTab construída com sucesso")
        except Exception as e:
            logger.error(f"Erro ao construir StatisticsTab: {e}")
            raise
    
    def _build(self):
        """Constrói a interface da tela."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background:transparent; border:none; }")
        
        content = QWidget()
        content.setStyleSheet(f"background:{C_BG};")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(40, 40, 40, 40)
        lay.setSpacing(32)
        
        # Título da página
        title = QLabel("ESTATÍSTICAS")
        title.setStyleSheet(
            f"color:{C_GREEN}; font-size:42px; font-weight:900; "
            "font-family:'Inter', 'Roboto', sans-serif; background:transparent; border:none;"
        )
        lay.addWidget(title)
        
        # Seletor de período (QComboBox estilizado)
        self._period_selector = QComboBox()
        self._period_selector.addItems([
            "Últimos 7 dias",
            "Últimos 30 dias",
            "Últimos 90 dias",
            "Último ano",
            "Todo o período"
        ])
        self._period_selector.setCurrentIndex(1)  # "Últimos 30 dias" por padrão
        self._period_selector.setStyleSheet(
            f"""
            QComboBox {{
                background:#0f0f0f;
                color:#FFFFFF;
                border:1px solid #2a2a2a;
                border-radius:8px;
                padding:10px 16px;
                font-size:13px;
                font-weight:600;
                font-family:'Inter', 'Roboto', sans-serif;
                min-width:180px;
            }}
            QComboBox:hover {{
                border:1px solid {C_GREEN};
            }}
            QComboBox::drop-down {{
                border:none;
                width:30px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left:5px solid transparent;
                border-right:5px solid transparent;
                border-top:5px solid #FFFFFF;
                margin-right:8px;
            }}
            QComboBox QAbstractItemView {{
                background:#0f0f0f;
                color:#FFFFFF;
                border:1px solid #2a2a2a;
                selection-background-color:{C_GREEN};
                selection-color:#0f0f0f;
                padding:4px;
            }}
            """
        )
        self._period_selector.currentIndexChanged.connect(self.refresh)
        lay.addWidget(self._period_selector, alignment=Qt.AlignLeft)
        
        lay.addSpacing(16)
        
        # Gráfico de Radar (Distribuição Muscular)
        chart_card = QFrame()
        chart_card.setStyleSheet(
            "QFrame { background:#0f0f0f; border:1px solid #2a2a2a; border-radius:12px; }"
        )
        
        # Size Policy para o card expandir
        from PySide6.QtWidgets import QSizePolicy
        chart_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        chart_card.setMinimumHeight(600)
        
        chart_lay = QVBoxLayout(chart_card)
        chart_lay.setContentsMargins(32, 32, 32, 32)
        chart_lay.setSpacing(0)
        
        self._radar_chart = _RadarChart()
        chart_lay.addWidget(self._radar_chart, stretch=1)
        
        lay.addWidget(chart_card, stretch=0)
        
        # Grid de Métricas (2x2)
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(20)
        metrics_grid.setContentsMargins(0, 0, 0, 0)
        
        # Card 1: Treinamentos
        self._workouts_card = _MetricCard("Treinamentos", "0", "0")
        metrics_grid.addWidget(self._workouts_card, 0, 0)
        
        # Card 2: Duração
        self._duration_card = _MetricCard("Duração", "0h 0min", "0min")
        metrics_grid.addWidget(self._duration_card, 0, 1)
        
        # Card 3: Volume
        self._volume_card = _MetricCard("Volume", "0 kg", "0 kg")
        metrics_grid.addWidget(self._volume_card, 1, 0)
        
        # Card 4: Séries
        self._sets_card = _MetricCard("Séries", "0", "0")
        metrics_grid.addWidget(self._sets_card, 1, 1)
        
        lay.addLayout(metrics_grid)
        lay.addStretch()
        
        scroll.setWidget(content)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)
    
    def refresh(self):
        """Atualiza todos os dados da tela."""
        logger.info("StatisticsTab.refresh() chamado")
        try:
            period_days = self._get_period_days()
            logger.info(f"Período selecionado: {period_days} dias")
            self._refresh_workouts(period_days)
            self._refresh_duration(period_days)
            self._refresh_volume(period_days)
            self._refresh_sets(period_days)
            self._refresh_muscle_distribution(period_days)
            logger.info("StatisticsTab.refresh() concluído com sucesso")
        except Exception as e:
            logger.error(f"Erro ao atualizar estatísticas: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _get_period_days(self) -> int | None:
        """Retorna o número de dias do período selecionado, ou None para todo o período."""
        period_map = {
            "Últimos 7 dias": 7,
            "Últimos 30 dias": 30,
            "Últimos 90 dias": 90,
            "Último ano": 365,
            "Todo o período": None
        }
        return period_map.get(self._period_selector.currentText(), 30)
    
    def _get_date_filter(self, days: int | None) -> str:
        """Retorna a cláusula SQL para filtrar por período."""
        if days is None:
            return ""
        return f"AND date(started_at, 'unixepoch') >= date('now', '-{days} days')"
    
    def _refresh_workouts(self, period_days: int | None):
        """Atualiza o card de Treinamentos."""
        date_filter = self._get_date_filter(period_days)
        
        # Total de treinos no período
        row = self._db.fetchone(
            f"""SELECT COUNT(*) AS total FROM workout_sessions 
                WHERE 1=1 {date_filter}"""
        )
        total = int(row["total"]) if row else 0
        
        # Crescimento (comparado com período anterior)
        if period_days:
            prev_row = self._db.fetchone(
                f"""SELECT COUNT(*) AS total FROM workout_sessions 
                    WHERE date(started_at, 'unixepoch') >= date('now', '-{period_days * 2} days')
                    AND date(started_at, 'unixepoch') < date('now', '-{period_days} days')"""
            )
            prev_total = int(prev_row["total"]) if prev_row else 0
            growth = total - prev_total
        else:
            growth = 0
        
        self._workouts_card.set_value(str(total))
        if growth > 0:
            self._workouts_card.set_growth(str(growth))
    
    def _refresh_duration(self, period_days: int | None):
        """Atualiza o card de Duração."""
        date_filter = self._get_date_filter(period_days)
        
        # Duração total no período
        row = self._db.fetchone(
            f"""SELECT COALESCE(SUM(duration_seconds), 0) AS total FROM workout_sessions 
                WHERE 1=1 {date_filter}"""
        )
        total_seconds = int(row["total"]) if row else 0
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        # Crescimento (comparado com período anterior)
        if period_days:
            prev_row = self._db.fetchone(
                f"""SELECT COALESCE(SUM(duration_seconds), 0) AS total FROM workout_sessions 
                    WHERE date(started_at, 'unixepoch') >= date('now', '-{period_days * 2} days')
                    AND date(started_at, 'unixepoch') < date('now', '-{period_days} days')"""
            )
            prev_seconds = int(prev_row["total"]) if prev_row else 0
            growth_seconds = total_seconds - prev_seconds
            growth_minutes = growth_seconds // 60
        else:
            growth_minutes = 0
        
        self._duration_card.set_value(f"{hours}h {minutes}min")
        if growth_minutes > 0:
            self._duration_card.set_growth(f"{growth_minutes}min")
    
    def _refresh_volume(self, period_days: int | None):
        """Atualiza o card de Volume."""
        date_filter = self._get_date_filter(period_days)
        
        # Volume total no período
        row = self._db.fetchone(
            f"""SELECT COALESCE(SUM(weight_kg * reps), 0) AS total 
                FROM workout_logs wl
                JOIN workout_sessions wss ON wl.session_id = wss.id
                WHERE wl.set_type != 'W' {date_filter}"""
        )
        total_kg = int(row["total"]) if row else 0
        
        # Crescimento (comparado com período anterior)
        if period_days:
            prev_row = self._db.fetchone(
                f"""SELECT COALESCE(SUM(weight_kg * reps), 0) AS total 
                    FROM workout_logs wl
                    JOIN workout_sessions wss ON wl.session_id = wss.id
                    WHERE wl.set_type != 'W'
                    AND date(wss.started_at, 'unixepoch') >= date('now', '-{period_days * 2} days')
                    AND date(wss.started_at, 'unixepoch') < date('now', '-{period_days} days')"""
            )
            prev_kg = int(prev_row["total"]) if prev_row else 0
            growth_kg = total_kg - prev_kg
        else:
            growth_kg = 0
        
        self._volume_card.set_value(f"{total_kg:,} kg".replace(',', '.'))
        if growth_kg > 0:
            self._volume_card.set_growth(f"{growth_kg:,} kg".replace(',', '.'))
    
    def _refresh_sets(self, period_days: int | None):
        """Atualiza o card de Séries."""
        date_filter = self._get_date_filter(period_days)
        
        # Total de séries no período (excluindo aquecimento)
        row = self._db.fetchone(
            f"""SELECT COUNT(*) AS total 
                FROM workout_logs wl
                JOIN workout_sessions wss ON wl.session_id = wss.id
                WHERE wl.set_type != 'W' {date_filter}"""
        )
        total = int(row["total"]) if row else 0
        
        # Crescimento (comparado com período anterior)
        if period_days:
            prev_row = self._db.fetchone(
                f"""SELECT COUNT(*) AS total 
                    FROM workout_logs wl
                    JOIN workout_sessions wss ON wl.session_id = wss.id
                    WHERE wl.set_type != 'W'
                    AND date(wss.started_at, 'unixepoch') >= date('now', '-{period_days * 2} days')
                    AND date(wss.started_at, 'unixepoch') < date('now', '-{period_days} days')"""
            )
            prev_total = int(prev_row["total"]) if prev_row else 0
            growth = total - prev_total
        else:
            growth = 0
        
        self._sets_card.set_value(str(total))
        if growth > 0:
            self._sets_card.set_growth(str(growth))
    
    def _refresh_muscle_distribution(self, period_days: int | None):
        """Atualiza o gráfico de distribuição muscular."""
        muscle_data = self._calculate_muscle_distribution(period_days)
        self._radar_chart.update_chart(muscle_data)
    
    def _calculate_muscle_distribution(self, period_days: int | None) -> dict[str, float]:
        """
        Calcula a distribuição de volume por grupo muscular.
        
        Args:
            period_days: Número de dias do período, ou None para todo o período
        
        Returns:
            Dicionário {nome_musculo: volume_total}
        """
        try:
            date_filter = self._get_date_filter(period_days)
            
            # Busca o volume proporcional por músculo usando a view session_muscle_volume
            query = f"""
                SELECT mg.name, SUM(smv.muscle_volume) AS total_volume
                FROM session_muscle_volume smv
                JOIN muscle_groups mg ON smv.muscle_group_id = mg.id
                JOIN workout_sessions ws ON smv.session_id = ws.id
                WHERE 1=1 {date_filter}
                GROUP BY mg.name
                ORDER BY total_volume DESC
            """
            logger.debug(f"Query de distribuição muscular: {query}")
            
            rows = self._db.fetchall(query)
            logger.debug(f"Linhas retornadas: {len(rows) if rows else 0}")
            
            if not rows:
                logger.warning("Nenhum dado de distribuição muscular encontrado")
                return {}
            
            result = {row["name"]: float(row["total_volume"]) for row in rows}
            logger.debug(f"Distribuição muscular: {result}")
            return result
        except Exception as e:
            logger.error(f"Erro ao calcular distribuição muscular: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {}
    
    def _refresh_streak(self):
        """DEPRECATED - Método mantido para compatibilidade."""
        pass
    
    def _calculate_streak(self) -> int:
        """DEPRECATED - Método mantido para compatibilidade."""
        return 0
    
    def _refresh_total_time(self):
        """DEPRECATED - Método mantido para compatibilidade."""
        pass
    
    def on_workout_finished(self, payload: dict):
        """Callback quando um treino é finalizado."""
        if not payload:
            return
        self.refresh()

