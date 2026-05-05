"""
ui/window.py
MainWindow: frameless window com titlebar customizada + navegação + QStackedWidget.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, QThread
from PySide6.QtGui import QCursor, QPainter, QPainterPath, QColor
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QStackedWidget, QVBoxLayout, QWidget,
)

from database import DatabaseConnection, seed_muscle_map
from engine import NormalizationEngine, PerformanceAnalyzer, Routine, RoutineManager
from src.ui.theme import C_BORDER, C_GREEN, C_SURFACE, C_TEXT2, RADIUS_MD
from src.ui.titlebar import make_wm_buttons
from src.ui.screens.dashboard import DashboardTab
from src.ui.screens.statistics import StatisticsTab
from src.ui.screens.workouts import WorkoutsTab
from src.ui.screens.active_workout import ActiveWorkoutScreen
from src.ui.screens.setup import SetupScreen, load_user_data
from src.ui.screens.gym_ai import GymAITab
from loguru import logger


# ---------------------------------------------------------------------------
# _RoundedWidget — widget central com cantos arredondados via clip
# ---------------------------------------------------------------------------

class _RoundedWidget(QWidget):
    """Widget central que clipa todos os filhos com border-radius."""

    RADIUS = 15

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # Adiciona padding interno para evitar que o conteúdo toque as bordas
        self.setContentsMargins(0, 0, 0, 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Aplica máscara de região para clipar filhos nos cantos
        from PySide6.QtGui import QRegion
        from PySide6.QtCore import QRect
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), self.RADIUS, self.RADIUS)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # Desenha o fundo
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), self.RADIUS, self.RADIUS)
        p.fillPath(path, QColor(C_SURFACE))
        
        # Desenha uma borda em cinza bem escuro (quase invisível)
        pen = p.pen()
        pen.setColor(QColor("#2a2a2a"))  # Cinza bem escuro, mesma cor do C_BORDER
        pen.setWidth(1)
        p.setPen(pen)
        p.drawPath(path)
        
        p.end()


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
            f"background:{C_SURFACE};"
            f"border-bottom:1px solid {C_BORDER};"
            f"border-top-left-radius:15px;"
            f"border-top-right-radius:15px;"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 0, 0)
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
# _TitleBarDragFilter — event filter na QApplication para drag no X11/WSL
# ---------------------------------------------------------------------------

class _TitleBarDragFilter(QObject):
    """
    Drag da titlebar compatível com X11/WSL.
    Usa windowHandle().startSystemMove() (Qt6) para delegar o drag ao WM,
    com fallback manual via QCursor caso não esteja disponível.
    """

    def __init__(self, titlebar: _TitleBar, win: QMainWindow):
        super().__init__(win)
        self._titlebar = titlebar
        self._win      = win
        self._drag_pos: QPoint | None = None

    def _in_titlebar(self, global_pos: QPoint) -> bool:
        local = self._titlebar.mapFromGlobal(global_pos)
        return self._titlebar.rect().contains(local)

    def _over_button(self, global_pos: QPoint) -> bool:
        local = self._titlebar.mapFromGlobal(global_pos)
        child = self._titlebar.childAt(local)
        return isinstance(child, QPushButton)

    def _try_system_move(self) -> bool:
        """Tenta usar o drag nativo do WM (funciona no X11/Wayland/WSL)."""
        handle = self._win.windowHandle()
        if handle is not None and hasattr(handle, "startSystemMove"):
            handle.startSystemMove()
            return True
        return False

    def eventFilter(self, obj, event):
        t = event.type()

        if t == QEvent.Type.MouseButtonPress and event.button() == Qt.LeftButton:
            gpos = QCursor.pos()
            if self._in_titlebar(gpos) and not self._over_button(gpos):
                if not self._try_system_move():
                    # fallback manual
                    self._drag_pos = gpos - self._win.pos()

        elif t == QEvent.Type.MouseMove:
            if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
                self._win.move(QCursor.pos() - self._drag_pos)
                return True

        elif t == QEvent.Type.MouseButtonRelease and event.button() == Qt.LeftButton:
            self._drag_pos = None

        elif t == QEvent.Type.MouseButtonDblClick and event.button() == Qt.LeftButton:
            gpos = QCursor.pos()
            if self._in_titlebar(gpos) and not self._over_button(gpos):
                if self._win.isMaximized():
                    self._win.showNormal()
                else:
                    self._win.showMaximized()
                return True

        return False


# ---------------------------------------------------------------------------
# MainWindow
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GYMNight")
        self.setMinimumSize(900, 620)
        self.resize(1100, 720)
        # Configurações de transparência e frameless para evitar vazamento de cor nos cantos
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

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

        # Outer rounded container
        central = _RoundedWidget()
        central.setObjectName("mainContainer")
        self.setCentralWidget(central)
        # Não aplicar neon_glow diretamente no central para evitar vazamento nos cantos
        
        # Adiciona margem externa para criar espaço de "respiro"
        root = QVBoxLayout(central)
        root.setContentsMargins(1, 1, 1, 1)  # Margem mínima para conter bordas
        root.setSpacing(0)
        
        # Container interno que receberá o conteúdo
        inner_container = QWidget()
        inner_container.setStyleSheet(f"background: {C_SURFACE}; border-radius: 14px;")
        root.addWidget(inner_container)
        
        inner_layout = QVBoxLayout(inner_container)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        # Outer stack: page 0 = Setup, page 1 = Main app
        self._outer_stack = QStackedWidget()
        inner_layout.addWidget(self._outer_stack)

        # --- Page 0: Setup screen ---
        self._setup_screen = SetupScreen()
        self._setup_screen.setup_complete.connect(self._on_setup_complete)
        self._outer_stack.addWidget(self._setup_screen)  # index 0

        # --- Page 1: Main app (titlebar + inner stack) ---
        main_page = QWidget()
        main_lay = QVBoxLayout(main_page)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        self._titlebar = _TitleBar(self)

        self._btn_dash       = QPushButton("Início")
        self._btn_workouts   = QPushButton("Treinos")
        self._btn_statistics = QPushButton("Estatísticas")
        self._btn_gymai      = QPushButton("GymAI")
        for btn in (self._btn_dash, self._btn_workouts, self._btn_statistics, self._btn_gymai):
            btn.setFixedHeight(34)
        self._btn_dash.clicked.connect(lambda: self._navigate(0))
        self._btn_workouts.clicked.connect(lambda: self._navigate(1))
        self._btn_statistics.clicked.connect(lambda: (logger.info("Botão Estatísticas Clicado"), self._navigate(3)))
        self._btn_gymai.clicked.connect(lambda: self._navigate(4))
        self._titlebar.add_nav_button(self._btn_dash)
        self._titlebar.add_nav_button(self._btn_workouts)
        self._titlebar.add_nav_button(self._btn_statistics)
        self._titlebar.add_nav_button(self._btn_gymai)

        main_lay.addWidget(self._titlebar)

        self._stack = QStackedWidget()
        main_lay.addWidget(self._stack)

        self._dash_tab       = DashboardTab(self._db)
        self._workout_tab    = WorkoutsTab(self._db, self._rm, self._norm)
        self._active_tab     = ActiveWorkoutScreen(self._db, self._rm, self._analyzer, self._norm)
        self._statistics_tab = StatisticsTab(self._db)
        self._gymai_tab      = GymAITab()

        self._stack.addWidget(self._dash_tab)       # 0
        self._stack.addWidget(self._workout_tab)    # 1
        self._stack.addWidget(self._active_tab)     # 2
        self._stack.addWidget(self._statistics_tab) # 3
        self._stack.addWidget(self._gymai_tab)      # 4

        self._workout_tab.start_workout.connect(self._go_active)
        self._active_tab.finished.connect(self._go_workouts)
        self._active_tab.finished.connect(self._dash_tab.on_workout_finished)
        self._active_tab.finished.connect(self._statistics_tab.on_workout_finished)

        self._outer_stack.addWidget(main_page)  # index 1

        # Instala o event filter global para drag funcionar no X11/WSL
        self._drag_filter = _TitleBarDragFilter(self._titlebar, self)
        QApplication.instance().installEventFilter(self._drag_filter)

        # Persistência: pula setup se user_data.json já existir
        user_data = load_user_data()
        if user_data:
            self._apply_user_data(user_data)
            self._outer_stack.setCurrentIndex(1)
            self._navigate(0)
        else:
            # Ajusta tamanho da janela para o setup
            self.resize(600, 700)
            self._outer_stack.setCurrentIndex(0)

    # ------------------------------------------------------------------

    def _on_setup_complete(self, data: dict):
        """Chamado quando o usuário termina o setup."""
        self._apply_user_data(data)
        # Restaura tamanho normal da janela
        self.resize(1100, 720)
        self._outer_stack.setCurrentIndex(1)
        self._navigate(0)

    def _apply_user_data(self, data: dict):
        """Atualiza o dashboard com os dados do perfil."""
        self._dash_tab.update_user(data)

    # ------------------------------------------------------------------

    def _navigate(self, idx: int):
        logger.info(f"Navegando para índice: {idx}")
        logger.info(f"Total de widgets no stack: {self._stack.count()}")
        logger.info(f"Índice atual do stack: {self._stack.currentIndex()}")
        
        from src.ui.theme import neon_glow
        active_style = (
            f"background:{C_GREEN}; color:#000; border:none;"
            f" border-radius:{RADIUS_MD}px; padding:0 14px; font-weight:700;"
        )
        inactive_style = (
            f"background:transparent; color:{C_TEXT2};"
            f" border:1px solid {C_BORDER}; border-radius:{RADIUS_MD}px; padding:0 14px;"
        )
        
        # Aplica estilos e efeito neon
        for btn, btn_idx in [(self._btn_dash, 0), (self._btn_workouts, 1), (self._btn_statistics, 3), (self._btn_gymai, 4)]:
            if btn_idx == idx:
                btn.setStyleSheet(active_style)
                neon_glow(btn, C_GREEN, blur=68, opacity=486)
            else:
                btn.setStyleSheet(inactive_style)
                btn.setGraphicsEffect(None)
        
        if idx == 0:
            logger.info("Atualizando Dashboard")
            self._dash_tab.refresh()
        if idx == 3:
            logger.info("Atualizando Estatísticas")
            logger.info(f"Widget de estatísticas visível: {self._statistics_tab.isVisible()}")
            logger.info(f"Widget de estatísticas habilitado: {self._statistics_tab.isEnabled()}")
            self._statistics_tab.refresh()
        
        logger.info(f"Mudando stack para índice: {idx}")
        self._stack.setCurrentIndex(idx)
        logger.info(f"Novo índice do stack: {self._stack.currentIndex()}")
        logger.info(f"Widget atual: {self._stack.currentWidget()}")

    def _go_active(self, routine: Routine, session_id: int):
        self._active_tab.load_routine(routine, session_id)
        self._btn_dash.setEnabled(False)
        self._btn_workouts.setEnabled(False)
        self._btn_statistics.setEnabled(False)
        self._btn_gymai.setEnabled(False)
        self._stack.setCurrentIndex(2)

    def _go_workouts(self, payload: dict = None):
        self._btn_dash.setEnabled(True)
        self._btn_workouts.setEnabled(True)
        self._btn_statistics.setEnabled(True)
        self._btn_gymai.setEnabled(True)
        self._workout_tab.reload()
        self._navigate(1)

    def closeEvent(self, event):
        QApplication.instance().removeEventFilter(self._drag_filter)
        self._worker.quit()
        self._worker.wait()
        self._db.close()
        super().closeEvent(event)
