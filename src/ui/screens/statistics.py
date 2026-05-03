"""
ui/screens/statistics.py
Tela de Estatísticas: Dashboard Moderno com Radar Chart e Grid de Métricas
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea,
    QVBoxLayout, QWidget, QGridLayout,
)

from database import DatabaseConnection
from src.ui.theme import C_GREEN, C_BG
from src.ui.smooth_scroll import apply_smooth_scroll
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
        self.figure = Figure(figsize=(10, 10), facecolor='#0a0a0a')
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setStyleSheet("background:#0a0a0a; border:none;")
        
        # Otimização de performance: evita redesenho desnecessário
        self.setAttribute(Qt.WA_OpaquePaintEvent)
        
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
        
        # Define os 6 grupos musculares principais para o gráfico
        # Agrupa Bíceps + Tríceps = Braços, e Abdômen = Core
        categories = ['Peito', 'Costas', 'Ombros', 'Braços', 'Pernas', 'Core']
        
        # Mapeia os dados recebidos para as categorias do gráfico
        values = []
        for cat in categories:
            value = 0
            if cat == 'Braços':
                # Soma Bíceps + Tríceps
                value = muscle_data.get('Bíceps', 0) + muscle_data.get('Tríceps', 0)
            elif cat == 'Core':
                # Abdômen vira Core
                value = muscle_data.get('Abdômen', 0)
            else:
                # Busca direto no dicionário
                value = muscle_data.get(cat, 0)
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
            ax.set_facecolor('#0a0a0a')
            ax.axis('off')
            self.canvas.draw_idle()
            return
        
        # Normaliza os valores para porcentagem (0-100)
        max_value = max(values) if max(values) > 0 else 1
        normalized_values = [(v / max_value) * 100 for v in values]
        
        # Número de variáveis
        num_vars = len(categories)
        
        # Calcula os ângulos para cada eixo
        angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)
        
        # Fecha o polígono: concatena o primeiro valor ao final
        normalized_values = np.concatenate((normalized_values, [normalized_values[0]]))
        angles = np.concatenate((angles, [angles[0]]))
        
        # Cria o subplot polar (radar) com fundo preto
        ax = self.figure.add_subplot(111, projection='polar', facecolor='#0a0a0a')
        self.figure.patch.set_facecolor('#0a0a0a')
        
        # Remove margens da figura
        self.figure.subplots_adjust(left=0.05, right=0.95, bottom=0.05, top=0.95)
        
        # Configura a escala fixa de 0 a 100
        ax.set_ylim(0, 100)
        
        # Configura as linhas de grade CIRCULARES (mais visíveis, em cinza claro)
        ax.set_yticks([25, 50, 75, 100])
        ax.set_yticklabels([])  # Remove os números, mantém apenas as linhas
        ax.yaxis.grid(True, color='#3a3a3a', linewidth=1.2, linestyle='-', alpha=0.8, zorder=1)
        
        # Configura as linhas RADIAIS (raios do centro para fora, em cinza claro)
        ax.xaxis.grid(True, color='#3a3a3a', linewidth=1.2, linestyle='-', alpha=0.8, zorder=1)
        
        # Plota a área preenchida (Verde Neon com preenchimento mais escuro)
        ax.plot(angles, normalized_values, 'o-', linewidth=3, color='#b5ff00', 
                markersize=8, markerfacecolor='#b5ff00', markeredgecolor='#b5ff00', zorder=3)
        ax.fill(angles, normalized_values, alpha=0.4, color='#6b8f00', zorder=2)
        
        # Posiciona os números de escala à direita (padrão do matplotlib)
        ax.set_rlabel_position(0)
        
        # Configura as labels dos músculos (BRANCO e FORA do gráfico)
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories, fontsize=13, color='#FFFFFF', weight='600')
        
        # Ajusta a posição das labels para FORA do gráfico
        ax.tick_params(axis='x', pad=20)  # Aumenta o espaçamento das labels
        
        # Remove o círculo externo (spine)
        ax.spines['polar'].set_visible(False)
        
        # Usa draw_idle() para melhor performance
        self.canvas.draw_idle()


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
        # Layout raiz sem margens
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background:transparent; border:none; }")
        
        # Aplica rolagem suave otimizada
        apply_smooth_scroll(scroll)
        
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
        
        lay.addSpacing(16)
        
        # Gráfico de Radar (Distribuição Muscular)
        chart_card = QFrame()
        chart_card.setStyleSheet(
            "QFrame { background:#0a0a0a; border:1px solid #2a2a2a; border-radius:12px; }"
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
        # Período fixo: últimos 30 dias
        return 30
    
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
    

    
    def on_workout_finished(self, payload: dict):
        """Callback quando um treino é finalizado."""
        if not payload:
            return
        self.refresh()

