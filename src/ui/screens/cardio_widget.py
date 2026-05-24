"""
ui/screens/cardio_widget.py
Widget de linha de cardio + página de seleção de tipo de cardio.
"""
from __future__ import annotations
import re
import unicodedata
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QDialog, QDoubleSpinBox, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSlider, QVBoxLayout, QWidget, QGridLayout, QScrollArea,
)
from PySide6.QtGui import QFont

from src.ui.theme import (
    C_BORDER, C_CARD, C_CARD2, C_GREEN, C_GREEN_BG, C_GREEN_ACTIVE, C_BG,
    C_TEXT, C_TEXT2, C_TEXT3, C_RED, label, separator, neon_glow,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, C_ACCENT_MUTED,
)


# ---------------------------------------------------------------------------
# Parser do tipo_cardios.md
# ---------------------------------------------------------------------------

def _norm(text: str) -> str:
    nfd = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def parse_cardio_types(md_path: str = "docs/tipo_cardios.md") -> list[dict]:
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


def estimate_calories(duration_min: float, pse: int, weight_kg: float = 75) -> int:
    """
    Estimativa simples de calorias queimadas baseada em duração, PSE e peso.
    Fórmula aproximada: MET * peso * tempo_horas
    PSE 1-3: ~3 MET, 4-6: ~6 MET, 7-8: ~9 MET, 9-10: ~12 MET
    """
    if pse <= 3:
        met = 3.0
    elif pse <= 6:
        met = 6.0
    elif pse <= 8:
        met = 9.0
    else:
        met = 12.0
    
    hours = duration_min / 60.0
    calories = met * weight_kg * hours
    return int(calories)


# ---------------------------------------------------------------------------
# CardioPage — página completa para adicionar cardio (ao invés de diálogo)
# ---------------------------------------------------------------------------

class CardioPage(QWidget):
    """Página completa para adicionar cardio, integrada ao stack da aplicação."""
    
    cardio_added = Signal(dict)  # Emite os dados do cardio quando confirmado
    cancelled = Signal()  # Emite quando o usuário cancela

    def __init__(self, user_weight_kg: float = 75, parent=None):
        super().__init__(parent)
        self._cardio_types = parse_cardio_types()
        self._user_weight = user_weight_kg
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Scroll principal
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"background: {C_BG}; border: none;")
        
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(20)

        # Header com botão voltar
        import qtawesome as qta
        hdr = QHBoxLayout()
        back_btn = QPushButton(" Voltar")
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color=C_TEXT2))
        back_btn.setObjectName("ghost")
        back_btn.setFixedWidth(100)
        back_btn.setFixedHeight(36)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C_TEXT2};
                border: 1px solid {C_BORDER};
                border-radius: {RADIUS_SM}px;
                padding: 0 12px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {C_CARD};
                color: {C_TEXT};
                border-color: {C_TEXT3};
            }}
        """)
        back_btn.clicked.connect(lambda: self.cancelled.emit())
        hdr.addWidget(back_btn)
        hdr.addStretch()
        lay.addLayout(hdr)

        # Título e descrição
        title_lay = QVBoxLayout()
        title_lay.setSpacing(8)
        title = QLabel("🏃 Adicionar Cardio")
        title.setObjectName("h1")
        title.setStyleSheet(f"color: {C_TEXT}; font-size: 32px; font-weight: 800;")
        title_lay.addWidget(title)
        
        desc = QLabel("Escolha o tipo de cardio e registre suas métricas para acompanhar seu progresso")
        desc.setStyleSheet(f"color: {C_TEXT2}; font-size: 14px;")
        title_lay.addWidget(desc)
        lay.addLayout(title_lay)
        
        lay.addWidget(separator())

        # Campo de busca com popup de lista
        search_lay = QVBoxLayout()
        search_lay.setSpacing(10)
        search_label = QLabel("🔍 BUSCAR TIPO DE CARDIO")
        search_label.setStyleSheet(f"color: {C_TEXT2}; font-size: 11px; font-weight: 700; letter-spacing: 1px;")
        search_lay.addWidget(search_label)
        
        self._search = QLineEdit()
        self._search.setPlaceholderText("Digite para buscar: Esteira, Remo, Jump...")
        self._search.setFixedHeight(48)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {C_CARD};
                color: {C_TEXT};
                border: 2px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 0 16px;
                font-size: 15px;
            }}
            QLineEdit:focus {{
                border-color: {C_GREEN};
                background: {C_CARD2};
            }}
        """)
        search_lay.addWidget(self._search)
        lay.addLayout(search_lay)

        # Popup de resultados (QListWidget flutuante)
        self._popup = QListWidget(self)
        self._popup.setWindowFlags(Qt.ToolTip)
        self._popup.setFocusPolicy(Qt.NoFocus)
        self._popup.setStyleSheet(f"""
            QListWidget {{
                background: {C_CARD};
                border: 2px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                outline: none;
                font-size: 14px;
            }}
            QListWidget::item {{
                padding: 12px 18px;
                color: {C_TEXT2};
                border-bottom: 1px solid {C_BORDER};
            }}
            QListWidget::item:hover {{ background: {C_CARD2}; color: {C_TEXT}; }}
            QListWidget::item:selected {{ background: {C_ACCENT_MUTED}; color: {C_GREEN}; }}
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

        lay.addWidget(separator())

        # Card de métricas com visual melhorado
        metrics = QFrame()
        metrics.setObjectName("card")
        metrics.setStyleSheet(f"""
            QFrame#card {{
                background: {C_CARD};
                border: 1px solid {C_BORDER};
                border-radius: {RADIUS_LG}px;
            }}
        """)
        m_lay = QVBoxLayout(metrics)
        m_lay.setContentsMargins(24, 24, 24, 24)
        m_lay.setSpacing(20)

        metrics_title = QLabel("📊 Métricas do Treino")
        metrics_title.setStyleSheet(f"color: {C_TEXT}; font-size: 16px; font-weight: 700;")
        m_lay.addWidget(metrics_title)

        # Tempo (obrigatório)
        time_frame = QFrame()
        time_frame.setStyleSheet("background: transparent; border: none;")
        time_lay = QVBoxLayout(time_frame)
        time_lay.setContentsMargins(0, 0, 0, 0)
        time_lay.setSpacing(10)
        
        time_label = QLabel("⏱️ Duração *")
        time_label.setStyleSheet(f"color: {C_TEXT2}; font-size: 14px; font-weight: 600;")
        time_lay.addWidget(time_label)
        
        self._duration = QDoubleSpinBox()
        self._duration.setRange(1, 300)
        self._duration.setValue(30)
        self._duration.setSuffix(" min")
        self._duration.setDecimals(0)
        self._duration.setFixedHeight(48)
        self._duration.setStyleSheet(f"""
            QDoubleSpinBox {{
                background: {C_CARD2};
                color: {C_TEXT};
                border: 1px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 0 16px;
                font-size: 16px;
                font-weight: 600;
            }}
            QDoubleSpinBox:focus {{
                border-color: {C_GREEN};
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 24px;
                border: none;
                background: transparent;
                border-radius: 4px;
            }}
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
                background: {C_ACCENT_MUTED};
            }}
            QDoubleSpinBox::up-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 7px solid {C_TEXT2};
                width: 0;
                height: 0;
            }}
            QDoubleSpinBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 7px solid {C_TEXT2};
                width: 0;
                height: 0;
            }}
        """)
        self._duration.valueChanged.connect(self._update_calories)
        time_lay.addWidget(self._duration)
        m_lay.addWidget(time_frame)

        # Distância (opcional)
        dist_frame = QFrame()
        dist_frame.setStyleSheet("background: transparent; border: none;")
        dist_lay = QVBoxLayout(dist_frame)
        dist_lay.setContentsMargins(0, 0, 0, 0)
        dist_lay.setSpacing(10)
        
        dist_label = QLabel("📏 Distância (opcional)")
        dist_label.setStyleSheet(f"color: {C_TEXT2}; font-size: 14px; font-weight: 600;")
        dist_lay.addWidget(dist_label)
        
        self._distance = QDoubleSpinBox()
        self._distance.setRange(0, 200)
        self._distance.setValue(0)
        self._distance.setSuffix(" km")
        self._distance.setDecimals(1)
        self._distance.setFixedHeight(48)
        self._distance.setSpecialValueText("Não informado")
        self._distance.setStyleSheet(f"""
            QDoubleSpinBox {{
                background: {C_CARD2};
                color: {C_TEXT2};
                border: 1px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 0 16px;
                font-size: 16px;
                font-weight: 600;
            }}
            QDoubleSpinBox:focus {{
                border-color: {C_GREEN};
                color: {C_TEXT};
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 24px;
                border: none;
                background: transparent;
                border-radius: 4px;
            }}
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
                background: {C_ACCENT_MUTED};
            }}
            QDoubleSpinBox::up-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 7px solid {C_TEXT2};
                width: 0;
                height: 0;
            }}
            QDoubleSpinBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 7px solid {C_TEXT2};
                width: 0;
                height: 0;
            }}
        """)
        dist_lay.addWidget(self._distance)
        m_lay.addWidget(dist_frame)

        # PSE (Escala de Borg 1-10) com visual melhorado
        pse_frame = QFrame()
        pse_frame.setStyleSheet("background: transparent; border: none;")
        pse_lay = QVBoxLayout(pse_frame)
        pse_lay.setContentsMargins(0, 0, 0, 0)
        pse_lay.setSpacing(10)
        
        pse_header = QHBoxLayout()
        pse_label = QLabel("💪 Intensidade (PSE)")
        pse_label.setStyleSheet(f"color: {C_TEXT2}; font-size: 14px; font-weight: 600;")
        pse_header.addWidget(pse_label)
        pse_header.addStretch()
        
        self._pse_lbl = QLabel("5")
        self._pse_lbl.setStyleSheet(f"""
            color: {C_GREEN}; 
            font-size: 28px; 
            font-weight: 800; 
            min-width: 45px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {C_GREEN_BG}, stop:1 #1a2e0a);
            border: 2px solid {C_GREEN};
            border-radius: {RADIUS_MD}px;
            padding: 4px 14px;
        """)
        self._pse_lbl.setAlignment(Qt.AlignCenter)
        neon_glow(self._pse_lbl, C_GREEN, blur=15, opacity=100)
        pse_header.addWidget(self._pse_lbl)
        pse_lay.addLayout(pse_header)
        
        self._pse = QSlider(Qt.Horizontal)
        self._pse.setRange(1, 10)
        self._pse.setValue(5)
        self._pse.setFixedHeight(36)
        self._pse.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 8px;
                background: {C_CARD2};
                border-radius: 4px;
                border: 1px solid {C_BORDER};
            }}
            QSlider::handle:horizontal {{
                background: {C_GREEN};
                width: 24px; 
                height: 24px;
                margin: -8px 0;
                border-radius: 12px;
                border: 2px solid {C_BG};
            }}
            QSlider::handle:horizontal:hover {{
                background: {C_GREEN_ACTIVE};
                width: 28px;
                height: 28px;
                margin: -10px 0;
                border-radius: 14px;
            }}
            QSlider::sub-page:horizontal {{
                background: {C_GREEN};
                border-radius: 4px;
            }}
        """)
        self._pse.valueChanged.connect(self._on_pse_changed)
        pse_lay.addWidget(self._pse)
        
        # Labels de referência com ícones
        ref_row = QHBoxLayout()
        ref_row.setSpacing(0)
        refs = [
            ("😌", "Leve", C_TEXT3),
            ("😊", "Moderado", C_TEXT3),
            ("😤", "Intenso", C_TEXT2),
            ("🔥", "Máximo", C_GREEN),
        ]
        for emoji, txt, color in refs:
            l = QLabel(f"{emoji} {txt}")
            l.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
            l.setAlignment(Qt.AlignCenter)
            ref_row.addWidget(l)
        pse_lay.addLayout(ref_row)
        m_lay.addWidget(pse_frame)

        # Estimativa de calorias
        cal_frame = QFrame()
        cal_frame.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {C_GREEN_BG}, stop:1 #1a2e0a);
            border: 2px solid {C_GREEN};
            border-radius: {RADIUS_MD}px;
        """)
        cal_lay = QHBoxLayout(cal_frame)
        cal_lay.setContentsMargins(16, 16, 16, 16)
        cal_lay.setSpacing(12)
        
        cal_icon = QLabel("🔥")
        cal_icon.setStyleSheet("font-size: 32px;")
        cal_lay.addWidget(cal_icon)
        
        cal_text_lay = QVBoxLayout()
        cal_text_lay.setSpacing(2)
        cal_title = QLabel("Calorias Estimadas")
        cal_title.setStyleSheet(f"color: {C_TEXT2}; font-size: 12px; font-weight: 600;")
        cal_text_lay.addWidget(cal_title)
        
        self._calories_lbl = QLabel("~150 kcal")
        self._calories_lbl.setStyleSheet(f"color: {C_GREEN}; font-size: 26px; font-weight: 800;")
        cal_text_lay.addWidget(self._calories_lbl)
        cal_lay.addLayout(cal_text_lay)
        cal_lay.addStretch()
        
        m_lay.addWidget(cal_frame)
        lay.addWidget(metrics)

        lay.addStretch()
        
        scroll.setWidget(content)
        root.addWidget(scroll)

        # Botões fixos no rodapé
        footer = QWidget()
        footer.setStyleSheet(f"background: {C_CARD}; border-top: 2px solid {C_BORDER};")
        footer_lay = QHBoxLayout(footer)
        footer_lay.setContentsMargins(24, 16, 24, 16)
        footer_lay.setSpacing(12)
        
        cancel = QPushButton("✕ Cancelar")
        cancel.setFixedHeight(52)
        cancel.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C_TEXT2};
                border: 1px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 0 24px;
                font-weight: 600;
                font-size: 15px;
            }}
            QPushButton:hover {{
                background: {C_CARD2};
                color: {C_TEXT};
                border-color: {C_TEXT3};
            }}
        """)
        cancel.clicked.connect(lambda: self.cancelled.emit())
        
        confirm = QPushButton("✓ Adicionar Cardio")
        confirm.setFixedHeight(52)
        confirm.setStyleSheet(f"""
            QPushButton {{
                background: {C_GREEN};
                color: #000;
                border: none;
                border-radius: {RADIUS_MD}px;
                padding: 0 28px;
                font-weight: 800;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background: {C_GREEN_ACTIVE};
            }}
        """)
        neon_glow(confirm, C_GREEN, blur=25, opacity=150)
        confirm.clicked.connect(self._confirm)
        
        footer_lay.addWidget(cancel)
        footer_lay.addWidget(confirm, 1)
        root.addWidget(footer)
        
        # Inicializar calorias
        self._update_calories()

    def _set_cardio_type(self, name: str):
        """Define o tipo de cardio via botão rápido."""
        self._search.setText(name)
        self._popup.hide()

    def _on_pse_changed(self, value: int):
        """Atualiza o label do PSE e as calorias."""
        self._pse_lbl.setText(str(value))
        self._update_calories()

    def _update_calories(self):
        """Atualiza a estimativa de calorias em tempo real."""
        duration = self._duration.value()
        pse = self._pse.value()
        calories = estimate_calories(duration, pse, self._user_weight)
        self._calories_lbl.setText(f"~{calories} kcal")

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
        row_h = self._popup.sizeHintForRow(0) if self._popup.count() > 0 else 40
        self._popup.setFixedHeight(min(300, row_h * min(self._popup.count(), 8) + 8))
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
        
        dist = self._distance.value()
        duration = self._duration.value()
        pse = self._pse.value()
        calories = estimate_calories(duration, pse, self._user_weight)
        
        data = {
            "cardio_type":   name,
            "duration_min":  duration,
            "distance_km":   dist if dist > 0 else None,
            "pse":           pse,
            "calories":      calories,
        }
        
        self.cardio_added.emit(data)


# ---------------------------------------------------------------------------
# CardioPickerDialog — mantido para compatibilidade
# ---------------------------------------------------------------------------

class CardioPickerDialog(QDialog):
    """Diálogo com autocomplete para selecionar o tipo de cardio."""

    def __init__(self, parent=None, user_weight_kg: float = 75):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self._selected_name: str = ""
        self._cardio_types = parse_cardio_types()
        self._user_weight = user_weight_kg
        self.setMinimumWidth(520)
        self._build()

    def _build(self):
        from src.ui.titlebar import build_dialog_titlebar

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(build_dialog_titlebar(self, "ADICIONAR CARDIO"))

        content = QWidget()
        content.setStyleSheet(
            "background: #242424;"
            f"border-bottom-left-radius: {RADIUS_LG}px;"
            f"border-bottom-right-radius: {RADIUS_LG}px;"
        )
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 20, 24, 24)
        lay.setSpacing(16)
        root.addWidget(content)

        self.setStyleSheet(f"QDialog {{ border: 1px solid {C_BORDER}; border-radius: {RADIUS_LG}px; }}")

        # Título e descrição
        title_lay = QVBoxLayout()
        title_lay.setSpacing(6)
        title = QLabel("🏃 Registre sua atividade cardiovascular")
        title.setObjectName("h3")
        title.setStyleSheet(f"color: {C_GREEN}; font-size: 20px; font-weight: 800;")
        title_lay.addWidget(title)
        
        desc = QLabel("Escolha o tipo de cardio e registre suas métricas para acompanhar seu progresso")
        desc.setStyleSheet(f"color: {C_TEXT3}; font-size: 13px;")
        title_lay.addWidget(desc)
        lay.addLayout(title_lay)
        
        lay.addWidget(separator())

        # Campo de busca com popup de lista
        search_lay = QVBoxLayout()
        search_lay.setSpacing(8)
        search_label = QLabel("🔍 Buscar tipo de cardio")
        search_label.setStyleSheet(f"color: {C_TEXT2}; font-size: 12px; font-weight: 600; text-transform: uppercase;")
        search_lay.addWidget(search_label)
        
        self._search = QLineEdit()
        self._search.setPlaceholderText("Digite para buscar: Esteira, Remo, Jump...")
        self._search.setFixedHeight(44)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {C_CARD};
                color: {C_TEXT};
                border: 2px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 0 16px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border-color: {C_GREEN};
                background: {C_CARD2};
            }}
        """)
        search_lay.addWidget(self._search)
        lay.addLayout(search_lay)

        # Popup de resultados (QListWidget flutuante)
        self._popup = QListWidget(self)
        self._popup.setWindowFlags(Qt.ToolTip)
        self._popup.setFocusPolicy(Qt.NoFocus)
        self._popup.setStyleSheet(f"""
            QListWidget {{
                background: {C_CARD};
                border: 2px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                outline: none;
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 10px 16px;
                color: {C_TEXT2};
                border-bottom: 1px solid {C_BORDER};
            }}
            QListWidget::item:hover {{ background: {C_CARD2}; color: {C_TEXT}; }}
            QListWidget::item:selected {{ background: {C_ACCENT_MUTED}; color: {C_GREEN}; }}
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

        lay.addWidget(separator())

        # Card de métricas com visual melhorado
        metrics = QFrame()
        metrics.setObjectName("card")
        metrics.setStyleSheet(f"""
            QFrame#card {{
                background: {C_CARD};
                border: 2px solid {C_BORDER};
                border-radius: {RADIUS_LG}px;
            }}
        """)
        m_lay = QVBoxLayout(metrics)
        m_lay.setContentsMargins(20, 20, 20, 20)
        m_lay.setSpacing(18)

        metrics_title = QLabel("📊 Métricas do Treino")
        metrics_title.setStyleSheet(f"color: {C_TEXT}; font-size: 15px; font-weight: 700;")
        m_lay.addWidget(metrics_title)

        # Tempo (obrigatório)
        time_frame = QFrame()
        time_frame.setStyleSheet("background: transparent; border: none;")
        time_lay = QVBoxLayout(time_frame)
        time_lay.setContentsMargins(0, 0, 0, 0)
        time_lay.setSpacing(8)
        
        time_label = QLabel("⏱️ Duração *")
        time_label.setStyleSheet(f"color: {C_TEXT2}; font-size: 13px; font-weight: 600;")
        time_lay.addWidget(time_label)
        
        self._duration = QDoubleSpinBox()
        self._duration.setRange(1, 300)
        self._duration.setValue(30)
        self._duration.setSuffix(" min")
        self._duration.setDecimals(0)
        self._duration.setFixedHeight(44)
        self._duration.setStyleSheet(f"""
            QDoubleSpinBox {{
                background: {C_CARD2};
                color: {C_TEXT};
                border: 2px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 0 16px;
                font-size: 14px;
                font-weight: 600;
            }}
            QDoubleSpinBox:focus {{
                border-color: {C_GREEN};
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 20px;
                border: none;
                background: {C_CARD};
            }}
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
                background: {C_ACCENT_MUTED};
            }}
            QDoubleSpinBox::up-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 6px solid {C_TEXT2};
                width: 0;
                height: 0;
            }}
            QDoubleSpinBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {C_TEXT2};
                width: 0;
                height: 0;
            }}
        """)
        self._duration.valueChanged.connect(self._update_calories)
        time_lay.addWidget(self._duration)
        m_lay.addWidget(time_frame)

        # Distância (opcional)
        dist_frame = QFrame()
        dist_frame.setStyleSheet("background: transparent; border: none;")
        dist_lay = QVBoxLayout(dist_frame)
        dist_lay.setContentsMargins(0, 0, 0, 0)
        dist_lay.setSpacing(8)
        
        dist_label = QLabel("📏 Distância (opcional)")
        dist_label.setStyleSheet(f"color: {C_TEXT2}; font-size: 13px; font-weight: 600;")
        dist_lay.addWidget(dist_label)
        
        self._distance = QDoubleSpinBox()
        self._distance.setRange(0, 200)
        self._distance.setValue(0)
        self._distance.setSuffix(" km")
        self._distance.setDecimals(1)
        self._distance.setFixedHeight(44)
        self._distance.setSpecialValueText("Não informado")
        self._distance.setStyleSheet(f"""
            QDoubleSpinBox {{
                background: {C_CARD2};
                color: {C_TEXT};
                border: 2px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 0 16px;
                font-size: 14px;
                font-weight: 600;
            }}
            QDoubleSpinBox:focus {{
                border-color: {C_GREEN};
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 20px;
                border: none;
                background: {C_CARD};
            }}
            QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
                background: {C_ACCENT_MUTED};
            }}
            QDoubleSpinBox::up-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-bottom: 6px solid {C_TEXT2};
                width: 0;
                height: 0;
            }}
            QDoubleSpinBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {C_TEXT2};
                width: 0;
                height: 0;
            }}
        """)
        dist_lay.addWidget(self._distance)
        m_lay.addWidget(dist_frame)

        # PSE (Escala de Borg 1-10) com visual melhorado
        pse_frame = QFrame()
        pse_frame.setStyleSheet("background: transparent; border: none;")
        pse_lay = QVBoxLayout(pse_frame)
        pse_lay.setContentsMargins(0, 0, 0, 0)
        pse_lay.setSpacing(8)
        
        pse_header = QHBoxLayout()
        pse_label = QLabel("💪 Intensidade (PSE)")
        pse_label.setStyleSheet(f"color: {C_TEXT2}; font-size: 13px; font-weight: 600;")
        pse_header.addWidget(pse_label)
        pse_header.addStretch()
        
        self._pse_lbl = QLabel("5")
        self._pse_lbl.setStyleSheet(f"""
            color: {C_GREEN}; 
            font-size: 28px; 
            font-weight: 800; 
            min-width: 40px;
            background: {C_GREEN_BG};
            border-radius: {RADIUS_SM}px;
            padding: 4px 12px;
        """)
        self._pse_lbl.setAlignment(Qt.AlignCenter)
        neon_glow(self._pse_lbl, C_GREEN, blur=20, opacity=120)
        pse_header.addWidget(self._pse_lbl)
        pse_lay.addLayout(pse_header)
        
        self._pse = QSlider(Qt.Horizontal)
        self._pse.setRange(1, 10)
        self._pse.setValue(5)
        self._pse.setFixedHeight(32)
        self._pse.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 8px;
                background: {C_CARD2};
                border-radius: 4px;
                border: 1px solid {C_BORDER};
            }}
            QSlider::handle:horizontal {{
                background: {C_GREEN};
                width: 24px; 
                height: 24px;
                margin: -8px 0;
                border-radius: 12px;
                border: 3px solid #000;
            }}
            QSlider::handle:horizontal:hover {{
                background: {C_GREEN_ACTIVE};
                width: 28px;
                height: 28px;
                margin: -10px 0;
                border-radius: 14px;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C_GREEN}, stop:1 {C_GREEN_ACTIVE});
                border-radius: 4px;
            }}
        """)
        self._pse.valueChanged.connect(self._on_pse_changed)
        pse_lay.addWidget(self._pse)
        
        # Labels de referência com ícones
        ref_row = QHBoxLayout()
        ref_row.setSpacing(0)
        refs = [
            ("😌", "Leve", C_TEXT3),
            ("😊", "Moderado", C_TEXT3),
            ("😤", "Intenso", C_TEXT2),
            ("🔥", "Máximo", C_GREEN),
        ]
        for emoji, txt, color in refs:
            l = QLabel(f"{emoji} {txt}")
            l.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 600;")
            l.setAlignment(Qt.AlignCenter)
            ref_row.addWidget(l)
        pse_lay.addLayout(ref_row)
        m_lay.addWidget(pse_frame)

        # Estimativa de calorias
        cal_frame = QFrame()
        cal_frame.setStyleSheet(f"""
            background: {C_GREEN_BG};
            border: 1px solid {C_GREEN};
            border-radius: {RADIUS_MD}px;
        """)
        cal_lay = QHBoxLayout(cal_frame)
        cal_lay.setContentsMargins(12, 12, 12, 12)
        cal_lay.setSpacing(10)
        
        cal_icon = QLabel("🔥")
        cal_icon.setStyleSheet("font-size: 24px;")
        cal_lay.addWidget(cal_icon)
        
        cal_text_lay = QVBoxLayout()
        cal_text_lay.setSpacing(2)
        cal_title = QLabel("Calorias Estimadas")
        cal_title.setStyleSheet(f"color: {C_TEXT3}; font-size: 11px; font-weight: 600;")
        cal_text_lay.addWidget(cal_title)
        
        self._calories_lbl = QLabel("~150 kcal")
        self._calories_lbl.setStyleSheet(f"color: {C_GREEN}; font-size: 20px; font-weight: 800;")
        cal_text_lay.addWidget(self._calories_lbl)
        cal_lay.addLayout(cal_text_lay)
        cal_lay.addStretch()
        
        m_lay.addWidget(cal_frame)
        lay.addWidget(metrics)

        # Botões com visual melhorado
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        
        cancel = QPushButton("✕ Cancelar")
        cancel.setObjectName("ghost")
        cancel.setFixedHeight(48)
        cancel.clicked.connect(self.reject)
        
        confirm = QPushButton("✓ Adicionar Cardio")
        confirm.setFixedHeight(48)
        confirm.setStyleSheet(f"""
            QPushButton {{
                background: {C_GREEN};
                color: #000;
                border: none;
                border-radius: {RADIUS_MD}px;
                padding: 0 24px;
                font-weight: 800;
                font-size: 15px;
            }}
            QPushButton:hover {{
                background: {C_GREEN_ACTIVE};
            }}
        """)
        neon_glow(confirm, C_GREEN, blur=25, opacity=150)
        confirm.clicked.connect(self._confirm)
        
        btn_row.addWidget(cancel)
        btn_row.addWidget(confirm, 1)
        lay.addLayout(btn_row)
        
        # Inicializar calorias
        self._update_calories()

    def _set_cardio_type(self, name: str):
        """Define o tipo de cardio via botão rápido."""
        self._search.setText(name)
        self._popup.hide()

    def _on_pse_changed(self, value: int):
        """Atualiza o label do PSE e as calorias."""
        self._pse_lbl.setText(str(value))
        self._update_calories()

    def _update_calories(self):
        """Atualiza a estimativa de calorias em tempo real."""
        duration = self._duration.value()
        pse = self._pse.value()
        calories = estimate_calories(duration, pse, self._user_weight)
        self._calories_lbl.setText(f"~{calories} kcal")

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
    Exibe: tipo | tempo | distância | PSE | calorias | botão remover
    """

    remove_requested = Signal(object)  # self

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self._data = data
        self.setObjectName("card")
        self.setStyleSheet(f"""
            QFrame#card {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {C_GREEN_BG}, stop:1 #1a2e0a);
                border: 2px solid {C_GREEN};
                border-radius: {RADIUS_LG}px;
            }}
            QFrame#card:hover {{
                border-color: {C_GREEN_ACTIVE};
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1f3a0f, stop:1 #1a2e0a);
            }}
        """)
        neon_glow(self, C_GREEN, blur=15, opacity=100)
        self._build()

    def _build(self):
        lay = QHBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(16)

        # Ícone maior e mais visual
        icon = QLabel("🏃")
        icon.setStyleSheet(f"font-size: 32px;")
        icon.setFixedSize(40, 40)
        icon.setAlignment(Qt.AlignCenter)
        lay.addWidget(icon)

        # Info principal
        info = QVBoxLayout()
        info.setSpacing(4)
        
        name_lbl = QLabel(self._data["cardio_type"])
        name_lbl.setStyleSheet(f"color: {C_GREEN}; font-weight: 800; font-size: 16px;")
        info.addWidget(name_lbl)

        # Métricas em linha
        metrics_lay = QHBoxLayout()
        metrics_lay.setSpacing(12)
        
        # Duração
        duration_lbl = QLabel(f"⏱️ {int(self._data['duration_min'])} min")
        duration_lbl.setStyleSheet(f"color: {C_TEXT2}; font-size: 12px; font-weight: 600;")
        metrics_lay.addWidget(duration_lbl)
        
        # Distância (se houver)
        dist = self._data.get("distance_km")
        if dist:
            dist_lbl = QLabel(f"📏 {dist:.1f} km")
            dist_lbl.setStyleSheet(f"color: {C_TEXT2}; font-size: 12px; font-weight: 600;")
            metrics_lay.addWidget(dist_lbl)
        
        # PSE
        pse_lbl = QLabel(f"💪 PSE {self._data['pse']}/10")
        pse_lbl.setStyleSheet(f"color: {C_TEXT2}; font-size: 12px; font-weight: 600;")
        metrics_lay.addWidget(pse_lbl)
        
        metrics_lay.addStretch()
        info.addLayout(metrics_lay)
        lay.addLayout(info)
        
        lay.addStretch()

        # Calorias estimadas (se disponível)
        if "calories" in self._data:
            cal_frame = QFrame()
            cal_frame.setStyleSheet(f"""
                background: {C_GREEN};
                border-radius: {RADIUS_SM}px;
                padding: 8px 12px;
            """)
            cal_lay = QVBoxLayout(cal_frame)
            cal_lay.setContentsMargins(8, 6, 8, 6)
            cal_lay.setSpacing(0)
            
            cal_val = QLabel(f"{self._data['calories']}")
            cal_val.setStyleSheet("color: #000; font-size: 18px; font-weight: 800;")
            cal_val.setAlignment(Qt.AlignCenter)
            cal_lay.addWidget(cal_val)
            
            cal_unit = QLabel("kcal")
            cal_unit.setStyleSheet("color: #000; font-size: 10px; font-weight: 600;")
            cal_unit.setAlignment(Qt.AlignCenter)
            cal_lay.addWidget(cal_unit)
            
            lay.addWidget(cal_frame)

        # Botão remover melhorado
        rm = QPushButton("✕")
        rm.setFixedSize(36, 36)
        rm.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C_TEXT3};
                border: 2px solid {C_BORDER};
                border-radius: 18px;
                font-size: 16px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {C_RED};
                color: #fff;
                border-color: {C_RED};
            }}
        """)
        rm.clicked.connect(lambda: self.remove_requested.emit(self))
        lay.addWidget(rm)

    def get_data(self) -> dict:
        return self._data
