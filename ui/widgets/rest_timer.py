"""
ui/widgets/rest_timer.py
Widget de descanso entre séries com contagem regressiva.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from ui.theme import C_CARD, C_GREEN, C_TEXT2, C_BORDER, RADIUS_LG


class RestTimerWidget(QWidget):
    """
    Exibe contagem regressiva de descanso entre séries.

    Uso:
        timer = RestTimerWidget(seconds=60)
        timer.rest_finished.connect(on_rest_done)
        timer.start()
    """

    rest_finished = Signal()

    def __init__(self, seconds: int = 60, parent=None):
        super().__init__(parent)
        self._total   = seconds
        self._remaining = seconds
        self._timer   = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._build()
        self._refresh()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build(self):
        self.setStyleSheet(f"""
            RestTimerWidget {{
                background: {C_CARD};
                border-radius: {RADIUS_LG}px;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)
        root.setAlignment(Qt.AlignCenter)

        # Rótulo superior
        lbl_title = QLabel("DESCANSO")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet(
            f"color: {C_TEXT2}; font-size: 13px; font-weight: 600;"
            "background: transparent; border: none;"
        )
        root.addWidget(lbl_title)

        # Contagem regressiva
        self._lbl_time = QLabel()
        self._lbl_time.setAlignment(Qt.AlignCenter)
        self._lbl_time.setStyleSheet(
            f"color: {C_GREEN}; font-size: 48px; font-weight: 700;"
            "background: transparent; border: none;"
        )
        root.addWidget(self._lbl_time)

        # Barra de progresso
        self._progress = QProgressBar()
        self._progress.setRange(0, self._total)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        self._progress.setStyleSheet(f"""
            QProgressBar {{
                background: {C_BORDER};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {C_GREEN};
                border-radius: 3px;
            }}
        """)
        root.addWidget(self._progress)

        # Botão pular
        self._btn_skip = QPushButton("Pular")
        self._btn_skip.setObjectName("ghost")
        self._btn_skip.setFixedHeight(36)
        self._btn_skip.setCursor(Qt.PointingHandCursor)
        self._btn_skip.clicked.connect(self._skip)
        root.addWidget(self._btn_skip)

    # ------------------------------------------------------------------
    # Controle
    # ------------------------------------------------------------------

    def start(self):
        """Inicia ou reinicia o timer com o total configurado."""
        self._remaining = self._total
        self._refresh()
        self._timer.start()

    def set_duration(self, seconds: int):
        """Redefine a duração e reinicia."""
        self._total     = seconds
        self._remaining = seconds
        self._progress.setRange(0, self._total)
        self._refresh()

    def stop(self):
        self._timer.stop()

    def is_running(self) -> bool:
        return self._timer.isActive()

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _tick(self):
        self._remaining -= 1
        self._refresh()
        if self._remaining <= 0:
            self._timer.stop()
            self.rest_finished.emit()

    def _skip(self):
        self._timer.stop()
        self._remaining = 0
        self._refresh()
        self.rest_finished.emit()

    def _refresh(self):
        self._lbl_time.setText(str(max(self._remaining, 0)))
        self._progress.setValue(self._remaining)
