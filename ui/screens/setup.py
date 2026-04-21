"""
ui/screens/setup.py
Tela de configuração inicial em 3 etapas.
Mantém a titlebar do GYMNight visível em todas as etapas.
"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QCursor, QColor
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QStackedWidget, QVBoxLayout,
    QWidget, QLineEdit, QApplication, QGraphicsDropShadowEffect,
    QSpacerItem, QSizePolicy,
)

from ui.theme import (
    C_BORDER, C_CARD, C_GREEN, C_SURFACE, C_TEXT2, C_TEXT3,
    RADIUS_MD, RADIUS_LG,
)
from ui.titlebar import make_wm_buttons

USER_DATA_PATH = Path("user_data.json")

# ---------------------------------------------------------------------------
# Persistência
# ---------------------------------------------------------------------------

def load_user_data() -> dict | None:
    if USER_DATA_PATH.exists():
        try:
            return json.loads(USER_DATA_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def save_user_data(data: dict) -> None:
    USER_DATA_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Helpers de estilo
# ---------------------------------------------------------------------------

_FIELD = (
    f"background:#1e1e1e; color:#fff; border:2px solid {C_BORDER};"
    f"border-radius:12px; padding:14px 18px; font-size:15px;"
    f"QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus"
    f"{{ border-color:{C_GREEN}; }}"
)

_FIELD_FOCUS = (
    f"background:#1e1e1e; color:#fff; border:2px solid {C_BORDER};"
    f"border-radius:12px; padding:14px 18px; font-size:15px;"
)

_LBL = f"color:{C_TEXT2}; font-size:14px; font-weight:600; background:transparent; border:none;"
_ERR = "color:#f87171; font-size:13px; background:transparent; border:none;"


def _field_label(text: str) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(_LBL)
    return l


def _input_row(label_widget: QLabel, field: QWidget) -> QVBoxLayout:
    col = QVBoxLayout()
    col.setSpacing(6)
    col.addWidget(label_widget)
    col.addWidget(field)
    return col


def _primary_btn(text: str, large: bool = False) -> QPushButton:
    b = QPushButton(text)
    height = 56 if large else 50
    b.setFixedHeight(height)
    b.setStyleSheet(
        f"background:{C_GREEN}; color:#000; font-size:16px; font-weight:800;"
        f"border:none; border-radius:12px; padding:0 24px;"
        f"QPushButton:hover {{ background:#bef264; }}"
        f"QPushButton:pressed {{ background:#84cc16; }}"
    )
    b.setCursor(Qt.PointingHandCursor)
    return b


def _ghost_btn(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(50)
    b.setStyleSheet(
        f"background:transparent; color:{C_TEXT2}; font-size:15px; font-weight:600;"
        f"border:2px solid {C_BORDER}; border-radius:12px; padding:0 24px;"
        f"QPushButton:hover {{ border-color:{C_GREEN}; color:#fff; }}"
    )
    b.setCursor(Qt.PointingHandCursor)
    return b


def _selectable_tile(text: str, large: bool = False) -> QPushButton:
    """Cria um botão estilo 'tile' selecionável com efeito de glow."""
    b = QPushButton(text)
    # Não define altura fixa aqui - será definida com setMinimumHeight no layout
    b.setCheckable(True)
    b.setStyleSheet(
        f"QPushButton {{"
        f"  background:#1e1e1e; color:{C_TEXT2}; font-size:15px; font-weight:700;"
        f"  border:2px solid {C_BORDER}; border-radius:12px; padding:0 20px;"
        f"}}"
        f"QPushButton:hover {{"
        f"  border-color:#555; color:#fff;"
        f"}}"
        f"QPushButton:checked {{"
        f"  background:{C_GREEN}; color:#000; border:2px solid {C_GREEN};"
        f"  font-weight:800;"
        f"}}"
    )
    b.setCursor(Qt.PointingHandCursor)
    return b


def _add_glow(widget: QWidget, color: str = C_GREEN, blur: int = 20):
    """Adiciona efeito de glow (sombra colorida) a um widget."""
    effect = QGraphicsDropShadowEffect()
    effect.setBlurRadius(blur)
    effect.setColor(QColor(color))
    effect.setOffset(0, 0)
    widget.setGraphicsEffect(effect)


# ---------------------------------------------------------------------------
# _SetupTitleBar — titlebar própria do setup (sem nav buttons)
# ---------------------------------------------------------------------------

class _SetupTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos: QPoint | None = None

        self.setFixedHeight(52)
        self.setStyleSheet(
            f"background:{C_SURFACE};"
            f"border-bottom:1px solid {C_BORDER};"
            "border-top-left-radius:12px;"
            "border-top-right-radius:12px;"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(20, 0, 0, 0)
        lay.setSpacing(8)

        icon = QLabel("⚡")
        icon.setStyleSheet(
            f"color:{C_GREEN}; font-size:18px; font-weight:900;"
            "background:transparent; border:none;"
        )
        icon.setAttribute(Qt.WA_TransparentForMouseEvents)

        text = QLabel("GYMNight")
        text.setStyleSheet(
            "color:#fff; font-size:15px; font-weight:800; letter-spacing:1px;"
            "background:transparent; border:none;"
        )
        text.setAttribute(Qt.WA_TransparentForMouseEvents)

        lay.addWidget(icon)
        lay.addWidget(text)
        lay.addStretch()
        
        # Get the main window reference for window controls
        main_win = self.window()
        lay.addWidget(make_wm_buttons(main_win, show_minimize=True, show_fullscreen=False))

    # drag support
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            main_win = self.window()
            handle = main_win.windowHandle()
            if handle and hasattr(handle, "startSystemMove"):
                handle.startSystemMove()
            else:
                self._drag_pos = QCursor.pos() - main_win.pos()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            main_win = self.window()
            main_win.move(QCursor.pos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


# ---------------------------------------------------------------------------
# _StepCard — card branco-escuro centralizado com título/subtítulo
# ---------------------------------------------------------------------------

class _StepCard(QWidget):
    def __init__(self, title: str, subtitle: str, parent=None):
        super().__init__(parent)
        self.setFixedWidth(520)
        self.setStyleSheet(
            f"background:{C_CARD}; border:2px solid {C_BORDER}; border-radius:16px;"
        )

        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(40, 36, 40, 36)
        self._lay.setSpacing(24)

        # Título
        t = QLabel(title)
        t.setStyleSheet("color:#fff; font-size:24px; font-weight:800; background:transparent; border:none;")
        self._lay.addWidget(t)

        # Subtítulo
        s = QLabel(subtitle)
        s.setStyleSheet(f"color:{C_TEXT3}; font-size:14px; background:transparent; border:none;")
        self._lay.addWidget(s)

        # Separador visual
        sep = QWidget()
        sep.setFixedHeight(2)
        sep.setStyleSheet(f"background:{C_BORDER};")
        self._lay.addWidget(sep)

    def content_layout(self) -> QVBoxLayout:
        return self._lay


# ---------------------------------------------------------------------------
# _ProgressDots — indicador de etapa
# ---------------------------------------------------------------------------

class _ProgressDots(QWidget):
    def __init__(self, total: int, parent=None):
        super().__init__(parent)
        self._total = total
        self._dots: list[QLabel] = []

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addStretch()
        for _ in range(total):
            d = QLabel()
            d.setFixedSize(8, 8)
            d.setStyleSheet(f"background:{C_BORDER}; border-radius:4px;")
            self._dots.append(d)
            lay.addWidget(d)
        lay.addStretch()

    def set_step(self, idx: int):
        for i, d in enumerate(self._dots):
            if i == idx:
                d.setStyleSheet(f"background:{C_GREEN}; border-radius:4px;")
                d.setFixedSize(20, 8)
            else:
                d.setStyleSheet(f"background:{C_BORDER}; border-radius:4px;")
                d.setFixedSize(8, 8)


# ---------------------------------------------------------------------------
# SetupScreen
# ---------------------------------------------------------------------------

class SetupScreen(QWidget):
    """
    Tela de setup em 3 etapas com titlebar própria.
    Emite `setup_complete` com o dict de dados do usuário.
    """

    setup_complete = Signal(dict)

    def __init__(self, parent=None):
        """
        Setup screen com 3 etapas: Identidade, Métricas e Objetivos.
        """
        super().__init__(parent)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Titlebar
        self._titlebar = _SetupTitleBar(self)
        root.addWidget(self._titlebar)

        # Área de conteúdo
        body = QWidget()
        body.setStyleSheet(f"background:{C_SURFACE};")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 32, 0, 32)
        body_lay.setSpacing(20)

        # Dots de progresso
        self._dots = _ProgressDots(3)
        body_lay.addWidget(self._dots)

        # Inner stack com os 3 passos
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background:transparent;")

        self._page0 = self._build_step0()
        self._page1 = self._build_step1()
        self._page2 = self._build_step2()

        self._stack.addWidget(self._page0)
        self._stack.addWidget(self._page1)
        self._stack.addWidget(self._page2)

        # Centraliza o stack
        stack_wrap = QHBoxLayout()
        stack_wrap.addStretch()
        stack_wrap.addWidget(self._stack)
        stack_wrap.addStretch()
        body_lay.addLayout(stack_wrap)
        body_lay.addStretch()

        root.addWidget(body)

        self._goto(0)

    # ------------------------------------------------------------------
    # Páginas
    # ------------------------------------------------------------------

    def _build_step0(self) -> QWidget:
        """Passo 1 — Identidade: Nome e Idade."""
        card = _StepCard("Quem é você?", "Passo 1 de 3 · Identidade")
        lay = card.content_layout()

        self._name = QLineEdit()
        self._name.setPlaceholderText("Ex: Pedro")
        self._name.setStyleSheet(_FIELD_FOCUS)
        self._name.setFixedHeight(50)
        lay.addLayout(_input_row(_field_label("Nome"), self._name))

        self._age = QSpinBox()
        self._age.setRange(10, 100)
        self._age.setValue(25)
        self._age.setStyleSheet(_FIELD_FOCUS)
        self._age.setFixedHeight(50)
        lay.addLayout(_input_row(_field_label("Idade"), self._age))

        self._err0 = QLabel("")
        self._err0.setStyleSheet(_ERR)
        self._err0.hide()
        lay.addWidget(self._err0)

        lay.addSpacing(10)
        btn_next = _primary_btn("Próximo →")
        btn_next.clicked.connect(self._next_from_0)
        lay.addWidget(btn_next)

        return card

    def _build_step1(self) -> QWidget:
        """Passo 2 — Métricas: Peso e Altura."""
        card = _StepCard("Suas medidas", "Passo 2 de 3 · Métricas")
        lay = card.content_layout()

        self._weight = QDoubleSpinBox()
        self._weight.setRange(30.0, 300.0)
        self._weight.setValue(75.0)
        self._weight.setSuffix(" kg")
        self._weight.setDecimals(1)
        self._weight.setStyleSheet(_FIELD_FOCUS)
        self._weight.setFixedHeight(50)
        lay.addLayout(_input_row(_field_label("Peso"), self._weight))

        self._height = QSpinBox()
        self._height.setRange(100, 250)
        self._height.setValue(175)
        self._height.setSuffix(" cm")
        self._height.setStyleSheet(_FIELD_FOCUS)
        self._height.setFixedHeight(50)
        lay.addLayout(_input_row(_field_label("Altura"), self._height))

        lay.addSpacing(10)
        btns = QHBoxLayout()
        btns.setSpacing(12)
        btn_back = _ghost_btn("← Voltar")
        btn_back.clicked.connect(lambda: self._goto(0))
        btn_next = _primary_btn("Próximo →")
        btn_next.clicked.connect(lambda: self._goto(2))
        btns.addWidget(btn_back)
        btns.addWidget(btn_next)
        lay.addLayout(btns)

        return card

    def _build_step2(self) -> QWidget:
        """Passo 3 — Objetivos: Meta e Frequência com tiles selecionáveis."""
        card = _StepCard("Seus objetivos", "Passo 3 de 3 · Metas")
        lay = card.content_layout()

        # Seção de Objetivo
        lay.addWidget(_field_label("Objetivo"))
        lay.addSpacing(8)
        
        # Layout dedicado para os botões de objetivo
        self._goal_buttons = []
        goal_options = ["Hipertrofia", "Definição", "Força", "Saúde"]
        goal_layout = QVBoxLayout()
        goal_layout.setSpacing(10)
        
        for goal in goal_options:
            btn = _selectable_tile(goal, large=True)
            btn.setMinimumHeight(50)
            btn.clicked.connect(lambda checked, b=btn: self._select_goal(b))
            self._goal_buttons.append(btn)
            goal_layout.addWidget(btn)
        
        lay.addLayout(goal_layout)
        
        # Espaçamento para separar as seções
        lay.addSpacing(30)

        # Seção de Frequência
        lay.addWidget(_field_label("Frequência semanal"))
        lay.addSpacing(8)
        
        self._freq_buttons = []
        freq_layout = QHBoxLayout()
        freq_layout.setSpacing(10)
        
        for day in range(1, 8):
            btn = _selectable_tile(str(day))
            btn.setFixedWidth(60)
            btn.setMinimumHeight(50)
            btn.clicked.connect(lambda checked, b=btn: self._select_freq(b))
            self._freq_buttons.append(btn)
            freq_layout.addWidget(btn)
        
        lay.addLayout(freq_layout)
        
        # Spacer expansível para empurrar botões para o fundo
        lay.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Botões de navegação no fundo
        btns = QHBoxLayout()
        btns.setSpacing(12)
        btn_back = _ghost_btn("← Voltar")
        btn_back.clicked.connect(lambda: self._goto(1))
        btns.addWidget(btn_back)
        lay.addLayout(btns)
        
        lay.addSpacing(10)
        
        # Botão Finish grande e proeminente
        self._btn_finish = _primary_btn("Começar a Treinar ✓", large=True)
        self._btn_finish.clicked.connect(self._finish)
        lay.addWidget(self._btn_finish)

        # Seleciona valores padrão
        self._goal_buttons[0].setChecked(True)  # Hipertrofia
        self._freq_buttons[3].setChecked(True)  # 4x semana

        return card

    # ------------------------------------------------------------------
    # Navegação interna
    # ------------------------------------------------------------------

    def _goto(self, idx: int):
        self._stack.setCurrentIndex(idx)
        self._dots.set_step(idx)

    def _next_from_0(self):
        if not self._name.text().strip():
            self._err0.setText("Por favor, insira seu nome.")
            self._err0.show()
            return
        self._err0.hide()
        self._goto(1)

    def _select_goal(self, selected_btn: QPushButton):
        """Garante que apenas um botão de objetivo esteja selecionado."""
        for btn in self._goal_buttons:
            if btn != selected_btn:
                btn.setChecked(False)
        selected_btn.setChecked(True)
        
        # Adiciona efeito de glow ao botão selecionado
        if selected_btn.isChecked():
            _add_glow(selected_btn, C_GREEN, 25)
        else:
            selected_btn.setGraphicsEffect(None)

    def _select_freq(self, selected_btn: QPushButton):
        """Garante que apenas um botão de frequência esteja selecionado."""
        for btn in self._freq_buttons:
            if btn != selected_btn:
                btn.setChecked(False)
        selected_btn.setChecked(True)
        
        # Adiciona efeito de glow ao botão selecionado
        if selected_btn.isChecked():
            _add_glow(selected_btn, C_GREEN, 20)
        else:
            selected_btn.setGraphicsEffect(None)

    def _finish(self):
        # Coleta o objetivo selecionado
        selected_goal = "Hipertrofia"  # padrão
        for btn in self._goal_buttons:
            if btn.isChecked():
                selected_goal = btn.text()
                break
        
        # Coleta a frequência selecionada
        selected_freq = 4  # padrão
        for i, btn in enumerate(self._freq_buttons):
            if btn.isChecked():
                selected_freq = i + 1
                break
        
        data = {
            "name":      self._name.text().strip(),
            "age":       self._age.value(),
            "weight":    self._weight.value(),
            "height":    self._height.value(),
            "goal":      selected_goal,
            "frequency": selected_freq,
        }
        save_user_data(data)
        self.setup_complete.emit(data)
