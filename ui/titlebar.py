"""
ui/titlebar.py
Componentes reutilizáveis de titlebar frameless para MainWindow e QDialogs.

Exporta:
  - make_wm_buttons(win)  → QWidget container com btn_minimize + btn_close
  - build_dialog_titlebar(dlg, title) → (QWidget titlebar, drag_press_fn, drag_move_fn)
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from ui.theme import C_BORDER


# ---------------------------------------------------------------------------
# _SquareIconButton — botão com quadrado cinza desenhado via QPainter
# ---------------------------------------------------------------------------

class _SquareIconButton(QPushButton):
    """Botão de fullscreen com ícone de quadrado branco desenhado via QPainter."""

    def __init__(self):
        super().__init__()
        self.setFixedSize(35, 30)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 7px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #333333;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        w, h = self.width(), self.height()
        size = 9
        x = (w - size) // 2
        y = (h - size) // 2
        from PySide6.QtGui import QPen
        pen = QPen(QColor("#ffffff"))
        pen.setWidth(2)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawRect(x, y, size, size)
        p.end()

# ---------------------------------------------------------------------------
# QSS dos botões — usa objectName para máxima especificidade e vence o global
# ---------------------------------------------------------------------------

_BTN_BASE = """
    QPushButton#{name} {{
        background-color: transparent;
        color: #ffffff;
        border: none;
        border-radius: 7px;
        font-size: {fsize}px;
        font-weight: 900;
        min-width: 35px;
        min-height: 30px;
        max-width: 35px;
        max-height: 30px;
        padding: 0px;
        {extra}
    }}
    QPushButton#{name}:hover {{
        background-color: {hover_bg};
        color: {hover_fg};
        border-color: {hover_border};
    }}
    QPushButton#{name}:pressed {{
        background-color: {pressed_bg};
    }}
"""


def _btn_qss(name: str, fsize: int, extra: str,
             hover_bg: str, hover_fg: str, hover_border: str,
             pressed_bg: str) -> str:
    return _BTN_BASE.format(
        name=name, fsize=fsize, extra=extra,
        hover_bg=hover_bg, hover_fg=hover_fg,
        hover_border=hover_border, pressed_bg=pressed_bg,
    )


# ---------------------------------------------------------------------------
# make_wm_buttons — container com minimizar + fechar
# ---------------------------------------------------------------------------

def _toggle_fullscreen(win: QWidget) -> None:
    if win.isFullScreen():
        win.showNormal()
    else:
        win.showFullScreen()


def make_wm_buttons(win: QWidget, *, show_minimize: bool = True, show_fullscreen: bool = True) -> QWidget:
    """
    Retorna um QWidget container com os botões de controle de janela.
    Conecta automaticamente minimize → win.showMinimized(), close → win.close().

    Args:
        win: a janela que será controlada (QMainWindow ou QDialog)
        show_minimize: False para dialogs que não precisam de minimizar
        show_fullscreen: False para dialogs que não precisam de tela cheia
    """
    container = QWidget()
    container.setObjectName("wm_ctrl_box")
    container.setStyleSheet(
        "QWidget#wm_ctrl_box {"
        "  background: #1e1e1e;"
        f"  border: 1px solid {C_BORDER};"
        "  border-radius: 10px;"
        "}"
    )

    lay = QHBoxLayout(container)
    lay.setContentsMargins(5, 5, 5, 5)
    lay.setSpacing(4)

    if show_minimize:
        btn_min = QPushButton("—")
        btn_min.setObjectName("btn_minimize")
        btn_min.setCursor(Qt.PointingHandCursor)
        btn_min.setStyleSheet(_btn_qss(
            name="btn_minimize",
            fsize=16,
            extra="padding-bottom: 2px;",
            hover_bg="#333333",
            hover_fg="#ffffff",
            hover_border="#777777",
            pressed_bg="#222222",
        ))
        btn_min.clicked.connect(win.showMinimized)
        lay.addWidget(btn_min)

    if show_fullscreen:
        btn_fs = _SquareIconButton()
        btn_fs.setCursor(Qt.PointingHandCursor)
        btn_fs.setToolTip("Tela cheia")
        btn_fs.clicked.connect(lambda: _toggle_fullscreen(win))
        lay.addWidget(btn_fs)

    btn_close = QPushButton("✕")
    btn_close.setObjectName("btn_close")
    btn_close.setCursor(Qt.PointingHandCursor)
    btn_close.setStyleSheet(_btn_qss(
        name="btn_close",
        fsize=13,
        extra="",
        hover_bg="#e81123",
        hover_fg="#ffffff",
        hover_border="#e81123",
        pressed_bg="#c0000f",
    ))
    btn_close.clicked.connect(win.close)
    lay.addWidget(btn_close)

    return container


# ---------------------------------------------------------------------------
# build_dialog_titlebar — titlebar completa para QDialog
# ---------------------------------------------------------------------------

def build_dialog_titlebar(dlg: QWidget, title: str) -> QWidget:
    """
    Constrói e retorna a titlebar de um QDialog frameless.
    Inclui: label de título (esquerda) + botão fechar (direita).
    O drag é implementado via override de mousePressEvent/mouseMoveEvent no widget retornado.
    """
    bar = _DraggableTitleBar(dlg, title)
    return bar


# ---------------------------------------------------------------------------
# _DraggableTitleBar — titlebar interna com drag embutido
# ---------------------------------------------------------------------------

class _DraggableTitleBar(QWidget):
    def __init__(self, win: QWidget, title: str):
        super().__init__(win)
        self._win      = win
        self._drag_pos = QPoint()
        self._dragging = False

        self.setFixedHeight(44)
        self.setStyleSheet(
            "background: #1a1a1a;"
            f"border-bottom: 1px solid {C_BORDER};"
            "border-top-left-radius: 14px;"
            "border-top-right-radius: 14px;"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 8, 0)
        lay.setSpacing(8)

        lbl = QLabel(title)
        lbl.setStyleSheet(
            "color: #9ca3af; font-size: 13px; font-weight: 600;"
            "background: transparent; border: none;"
        )
        lay.addWidget(lbl)
        lay.addStretch()

        # Botão fechar (sem minimizar em dialogs)
        ctrl = make_wm_buttons(win, show_minimize=False)
        lay.addWidget(ctrl)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            from PySide6.QtGui import QCursor
            self._drag_pos = QCursor.pos() - self._win.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.LeftButton:
            from PySide6.QtGui import QCursor
            self._win.move(QCursor.pos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        event.accept()
