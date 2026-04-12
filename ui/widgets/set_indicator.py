"""
ui/widgets/set_indicator.py
Indicador visual de séries via fileira de círculos desenhados com QPainter.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ui.theme import C_BORDER, C_GREEN

_CIRCLE_D = 14   # diâmetro px
_GAP      = 8    # espaço entre círculos px


class SetIndicatorWidget(QWidget):
    """
    Fileira de círculos representando o estado das séries de um exercício.

    Estados por índice:
      - i < sets_done          → preenchido (C_GREEN)
      - i == sets_done         → atual: borda C_GREEN, fundo transparente
      - i > sets_done          → pendente: borda C_BORDER, fundo transparente
    """

    def __init__(self, sets_total: int = 4, sets_done: int = 0, parent=None):
        super().__init__(parent)
        self._total = max(sets_total, 1)
        self._done  = max(0, min(sets_done, self._total))
        self.setFixedHeight(30)
        self._update_min_width()

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def update_state(self, sets_total: int, sets_done: int):
        """Atualiza totais e redesenha."""
        self._total = max(sets_total, 1)
        self._done  = max(0, min(sets_done, self._total))
        self._update_min_width()
        self.update()

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _update_min_width(self):
        w = self._total * _CIRCLE_D + (self._total - 1) * _GAP
        self.setMinimumWidth(w)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        total_w = self._total * _CIRCLE_D + (self._total - 1) * _GAP
        x0 = (self.width() - total_w) // 2          # centraliza horizontalmente
        cy = self.height() // 2                      # centro vertical

        color_green  = QColor(C_GREEN)
        color_border = QColor(C_BORDER)

        for i in range(self._total):
            x = x0 + i * (_CIRCLE_D + _GAP)
            rect_x = x
            rect_y = cy - _CIRCLE_D // 2

            if i < self._done:
                # Concluída — preenchida
                p.setPen(Qt.NoPen)
                p.setBrush(color_green)
            elif i == self._done:
                # Atual — borda verde, sem preenchimento
                pen = QPen(color_green, 2)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)
            else:
                # Pendente — borda cinza, sem preenchimento
                pen = QPen(color_border, 1)
                p.setPen(pen)
                p.setBrush(Qt.NoBrush)

            p.drawEllipse(rect_x, rect_y, _CIRCLE_D, _CIRCLE_D)

        p.end()
