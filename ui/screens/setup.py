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
    RADIUS_MD, RADIUS_LG, neon_glow,
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
    f"QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus"
    f"{{ border:2px solid {C_GREEN}; }}"
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
        f"QPushButton:hover {{ background:#8ad900; }}"
        f"QPushButton:pressed {{ background:#84cc16; }}"
    )
    b.setCursor(Qt.PointingHandCursor)
    # Não aplica efeito neon nos botões primários para mantê-los visíveis
    return b


def _ghost_btn(text: str) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(50)
    b.setStyleSheet(
        f"background:transparent; color:{C_TEXT2}; font-size:15px; font-weight:600;"
        f"border:2px solid {C_BORDER}; border-radius:12px; padding:0 24px;"
        f"QPushButton:hover {{ border-color:{C_GREEN}; color:#fff; background:rgba(162, 255, 0, 0.08); }}"
    )
    b.setCursor(Qt.PointingHandCursor)
    return b


def _selectable_tile(text: str, large: bool = False) -> QPushButton:
    """Cria um botão estilo 'tile' selecionável com efeito de glow."""
    b = QPushButton(text)
    b.setCheckable(True)
    b.setStyleSheet(
        f"QPushButton {{"
        f"  background:#1e1e1e; color:{C_TEXT2}; font-size:15px; font-weight:700;"
        f"  border:2px solid {C_BORDER}; border-radius:12px;"
        f"  padding:16px 20px;"
        f"  min-height:50px;"
        f"}}"
        f"QPushButton:hover {{"
        f"  border-color:{C_GREEN}; color:#fff; background:#1a1a1a;"
        f"}}"
        f"QPushButton:checked {{"
        f"  background:{C_GREEN}; color:#000; border:2px solid {C_GREEN};"
        f"  font-weight:800;"
        f"}}"
        f"QPushButton:checked:hover {{"
        f"  background:#8ad900;"
        f"}}"
    )
    b.setCursor(Qt.PointingHandCursor)
    return b


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
        self.setFixedWidth(700)
        self.setStyleSheet(
            f"background:#1e1e1e; border:1px solid #2a2a2a; border-radius:20px;"
        )

        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(50, 40, 50, 40)
        self._lay.setSpacing(16)

        # Título com ícone
        t = QLabel(title)
        t.setStyleSheet("color:#fff; font-size:28px; font-weight:800; background:transparent; border:none;")
        self._lay.addWidget(t)

        # Subtítulo
        s = QLabel(subtitle)
        s.setStyleSheet(f"color:#6b7280; font-size:15px; background:transparent; border:none;")
        self._lay.addWidget(s)

        # Espaçamento
        self._lay.addSpacing(10)

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
            d.setFixedSize(60, 6)
            d.setStyleSheet(f"background:#2a2a2a; border-radius:3px;")
            self._dots.append(d)
            lay.addWidget(d)
        lay.addStretch()

    def set_step(self, idx: int):
        for i, d in enumerate(self._dots):
            if i <= idx:
                d.setStyleSheet(f"background:{C_GREEN}; border-radius:3px;")
            else:
                d.setStyleSheet(f"background:#2a2a2a; border-radius:3px;")


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
        Setup screen com 4 etapas: Nome, Medidas, Gênero e Meta.
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
        body_lay.setContentsMargins(0, 40, 0, 40)
        body_lay.setSpacing(30)

        # Logo centralizado
        logo_lay = QHBoxLayout()
        logo_lay.addStretch()
        logo_icon = QLabel("💪")
        logo_icon.setStyleSheet(f"color:{C_GREEN}; font-size:48px; background:transparent; border:none;")
        logo_lay.addWidget(logo_icon)
        logo_text = QLabel("GYMNight")
        logo_text.setStyleSheet(f"color:#fff; font-size:36px; font-weight:800; background:transparent; border:none;")
        logo_lay.addWidget(logo_text)
        logo_lay.addStretch()
        body_lay.addLayout(logo_lay)

        # Dots de progresso
        self._dots = _ProgressDots(4)
        body_lay.addWidget(self._dots)

        # Inner stack com os 4 passos
        self._stack = QStackedWidget()
        self._stack.setStyleSheet("background:transparent;")

        self._page0 = self._build_step0()
        self._page1 = self._build_step1()
        self._page2 = self._build_step2()
        self._page3 = self._build_step3()

        self._stack.addWidget(self._page0)
        self._stack.addWidget(self._page1)
        self._stack.addWidget(self._page2)
        self._stack.addWidget(self._page3)

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
        """Passo 1 — Nome."""
        card = _StepCard("👤 SEU NOME", "Como você quer ser chamado?")
        lay = card.content_layout()

        self._name = QLineEdit()
        self._name.setPlaceholderText("Ex: João")
        self._name.setStyleSheet(_FIELD_FOCUS)
        self._name.setFixedHeight(56)
        lay.addWidget(self._name)

        self._err0 = QLabel("")
        self._err0.setStyleSheet(_ERR)
        self._err0.hide()
        lay.addWidget(self._err0)

        lay.addSpacing(20)
        btn_next = _primary_btn("Próximo →")
        btn_next.clicked.connect(self._next_from_0)
        lay.addWidget(btn_next)

        return card

    def _build_step1(self) -> QWidget:
        """Passo 2 — Medidas: Peso e Altura."""
        card = _StepCard("⚖️ MEDIDAS", "Informe seu peso e altura atuais")
        lay = card.content_layout()

        row = QHBoxLayout()
        row.setSpacing(16)
        
        # Peso
        col_weight = QVBoxLayout()
        col_weight.setSpacing(8)
        col_weight.addWidget(_field_label("Peso (kg)"))
        self._weight = QDoubleSpinBox()
        self._weight.setRange(30.0, 300.0)
        self._weight.setValue(75.0)
        self._weight.setDecimals(0)
        self._weight.setButtonSymbols(QDoubleSpinBox.NoButtons)
        self._weight.setStyleSheet(_FIELD_FOCUS)
        self._weight.setFixedHeight(56)
        col_weight.addWidget(self._weight)
        row.addLayout(col_weight)

        # Altura
        col_height = QVBoxLayout()
        col_height.setSpacing(8)
        col_height.addWidget(_field_label("Altura (cm)"))
        self._height = QSpinBox()
        self._height.setRange(100, 250)
        self._height.setValue(175)
        self._height.setButtonSymbols(QSpinBox.NoButtons)
        self._height.setStyleSheet(_FIELD_FOCUS)
        self._height.setFixedHeight(56)
        col_height.addWidget(self._height)
        row.addLayout(col_height)
        
        lay.addLayout(row)

        lay.addSpacing(20)
        btn_next = _primary_btn("Próximo →")
        btn_next.clicked.connect(lambda: self._goto(2))
        lay.addWidget(btn_next)
        
        lay.addSpacing(10)
        btn_back = QPushButton("Voltar")
        btn_back.setStyleSheet(f"background:transparent; color:{C_TEXT3}; border:none; font-size:14px;")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.clicked.connect(lambda: self._goto(0))
        lay.addWidget(btn_back, 0, Qt.AlignCenter)

        return card

    def _build_step2(self) -> QWidget:
        """Passo 3 — Gênero."""
        card = _StepCard("🏷️ GÊNERO", "Selecione seu gênero")
        lay = card.content_layout()

        self._gender_buttons = []
        gender_options = [
            ("Masculino", "male"),
            ("Feminino", "female"),
            ("Outro", "other")
        ]
        
        for text, value in gender_options:
            btn = _selectable_tile(text, large=False)
            btn.setFixedHeight(56)
            btn.setProperty("gender_value", value)
            btn.clicked.connect(lambda checked, b=btn: self._select_gender(b))
            self._gender_buttons.append(btn)
            lay.addWidget(btn)
        
        lay.addSpacing(20)
        btn_next = _primary_btn("Próximo →")
        btn_next.clicked.connect(lambda: self._goto(3))
        lay.addWidget(btn_next)
        
        lay.addSpacing(10)
        btn_back = QPushButton("Voltar")
        btn_back.setStyleSheet(f"background:transparent; color:{C_TEXT3}; border:none; font-size:14px;")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.clicked.connect(lambda: self._goto(1))
        lay.addWidget(btn_back, 0, Qt.AlignCenter)

        # Seleciona masculino por padrão
        self._gender_buttons[0].setChecked(True)

        return card

    def _build_step3(self) -> QWidget:
        """Passo 4 — Meta."""
        card = _StepCard("🎯 SUA META", "Qual seu objetivo principal?")
        lay = card.content_layout()

        self._goal_buttons = []
        goal_options = [
            ("Hipertrofia", "Ganho de massa muscular"),
            ("Emagrecimento", "Perda de gordura"),
            ("Resistência", "Condicionamento físico"),
            ("Saúde", "Qualidade de vida geral")
        ]
        
        for title, subtitle in goal_options:
            btn = self._create_goal_tile(title, subtitle)
            btn.clicked.connect(lambda checked, b=btn: self._select_goal(b))
            self._goal_buttons.append(btn)
            lay.addWidget(btn)
        
        lay.addSpacing(20)
        self._btn_finish = _primary_btn("Começar →")
        self._btn_finish.clicked.connect(self._finish)
        lay.addWidget(self._btn_finish)
        
        lay.addSpacing(10)
        btn_back = QPushButton("Voltar")
        btn_back.setStyleSheet(f"background:transparent; color:{C_TEXT3}; border:none; font-size:14px;")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.clicked.connect(lambda: self._goto(2))
        lay.addWidget(btn_back, 0, Qt.AlignCenter)

        # Seleciona hipertrofia por padrão
        self._goal_buttons[0].setChecked(True)

        return card

    def _create_goal_tile(self, title: str, subtitle: str) -> QPushButton:
        """Cria um tile de meta com título e subtítulo."""
        btn = QPushButton()
        btn.setCheckable(True)
        btn.setFixedHeight(70)
        btn.setCursor(Qt.PointingHandCursor)
        
        # Layout interno do botão
        btn_layout = QVBoxLayout(btn)
        btn_layout.setContentsMargins(20, 12, 20, 12)
        btn_layout.setSpacing(4)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color:#fff; font-size:16px; font-weight:700; background:transparent; border:none;")
        btn_layout.addWidget(title_lbl)
        
        subtitle_lbl = QLabel(subtitle)
        subtitle_lbl.setStyleSheet("color:#6b7280; font-size:13px; background:transparent; border:none;")
        btn_layout.addWidget(subtitle_lbl)
        
        btn.setStyleSheet(
            f"QPushButton {{"
            f"  background:#1e1e1e; color:#fff;"
            f"  border:2px solid {C_BORDER}; border-radius:12px;"
            f"  text-align:left;"
            f"}}"
            f"QPushButton:hover {{"
            f"  border-color:{C_GREEN}; background:#1a1a1a;"
            f"}}"
            f"QPushButton:checked {{"
            f"  background:#1e1e1e; border:2px solid {C_GREEN};"
            f"}}"
            f"QPushButton:checked:hover {{"
            f"  background:#1a1a1a;"
            f"}}"
        )
        
        return btn
        """Passo 3 — Objetivos: Meta e Frequência com tiles selecionáveis."""
        from PySide6.QtWidgets import QScrollArea, QButtonGroup
        
        card = _StepCard("Seus objetivos", "Passo 3 de 3 · Metas")
        lay = card.content_layout()
        
        # Criar área de scroll que ocupa todo o espaço disponível
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ background:{C_CARD}; border:none; }}"
            f"QScrollBar:vertical {{"
            f"  background:#1a1a1a; width:6px; border-radius:3px; margin:0px;"
            f"}}"
            f"QScrollBar::handle:vertical {{"
            f"  background:#333; border-radius:3px; min-height:30px;"
            f"}}"
            f"QScrollBar::handle:vertical:hover {{"
            f"  background:{C_GREEN};"
            f"}}"
            f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{"
            f"  height:0px; background:none; border:none;"
            f"}}"
            f"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{"
            f"  background:none;"
            f"}}"
        )
        
        # Widget de conteúdo dentro do scroll - TUDO vai aqui
        scroll_content = QWidget()
        scroll_content.setStyleSheet(f"background:{C_CARD}; border:none;")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 8, 0)
        content_layout.setSpacing(15)
        
        # 1. Label 'Objetivo'
        content_layout.addWidget(_field_label("Objetivo"))
        
        # 2. Lista vertical de botões de objetivo
        self._goal_buttons = []
        goal_options = ["Hipertrofia", "Definição", "Força", "Saúde"]
        
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

    def _select_gender(self, selected_btn: QPushButton):
        """Garante que apenas um botão de gênero esteja selecionado."""
        for btn in self._gender_buttons:
            if btn != selected_btn:
                btn.setChecked(False)
        selected_btn.setChecked(True)

    def _select_goal(self, selected_btn: QPushButton):
        """Garante que apenas um botão de objetivo esteja selecionado."""
        for btn in self._goal_buttons:
            if btn != selected_btn:
                btn.setChecked(False)
                btn.setGraphicsEffect(None)
        selected_btn.setChecked(True)

    def _finish(self):
        # Coleta o gênero selecionado
        selected_gender = "male"
        for btn in self._gender_buttons:
            if btn.isChecked():
                selected_gender = btn.property("gender_value")
                break
        
        # Coleta o objetivo selecionado
        selected_goal = "Hipertrofia"
        for btn in self._goal_buttons:
            if btn.isChecked():
                # Pega o texto do primeiro QLabel filho
                title_lbl = btn.findChild(QLabel)
                if title_lbl:
                    selected_goal = title_lbl.text()
                break
        
        data = {
            "name":      self._name.text().strip(),
            "weight":    self._weight.value(),
            "height":    self._height.value(),
            "gender":    selected_gender,
            "goal":      selected_goal,
            "frequency": 4,  # padrão
        }
        save_user_data(data)
        self.setup_complete.emit(data)
