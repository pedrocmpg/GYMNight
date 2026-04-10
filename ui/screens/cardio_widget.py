"""
ui/screens/cardio_widget.py
Widget de linha de cardio + diálogo de seleção de tipo de cardio.
"""
from __future__ import annotations
import re
import unicodedata
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QDialog, QDoubleSpinBox, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSlider, QVBoxLayout, QWidget,
)

from ui.theme import (
    C_BORDER, C_CARD, C_CARD2, C_GREEN, C_GREEN_BG,
    C_TEXT, C_TEXT2, C_TEXT3, label, separator,
)


# ---------------------------------------------------------------------------
# Parser do tipo_cardios.md
# ---------------------------------------------------------------------------

def _norm(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def parse_cardio_types(md_path: str = "tipo_cardios.md") -> list[dict]:
    """
    Lê tipo_cardios.md e retorna lista de dicts:
    {name, intensity, pse_avg, description}
    """
    path = Path(md_path)
    if not path.exists():
        return []

    results = []
    section_re = re.compile(r"^\|\s*\*\*.*\*\*")

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|"):
                continue
            if ":---" in line or section_re.match(line):
                continue
            cells = [c.strip() for c in line.split("|")]
            cells = [c for c in cells if c]
            if len(cells) < 3:
                continue
            name = cells[0].strip()
            if not name or name.startswith("**"):
                continue
            results.append({
                "name":        name,
                "intensity":   cells[1] if len(cells) > 1 else "",
                "pse_avg":     cells[2] if len(cells) > 2 else "",
                "description": cells[3] if len(cells) > 3 else "",
            })
    return results


# ---------------------------------------------------------------------------
# CardioPickerDialog — autocomplete de tipos de cardio
# ---------------------------------------------------------------------------

class CardioPickerDialog(QDialog):
    """Diálogo com autocomplete para selecionar o tipo de cardio."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self._selected_name: str = ""
        self._cardio_types = parse_cardio_types()
        self.setMinimumWidth(460)
        self._build()

    def _build(self):
        from ui.titlebar import build_dialog_titlebar

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(build_dialog_titlebar(self, "ADICIONAR CARDIO"))

        content = QWidget()
        content.setStyleSheet(
            "background: #242424;"
            "border-bottom-left-radius: 14px;"
            "border-bottom-right-radius: 14px;"
        )
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(14)
        root.addWidget(content)

        self.setStyleSheet(f"QDialog {{ border: 1px solid {C_BORDER}; border-radius: 14px; }}")

        # Campo de busca com popup de lista
        lay.addWidget(label("Tipo de Cardio", "h3"))
        self._search = QLineEdit()
        self._search.setPlaceholderText("Ex: Esteira, Corrida, Bicicleta...")
        self._search.setFixedHeight(42)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {C_CARD};
                color: {C_TEXT};
                border: 1px solid {C_GREEN};
                border-radius: 10px;
                padding: 0 14px;
                font-size: 13px;
            }}
        """)
        lay.addWidget(self._search)

        # Popup de resultados (QListWidget flutuante)
        self._popup = QListWidget(self)
        self._popup.setWindowFlags(Qt.ToolTip)
        self._popup.setFocusPolicy(Qt.NoFocus)
        self._popup.setStyleSheet(f"""
            QListWidget {{
                background: {C_CARD};
                border: 1px solid {C_GREEN};
                border-radius: 8px;
                outline: none;
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 9px 14px;
                color: {C_TEXT2};
                border-bottom: 1px solid {C_BORDER};
            }}
            QListWidget::item:hover {{ background: {C_CARD2}; color: {C_TEXT}; }}
            QListWidget::item:selected {{ background: #1a2e1a; color: {C_GREEN}; }}
        """)
        self._popup.hide()
        self._popup.itemClicked.connect(self._on_item_clicked)

        # Debounce de 100ms para filtrar
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(100)
        self._filter_timer.timeout.connect(self._update_popup)

        self._search.textChanged.connect(lambda _: self._filter_timer.start())
        self._search.mousePressEvent = lambda e: (
            QLineEdit.mousePressEvent(self._search, e),
            self._update_popup()
        )
        self._search.installEventFilter(self)

        # Campos de métricas
        metrics = QFrame()
        metrics.setObjectName("card")
        m_lay = QVBoxLayout(metrics)
        m_lay.setContentsMargins(16, 16, 16, 16)
        m_lay.setSpacing(12)

        # Tempo (obrigatório)
        row1 = QHBoxLayout()
        row1.addWidget(label("Tempo (min) *", "h3"), 1)
        self._duration = QDoubleSpinBox()
        self._duration.setRange(1, 300)
        self._duration.setValue(30)
        self._duration.setSuffix(" min")
        self._duration.setDecimals(0)
        self._duration.setMinimumWidth(120)
        row1.addWidget(self._duration, 1)
        m_lay.addLayout(row1)

        # Distância (opcional)
        row2 = QHBoxLayout()
        row2.addWidget(label("Distância (km)", "h3"), 1)
        self._distance = QDoubleSpinBox()
        self._distance.setRange(0, 200)
        self._distance.setValue(0)
        self._distance.setSuffix(" km")
        self._distance.setDecimals(1)
        self._distance.setMinimumWidth(120)
        self._distance.setSpecialValueText("—")  # 0 = não informado
        row2.addWidget(self._distance, 1)
        m_lay.addLayout(row2)

        # PSE (Escala de Borg 1-10)
        row3 = QHBoxLayout()
        row3.addWidget(label("Esforço (PSE 1-10)", "h3"), 1)
        pse_col = QVBoxLayout()
        self._pse = QSlider(Qt.Horizontal)
        self._pse.setRange(1, 10)
        self._pse.setValue(5)
        self._pse.setTickPosition(QSlider.TicksBelow)
        self._pse.setTickInterval(1)
        self._pse.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 6px;
                background: {C_CARD2};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {C_GREEN};
                width: 18px; height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }}
            QSlider::sub-page:horizontal {{
                background: {C_GREEN};
                border-radius: 3px;
            }}
        """)
        self._pse_lbl = QLabel("5")
        self._pse_lbl.setStyleSheet(f"color:{C_GREEN}; font-size:18px; font-weight:800; min-width:24px; font-family:'Arial';")
        self._pse_lbl.setAlignment(Qt.AlignCenter)
        self._pse.valueChanged.connect(lambda v: self._pse_lbl.setText(str(v)))
        pse_row = QHBoxLayout()
        pse_row.addWidget(self._pse)
        pse_row.addWidget(self._pse_lbl)
        pse_col.addLayout(pse_row)
        # Labels de referência
        ref_row = QHBoxLayout()
        for txt in ["Leve", "Moderado", "Intenso", "Máximo"]:
            l = QLabel(txt)
            l.setStyleSheet(f"color:{C_TEXT3}; font-size:10px;")
            l.setAlignment(Qt.AlignCenter)
            ref_row.addWidget(l)
        pse_col.addLayout(ref_row)
        row3.addLayout(pse_col, 2)
        m_lay.addLayout(row3)

        lay.addWidget(metrics)

        # Botões
        btn_row = QHBoxLayout()
        cancel = QPushButton("✕ Cancelar")
        cancel.setObjectName("ghost")
        cancel.clicked.connect(self.reject)
        confirm = QPushButton("＋ Adicionar")
        confirm.clicked.connect(self._confirm)
        btn_row.addWidget(cancel)
        btn_row.addWidget(confirm)
        lay.addLayout(btn_row)

    def _update_popup(self):
        """Filtra e exibe o popup abaixo do campo de busca."""
        query = _norm(self._search.text())
        self._popup.clear()

        matches = [
            ct for ct in self._cardio_types
            if query == "" or query in _norm(ct["name"])
        ]

        if not matches:
            self._popup.hide()
            return

        for ct in matches[:20]:
            intensity = ct.get("intensity", "")
            text = f"{ct['name']}  [{intensity}]" if intensity else ct["name"]
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, ct["name"])
            self._popup.addItem(item)

        pos = self._search.mapToGlobal(self._search.rect().bottomLeft())
        self._popup.setFixedWidth(self._search.width())
        row_h = self._popup.sizeHintForRow(0) if self._popup.count() > 0 else 36
        self._popup.setFixedHeight(min(280, row_h * min(self._popup.count(), 8) + 8))
        self._popup.move(pos)
        self._popup.show()
        self._popup.raise_()

    def _on_item_clicked(self, item: QListWidgetItem):
        name = item.data(Qt.UserRole)
        self._search.blockSignals(True)
        self._search.setText(name)
        self._search.blockSignals(False)
        self._popup.hide()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self._search:
            if event.type() == QEvent.KeyPress:
                key = event.key()
                if key == Qt.Key_Down and self._popup.isVisible():
                    self._popup.setFocus()
                    self._popup.setCurrentRow(0)
                    return True
                if key == Qt.Key_Escape:
                    self._popup.hide()
                    return True
            if event.type() == QEvent.FocusOut:
                QTimer.singleShot(150, self._popup.hide)
        return super().eventFilter(obj, event)

    def _confirm(self):
        name = self._search.text().strip()
        if not name:
            return
        self._popup.hide()
        self._selected_name = name
        self.accept()

    def get_data(self) -> dict | None:
        if not self._selected_name:
            return None
        dist = self._distance.value()
        return {
            "cardio_type":   self._selected_name,
            "duration_min":  self._duration.value(),
            "distance_km":   dist if dist > 0 else None,
            "pse":           self._pse.value(),
        }


# ---------------------------------------------------------------------------
# CardioRow — widget de linha de cardio na tela de treino ativo
# ---------------------------------------------------------------------------

class CardioRow(QFrame):
    """
    Widget visual de uma entrada de cardio.
    Exibe: tipo | tempo | distância | PSE | botão remover
    """

    remove_requested = Signal(object)  # self

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._data = data
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background: {C_GREEN_BG};
                border: 1px solid {C_GREEN};
                border-radius: 10px;
            }}
        """)
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(12)

        # Ícone
        icon = QLabel("♡")
        icon.setStyleSheet(f"font-size:20px; color:{C_GREEN}; font-weight:700;")
        lay.addWidget(icon)

        # Info
        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(self._data["cardio_type"])
        name_lbl.setStyleSheet(f"color:{C_GREEN}; font-weight:700; font-size:13px;")
        info.addWidget(name_lbl)

        dist = self._data.get("distance_km")
        dist_str = f" · {dist:.1f} km" if dist else ""
        meta = QLabel(f"{int(self._data['duration_min'])} min{dist_str} · PSE {self._data['pse']}/10")
        meta.setStyleSheet(f"color:{C_TEXT3}; font-size:11px;")
        info.addWidget(meta)
        lay.addLayout(info)
        lay.addStretch()

        # Botão remover
        rm = QPushButton("✕")
        rm.setFixedSize(28, 28)
        rm.setStyleSheet(f"background:transparent; color:{C_TEXT3}; border:none; font-size:14px; font-weight:700;")
        rm.clicked.connect(lambda: self.remove_requested.emit(self))
        lay.addWidget(rm)

    def get_data(self) -> dict:
        return self._data
