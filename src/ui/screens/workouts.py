"""
ui/screens/workouts.py
Tela de Treinos: barra de pesquisa, lista de rotinas, botão + Cardio avulso.
"""
from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QScrollArea,
    QSlider, QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)

from database import DatabaseConnection
from engine import NormalizationEngine, Routine, RoutineManager
from src.ui.dialogs import ExerciseLineEdit
from src.ui.theme import (
    C_BORDER, C_CARD, C_CARD2, C_GREEN, C_GREEN_BG,
    C_TEXT, C_TEXT2, C_TEXT3, C_BG, label, separator,
    RADIUS_MD, RADIUS_SM,
)
from src.ui.widgets import RoutineCard
from src.ui.smooth_scroll import apply_smooth_scroll


class WorkoutsTab(QWidget):
    start_workout  = Signal(object, int)   # (Routine, session_id)
    add_cardio_req = Signal()              # abre diálogo de cardio avulso

    def __init__(self, db: DatabaseConnection, rm: RoutineManager,
                 norm: NormalizationEngine, parent=None):
        super().__init__(parent)
        self._db       = db
        self._rm       = rm
        self._norm     = norm
        self._all_cards: list[tuple[Routine, RoutineCard]] = []
        self._build()

    def _build(self):
        # Layout raiz sem margens
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        # ── Página 0: lista de treinos ────────────────────────────────────
        list_page = QWidget()
        page_layout = QVBoxLayout(list_page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)
        
        # Container para header e search (fora do scroll)
        header_container = QWidget()
        header_container.setStyleSheet(f"background:{C_BG};")
        header_lay = QVBoxLayout(header_container)
        header_lay.setContentsMargins(24, 24, 24, 16)
        header_lay.setSpacing(16)

        hdr = QHBoxLayout()
        left = QVBoxLayout()
        left.setSpacing(2)
        h = QLabel("SEUS <span style='color:#a3e635'>TREINOS</span>")
        h.setTextFormat(Qt.RichText)
        h.setStyleSheet("font-size:26px; font-weight:800; color:#fff;")
        left.addWidget(h)
        hdr.addLayout(left)
        hdr.addStretch()

        cardio_btn = QPushButton(" Cardio")
        cardio_btn.setIcon(qta.icon("fa5s.heart", color=C_GREEN))
        cardio_btn.setFixedHeight(38)
        cardio_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C_GREEN};
                border: 1px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                padding: 0 16px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: rgba(162, 255, 0, 0.12); }}
            QPushButton:pressed {{ background: {C_GREEN}; color: #000; }}
        """)
        cardio_btn.clicked.connect(self._open_cardio)
        hdr.addWidget(cardio_btn)

        new_btn = QPushButton(" Novo Treino")
        new_btn.setIcon(qta.icon("fa5s.plus", color=C_GREEN))
        new_btn.setFixedHeight(38)
        new_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C_GREEN};
                border: 1px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                padding: 0 16px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: rgba(162, 255, 0, 0.12); }}
            QPushButton:pressed {{ background: {C_GREEN}; color: #000; }}
        """)
        new_btn.clicked.connect(self._show_create_form)
        hdr.addWidget(new_btn)
        header_lay.addLayout(hdr)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Pesquisar treino...")
        self._search.setFixedHeight(40)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {C_CARD};
                color: {C_TEXT};
                border: 1px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 0 14px 0 36px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border-color: {C_GREEN};
            }}
        """)
        self._search.textChanged.connect(self._filter_routines)
        header_lay.addWidget(self._search)
        
        page_layout.addWidget(header_container)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background:{C_BG}; border:none; }}")
        # Aplica rolagem suave otimizada
        apply_smooth_scroll(scroll)
        self._list_w = QWidget()
        self._list_w.setStyleSheet(f"background:{C_BG};")
        self._list_lay = QVBoxLayout(self._list_w)
        self._list_lay.setContentsMargins(24, 8, 24, 24)
        self._list_lay.setSpacing(10)
        self._list_lay.addStretch()
        scroll.setWidget(self._list_w)
        page_layout.addWidget(scroll)

        self._stack.addWidget(list_page)  # index 0

        # ── Página 1: formulário de criação ───────────────────────────────
        self._stack.addWidget(self._build_create_page())  # index 1
        self._stack.addWidget(self._build_cardio_page())   # index 2

        # ── Página 3: editar rotina (inline) ─────────────────────────────
        from src.ui.screens.edit_routine_dialog import EditRoutineWidget
        self._edit_widget = EditRoutineWidget(self._rm, self._norm)
        self._edit_widget.saved.connect(self._on_edit_saved)
        self._edit_widget.cancelled.connect(lambda: self._stack.setCurrentIndex(0))
        self._stack.addWidget(self._edit_widget)  # index 3

        # ── Página 4: confirmação de treino criado ────────────────────────
        self._stack.addWidget(self._build_success_page())  # index 4

        self.reload()

    # ------------------------------------------------------------------
    # Página de sucesso (treino criado)
    # ------------------------------------------------------------------

    def _build_success_page(self) -> QWidget:
        """Página de confirmação após criar um treino - Visual Premium."""
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve
        
        page = QWidget()
        page.setStyleSheet(f"background:{C_BG};")
        
        # Layout principal com stretches laterais para centralizar
        main_layout = QHBoxLayout(page)
        main_layout.setContentsMargins(40, 60, 40, 40)
        main_layout.setSpacing(0)
        
        # Stretch esquerdo
        main_layout.addStretch(1)
        
        # Container principal com largura máxima de 600px
        self._success_container = QWidget()
        self._success_container.setMaximumWidth(600)
        self._success_container.setStyleSheet("QWidget { background: transparent; }")
        
        container_layout = QVBoxLayout(self._success_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(24)
        container_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        # Card Premium com fundo escuro e borda neon
        success_card = QFrame()
        success_card.setObjectName("success_card")
        success_card.setStyleSheet("""
            QFrame#success_card {
                background: #1a1a1a;
                border: 1px solid #b5ff00;
                border-radius: 20px;
                padding: 48px 40px;
            }
        """)
        card_layout = QVBoxLayout(success_card)
        card_layout.setSpacing(24)
        card_layout.setAlignment(Qt.AlignCenter)

        # Ícone de sucesso com efeito glow
        icon_label = QLabel("✓")
        icon_label.setStyleSheet(f"""
            font-size: 120px;
            color: {C_GREEN};
            font-weight: bold;
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        
        # Adiciona efeito de brilho (glow) verde
        glow_effect = QGraphicsDropShadowEffect()
        glow_effect.setBlurRadius(40)
        glow_effect.setColor(QColor(181, 255, 0, 200))
        glow_effect.setOffset(0, 0)
        icon_label.setGraphicsEffect(glow_effect)
        
        card_layout.addWidget(icon_label)

        # Título "Treino Criado!"
        self._success_title = QLabel()
        self._success_title.setStyleSheet("""
            font-size: 32px;
            font-weight: 800;
            color: #fff;
            margin-top: 8px;
        """)
        self._success_title.setAlignment(Qt.AlignCenter)
        self._success_title.setWordWrap(True)
        card_layout.addWidget(self._success_title)

        # Nome do treino (destaque maior e negrito)
        self._success_workout_name = QLabel()
        self._success_workout_name.setStyleSheet(f"""
            font-size: 28px;
            font-weight: 700;
            color: {C_GREEN};
            margin: 8px 0;
        """)
        self._success_workout_name.setAlignment(Qt.AlignCenter)
        self._success_workout_name.setWordWrap(True)
        card_layout.addWidget(self._success_workout_name)

        # Container horizontal para badges de estatísticas
        badges_container = QWidget()
        badges_container.setStyleSheet("background: transparent;")
        badges_layout = QHBoxLayout(badges_container)
        badges_layout.setContentsMargins(0, 16, 0, 0)
        badges_layout.setSpacing(15)
        badges_layout.setAlignment(Qt.AlignCenter)

        # Badge 1: Exercícios (usando iniciais ao invés de emoji)
        self._badge_exercises = self._create_stat_badge("EX", "0", "exercícios", is_text_icon=True)
        badges_layout.addWidget(self._badge_exercises)

        # Badge 2: Séries (usando iniciais ao invés de emoji)
        self._badge_series = self._create_stat_badge("SR", "0", "séries", is_text_icon=True)
        badges_layout.addWidget(self._badge_series)

        # Badge 3: Dias (usando iniciais ao invés de emoji)
        self._badge_days = self._create_stat_badge("DI", "", "", is_text_icon=True)
        badges_layout.addWidget(self._badge_days)

        card_layout.addWidget(badges_container)

        container_layout.addWidget(success_card)

        # Container de botões horizontais (mesma largura do card)
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setSpacing(16)
        buttons_layout.setContentsMargins(0, 0, 0, 0)

        # Botão "Voltar" - discreto com bordas
        back_btn = QPushButton("← Voltar")
        back_btn.setMinimumHeight(56)
        back_btn.setMaximumWidth(180)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C_TEXT};
                border: 1px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                font-size: 15px;
                font-weight: 600;
                padding: 0 32px;
            }}
            QPushButton:hover {{
                border-color: {C_TEXT};
                color: #fff;
            }}
            QPushButton:pressed {{
                background: rgba(255, 255, 255, 0.05);
            }}
        """)
        back_btn.clicked.connect(lambda: (self._stack.setCurrentIndex(0), self.reload()))
        buttons_layout.addWidget(back_btn)

        # Botão "Iniciar Treino" - destaque verde neon
        self._start_workout_btn = QPushButton("▶ Iniciar Treino")
        self._start_workout_btn.setMinimumHeight(56)
        self._start_workout_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_GREEN};
                color: #000;
                border: none;
                border-radius: {RADIUS_MD}px;
                font-size: 16px;
                font-weight: 700;
                padding: 0 32px;
            }}
            QPushButton:hover {{
                background: #b5ff00;
            }}
            QPushButton:pressed {{
                background: #8ad900;
            }}
        """)
        self._start_workout_btn.clicked.connect(self._start_created_workout)
        buttons_layout.addWidget(self._start_workout_btn)

        container_layout.addWidget(buttons_container)
        
        # Adiciona o container centralizado ao layout principal
        main_layout.addWidget(self._success_container)
        
        # Stretch direito
        main_layout.addStretch(1)
        
        return page
    
    def _create_stat_badge(self, icon_text: str, value: str, label: str, is_text_icon: bool = False) -> QFrame:
        """Cria um badge individual para estatísticas com design de pílula."""
        
        badge = QFrame()
        badge.setObjectName("stat_badge")
        badge.setStyleSheet("""
            QFrame#stat_badge {
                background-color: #1e1e1e;
                border-radius: 12px;
                padding: 12px;
                min-width: 110px;
            }
        """)
        
        badge_layout = QVBoxLayout(badge)
        badge_layout.setContentsMargins(12, 10, 12, 10)
        badge_layout.setSpacing(6)
        badge_layout.setAlignment(Qt.AlignCenter)
        
        # Ícone - usando texto estilizado ao invés de emoji
        if is_text_icon:
            icon_label = QLabel(icon_text)
            icon_label.setStyleSheet(f"""
                font-size: 16px;
                font-weight: 800;
                color: {C_GREEN};
                background: transparent;
                letter-spacing: 1px;
            """)
        else:
            # Fallback para emoji (caso necessário no futuro)
            import platform
            system = platform.system()
            if system == "Windows":
                emoji_font = "Segoe UI Emoji"
            elif system == "Darwin":  # macOS
                emoji_font = "Apple Color Emoji"
            else:  # Linux
                emoji_font = "Noto Color Emoji"
            
            icon_label = QLabel(icon_text)
            icon_label.setStyleSheet(f"""
                font-size: 20px;
                font-family: '{emoji_font}';
                background: transparent;
            """)
        
        icon_label.setAlignment(Qt.AlignCenter)
        badge_layout.addWidget(icon_label)
        
        # Valor (número em verde neon e negrito) - AUMENTADO
        value_label = QLabel(value)
        value_label.setObjectName("badge_value")
        value_label.setStyleSheet(f"""
            QLabel#badge_value {{
                font-size: 20px;
                font-weight: 700;
                color: {C_GREEN};
                background: transparent;
            }}
        """)
        value_label.setAlignment(Qt.AlignCenter)
        badge_layout.addWidget(value_label)
        
        # Label (texto descritivo em branco) - AUMENTADO
        desc_label = QLabel(label)
        desc_label.setObjectName("badge_label")
        desc_label.setStyleSheet("""
            QLabel#badge_label {
                font-size: 14px;
                font-weight: 400;
                color: #ffffff;
                background: transparent;
            }
        """)
        desc_label.setAlignment(Qt.AlignCenter)
        badge_layout.addWidget(desc_label)
        
        # Armazena referências aos labels para atualização posterior
        badge.value_label = value_label
        badge.desc_label = desc_label
        
        return badge
    
    def _start_created_workout(self):
        """Inicia o treino recém-criado."""
        if hasattr(self, '_last_created_routine'):
            self._on_start(self._last_created_routine)
        else:
            # Fallback: volta para a lista
            self._stack.setCurrentIndex(0)
            self.reload()
    
    def _animate_success_page(self):
        """Animação de entrada (Fade In + Slide Up) para a página de sucesso."""
        from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
        
        # Animação de opacidade (Fade In)
        self._fade_animation = QPropertyAnimation(self._success_container, b"windowOpacity")
        self._fade_animation.setDuration(600)
        self._fade_animation.setStartValue(0.0)
        self._fade_animation.setEndValue(1.0)
        self._fade_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Animação de posição (Slide Up)
        self._slide_animation = QPropertyAnimation(self._success_container, b"pos")
        self._slide_animation.setDuration(600)
        start_pos = self._success_container.pos()
        self._slide_animation.setStartValue(start_pos + self._success_container.rect().bottomLeft().__class__(0, 30))
        self._slide_animation.setEndValue(start_pos)
        self._slide_animation.setEasingCurve(QEasingCurve.OutCubic)
        
        # Grupo de animações paralelas
        self._animation_group = QParallelAnimationGroup()
        self._animation_group.addAnimation(self._fade_animation)
        self._animation_group.addAnimation(self._slide_animation)
        self._animation_group.start()

    # ------------------------------------------------------------------
    # Pesquisa
    # ------------------------------------------------------------------

    def _filter_routines(self, query: str):
        """Filtra os cards de rotina pelo nome em tempo real."""
        q = query.strip().lower()
        for routine, card in self._all_cards:
            visible = q == "" or q in routine.name.lower()
            card.setVisible(visible)

    # ------------------------------------------------------------------
    # Cardio avulso
    # ------------------------------------------------------------------

    def _open_cardio(self):
        self._cardio_search.clear()
        self._cardio_duration.setValue(30)
        self._cardio_distance.setValue(0)
        self._cardio_pse.setValue(5)
        self._stack.setCurrentIndex(2)

    def _build_cardio_page(self) -> QWidget:
        from src.ui.screens.cardio_widget import parse_cardio_types
        self._cardio_types = parse_cardio_types()

        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        # Cabeçalho
        hdr = QHBoxLayout()
        back_btn = QPushButton("← Voltar")
        back_btn.setObjectName("ghost")
        back_btn.setFixedWidth(90)
        back_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        hdr.addWidget(back_btn)
        hdr.addStretch()
        outer.addLayout(hdr)

        outer.addWidget(label("CARDIO AVULSO", "h2"))
        outer.addWidget(label("Registre uma atividade cardiovascular fora do treino.", "sub"))
        outer.addWidget(separator())

        # Tipo de cardio
        outer.addWidget(label("Tipo de Cardio", "h3"))
        self._cardio_search = QLineEdit()
        self._cardio_search.setPlaceholderText("Ex: Esteira, Corrida, Bicicleta...")
        self._cardio_search.setFixedHeight(42)
        self._cardio_search.setStyleSheet(f"""
            QLineEdit {{
                background: {C_CARD};
                color: {C_TEXT};
                border: 1px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                padding: 0 14px;
                font-size: 13px;
            }}
        """)
        outer.addWidget(self._cardio_search)

        # Popup flutuante de resultados
        self._cardio_popup = QListWidget(page)
        self._cardio_popup.setWindowFlags(Qt.ToolTip)
        self._cardio_popup.setFocusPolicy(Qt.NoFocus)
        self._cardio_popup.setStyleSheet(f"""
            QListWidget {{
                background: {C_CARD};
                border: 1px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
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
        self._cardio_popup.hide()
        self._cardio_popup.itemClicked.connect(self._cardio_on_item_clicked)

        self._cardio_filter_timer = QTimer(self)
        self._cardio_filter_timer.setSingleShot(True)
        self._cardio_filter_timer.setInterval(100)
        self._cardio_filter_timer.timeout.connect(self._cardio_update_popup)
        self._cardio_search.textChanged.connect(lambda _: self._cardio_filter_timer.start())
        self._cardio_search.mousePressEvent = lambda e: (
            QLineEdit.mousePressEvent(self._cardio_search, e),
            self._cardio_update_popup()
        )
        self._cardio_search.installEventFilter(self)

        # Métricas
        metrics = QFrame()
        metrics.setObjectName("card")
        m_lay = QVBoxLayout(metrics)
        m_lay.setContentsMargins(16, 16, 16, 16)
        m_lay.setSpacing(12)

        row1 = QHBoxLayout()
        row1.addWidget(label("Tempo (min) *", "h3"), 1)
        self._cardio_duration = QDoubleSpinBox()
        self._cardio_duration.setRange(1, 300)
        self._cardio_duration.setValue(30)
        self._cardio_duration.setSuffix(" min")
        self._cardio_duration.setDecimals(0)
        self._cardio_duration.setMinimumWidth(120)
        row1.addWidget(self._cardio_duration, 1)
        m_lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(label("Distância (km)", "h3"), 1)
        self._cardio_distance = QDoubleSpinBox()
        self._cardio_distance.setRange(0, 200)
        self._cardio_distance.setValue(0)
        self._cardio_distance.setSuffix(" km")
        self._cardio_distance.setDecimals(1)
        self._cardio_distance.setSpecialValueText("—")
        self._cardio_distance.setMinimumWidth(120)
        row2.addWidget(self._cardio_distance, 1)
        m_lay.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(label("Esforço (PSE 1-10)", "h3"), 1)
        pse_col = QVBoxLayout()
        self._cardio_pse = QSlider(Qt.Horizontal)
        self._cardio_pse.setRange(1, 10)
        self._cardio_pse.setValue(5)
        self._cardio_pse.setTickPosition(QSlider.TicksBelow)
        self._cardio_pse.setTickInterval(1)
        self._cardio_pse.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 6px; background: {C_CARD2}; border-radius: {RADIUS_SM}px;
            }}
            QSlider::handle:horizontal {{
                background: {C_GREEN}; width: 18px; height: 18px;
                margin: -6px 0; border-radius: 9px;
            }}
            QSlider::sub-page:horizontal {{
                background: {C_GREEN}; border-radius: {RADIUS_SM}px;
            }}
        """)
        self._cardio_pse_lbl = QLabel("5")
        self._cardio_pse_lbl.setStyleSheet(
            f"color:{C_GREEN}; font-size:18px; font-weight:800; min-width:24px; font-family:'Arial';"
        )
        self._cardio_pse_lbl.setAlignment(Qt.AlignCenter)
        self._cardio_pse.valueChanged.connect(lambda v: self._cardio_pse_lbl.setText(str(v)))
        pse_row = QHBoxLayout()
        pse_row.addWidget(self._cardio_pse)
        pse_row.addWidget(self._cardio_pse_lbl)
        pse_col.addLayout(pse_row)
        ref_row = QHBoxLayout()
        for txt in ["Leve", "Moderado", "Intenso", "Máximo"]:
            lbl = QLabel(txt)
            lbl.setStyleSheet(f"color:{C_TEXT3}; font-size:10px;")
            lbl.setAlignment(Qt.AlignCenter)
            ref_row.addWidget(lbl)
        pse_col.addLayout(ref_row)
        row3.addLayout(pse_col, 2)
        m_lay.addLayout(row3)

        outer.addWidget(metrics)
        outer.addStretch()

        save_btn = QPushButton("＋ Registrar Cardio")
        save_btn.setMinimumHeight(44)
        save_btn.clicked.connect(self._save_cardio)
        outer.addWidget(save_btn)

        return page

    def _cardio_update_popup(self):
        import unicodedata
        def norm(t):
            nfd = unicodedata.normalize("NFD", t.lower().strip())
            return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

        query = norm(self._cardio_search.text())
        self._cardio_popup.clear()
        matches = [ct for ct in self._cardio_types if query == "" or query in norm(ct["name"])]
        if not matches:
            self._cardio_popup.hide()
            return
        for ct in matches[:20]:
            intensity = ct.get("intensity", "")
            text = f"{ct['name']}  [{intensity}]" if intensity else ct["name"]
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, ct["name"])
            self._cardio_popup.addItem(item)
        pos = self._cardio_search.mapToGlobal(self._cardio_search.rect().bottomLeft())
        self._cardio_popup.setFixedWidth(self._cardio_search.width())
        row_h = self._cardio_popup.sizeHintForRow(0) if self._cardio_popup.count() > 0 else 36
        self._cardio_popup.setFixedHeight(min(280, row_h * min(self._cardio_popup.count(), 8) + 8))
        self._cardio_popup.move(pos)
        self._cardio_popup.show()
        self._cardio_popup.raise_()

    def _cardio_on_item_clicked(self, item: QListWidgetItem):
        self._cardio_search.blockSignals(True)
        self._cardio_search.setText(item.data(Qt.UserRole))
        self._cardio_search.blockSignals(False)
        self._cardio_popup.hide()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self._cardio_search:
            if event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Down and self._cardio_popup.isVisible():
                    self._cardio_popup.setFocus()
                    self._cardio_popup.setCurrentRow(0)
                    return True
                if event.key() == Qt.Key_Escape:
                    self._cardio_popup.hide()
                    return True
            if event.type() == QEvent.FocusOut:
                QTimer.singleShot(150, self._cardio_popup.hide)
        return super().eventFilter(obj, event)

    def _save_cardio(self):
        name = self._cardio_search.text().strip()
        if not name:
            QMessageBox.warning(self, "Atenção", "Selecione o tipo de cardio.")
            return
        dist = self._cardio_distance.value()
        session_id = self._db.execute_write(
            "INSERT INTO workout_sessions DEFAULT VALUES"
        )
        self._db.execute_write(
            "INSERT INTO cardio_logs (session_id, cardio_type, duration_min, distance_km, pse) VALUES (?,?,?,?,?)",
            (session_id, name, self._cardio_duration.value(),
             dist if dist > 0 else None, self._cardio_pse.value()),
        )
        self._db.execute_write(
            "UPDATE workout_sessions SET duration_seconds=? WHERE id=?",
            (int(self._cardio_duration.value() * 60), session_id),
        )
        QMessageBox.information(
            self, "Cardio Registrado",
            f"✓ {name}\n◷ {int(self._cardio_duration.value())} min"
            + (f" · {dist:.1f} km" if dist > 0 else "")
            + f"\n◈ PSE {self._cardio_pse.value()}/10",
        )
        self._stack.setCurrentIndex(0)



    # ------------------------------------------------------------------
    # Formulário inline de criação
    # ------------------------------------------------------------------

    def _build_create_page(self) -> QWidget:
        page = QWidget()
        page.setStyleSheet(f"background-color: {C_CARD};")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(40, 20, 40, 32)
        outer.setSpacing(0)

        # Cabeçalho com botão fechar (X) - fixo no topo
        hdr = QHBoxLayout()
        hdr.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 36)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #888;
                border: none;
                font-size: 24px;
                font-weight: 300;
            }
            QPushButton:hover { color: #fff; }
        """)
        close_btn.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        hdr.addWidget(close_btn)
        outer.addLayout(hdr)

        # Área de rolagem contendo todo o conteúdo
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background: {C_CARD}; border: none; }}")
        # Aplica rolagem suave otimizada
        apply_smooth_scroll(scroll)
        form_w = QWidget()
        form_w.setStyleSheet(f"background: {C_CARD};")
        self._form_lay = QVBoxLayout(form_w)
        self._form_lay.setSpacing(20)
        self._form_lay.setContentsMargins(0, 30, 0, 0)  # Padding-top generoso
        scroll.setWidget(form_w)
        outer.addWidget(scroll)

        # ===== TÍTULO E SUBTÍTULO (dentro da área de rolagem) =====
        title = QLabel("CRIAR TREINO")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #fff; background: transparent;")
        self._form_lay.addWidget(title)

        subtitle = QLabel("Monte seu treino personalizado com exercícios, séries e repetições.")
        subtitle.setStyleSheet("font-size: 13px; color: #AAAAAA; font-weight: normal; background: transparent;")
        self._form_lay.addWidget(subtitle)

        # Espaçamento após o subtítulo
        self._form_lay.addSpacing(24)

        # ===== NOME DO TREINO - FLOATING INPUT =====
        name_lbl = QLabel("Nome do treino")
        name_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #fff; margin-top: 4px; margin-bottom: 6px; background: transparent;")
        self._form_lay.addWidget(name_lbl)
        
        self._name = QLineEdit()
        self._name.setPlaceholderText("Ex: Treino D — Ombro")
        self._name.setFixedHeight(48)
        self._name.setStyleSheet("""
            QLineEdit {
                border: none;
                border-bottom: 2px solid #333333;
                background: transparent;
                color: white;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus { 
                border-bottom: 2px solid #a2ff00;
            }
        """)
        self._form_lay.addWidget(self._name)

        # ===== SELETOR DE DIAS (7 BOTÕES CIRCULARES) =====
        days_lbl = QLabel("Dias da semana")
        days_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #fff; margin-top: 12px; margin-bottom: 6px; background: transparent;")
        self._form_lay.addWidget(days_lbl)
        
        days_row = QHBoxLayout()
        days_row.setSpacing(12)
        self._day_buttons = []
        day_labels = ["S", "T", "Q", "Q", "S", "S", "D"]
        
        for day_label in day_labels:
            btn = QPushButton(day_label)
            btn.setCheckable(True)
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #888;
                    border: 2px solid #333333;
                    border-radius: 20px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    border-color: #555;
                    color: #aaa;
                }
                QPushButton:checked {
                    border-color: #a2ff00;
                    color: #a2ff00;
                }
            """)
            self._day_buttons.append(btn)
            days_row.addWidget(btn)
        
        days_row.addStretch()
        self._form_lay.addLayout(days_row)

        # Espaçamento para o layout "respirar"
        self._form_lay.addSpacing(30)

        # Exercícios
        ex_lbl = QLabel("Exercícios")
        ex_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #fff; margin-top: 8px; margin-bottom: 6px; background: transparent;")
        self._form_lay.addWidget(ex_lbl)
        
        self._ex_widgets: list[dict] = []
        self._ex_container = QVBoxLayout()
        self._ex_container.setSpacing(16)
        self._form_lay.addLayout(self._ex_container)
        self._add_exercise_block()

        # Botão adicionar exercício (estilo premium integrado)
        add_ex = QPushButton("＋  Adicionar exercício")
        add_ex.setObjectName("btn_adicionar")
        add_ex.setFixedHeight(44)
        add_ex.setStyleSheet("""
            QPushButton#btn_adicionar {
                background-color: #151515;
                color: #a2ff00;
                border: 1px solid #222222;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton#btn_adicionar:hover { 
                color: #b5ff00;
                border-color: #a2ff00;
                background-color: rgba(162, 255, 0, 0.08);
            }
        """)
        add_ex.clicked.connect(self._add_exercise_block)
        self._form_lay.addWidget(add_ex)

        # Espaçamento antes do botão salvar
        self._form_lay.addSpacing(30)

        # Botão Salvar Treino (dentro do scroll, último elemento)
        save = QPushButton("✓  SALVAR TREINO")
        save.setObjectName("btn_salvar_treino")
        save.setMinimumHeight(70)
        save.setStyleSheet("""
            QPushButton#btn_salvar_treino {
                background-color: #a2ff00;
                color: #000000;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                margin-top: 30px;
            }
            QPushButton#btn_salvar_treino:hover { 
                background-color: #b5ff00;
            }
            QPushButton#btn_salvar_treino:pressed { 
                background-color: #8ad900;
            }
        """)
        save.clicked.connect(self._save_workout)
        self._form_lay.addWidget(save)

        # Espaçamento final para garantir visibilidade total
        self._form_lay.addSpacing(20)

        return page

    def _add_exercise_block(self):
        """Cria um novo card de exercício com séries dinâmicas."""
        block = QFrame()
        block.setObjectName("componente_exercicio")
        block.setStyleSheet("""
            QFrame#componente_exercicio {
                background: transparent;
                border: 1px solid #333333;
                border-radius: 12px;
            }
        """)
        b_lay = QVBoxLayout(block)
        b_lay.setContentsMargins(20, 20, 20, 20)
        b_lay.setSpacing(16)

        # ===== NOME DO EXERCÍCIO - FLOATING INPUT =====
        name_edit = ExerciseLineEdit(self._norm, block)
        name_edit.setPlaceholderText("Nome do exercício")
        name_edit.setFixedHeight(48)
        name_edit.setStyleSheet("""
            QLineEdit {
                border: none;
                border-bottom: 2px solid #333333;
                background: transparent;
                color: white;
                padding: 10px;
                font-size: 15px;
                font-weight: bold;
            }
            QLineEdit:focus { 
                border-bottom: 2px solid #a2ff00;
            }
        """)
        b_lay.addWidget(name_edit)

        # ===== CABEÇALHO DAS COLUNAS =====
        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        header_row.setContentsMargins(0, 8, 0, 4)
        
        serie_hdr = QLabel("Série")
        serie_hdr.setFixedWidth(50)
        serie_hdr.setStyleSheet("font-size: 11px; color: #666; font-weight: bold; background: transparent;")
        header_row.addWidget(serie_hdr)
        
        peso_hdr = QLabel("Peso (kg)")
        peso_hdr.setStyleSheet("font-size: 11px; color: #666; font-weight: bold; background: transparent;")
        header_row.addWidget(peso_hdr, 1)
        
        reps_hdr = QLabel("Reps")
        reps_hdr.setStyleSheet("font-size: 11px; color: #666; font-weight: bold; background: transparent;")
        header_row.addWidget(reps_hdr, 1)
        
        b_lay.addLayout(header_row)

        # ===== CONTAINER DE SÉRIES =====
        series_container = QVBoxLayout()
        series_container.setSpacing(8)
        series_container.setContentsMargins(0, 0, 0, 0)
        
        # Lista para armazenar as linhas de série
        series_rows = []
        
        # Adiciona 3 séries iniciais
        for i in range(3):
            series_rows.append(self._create_series_row(i + 1, series_container, series_rows))
        
        b_lay.addLayout(series_container)

        # ===== BOTÃO ADICIONAR SÉRIE =====
        add_series_btn = QPushButton("+ Adicionar série")
        add_series_btn.setFixedHeight(44)  # Aumentado de 32 para 44
        add_series_btn.setStyleSheet("""
            QPushButton {
                background-color: #151515;
                color: #a2ff00;
                border: 1px solid #222222;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover { 
                color: #b5ff00;
                border-color: #a2ff00;
                background-color: rgba(162, 255, 0, 0.08);
            }
        """)
        
        # Conecta o botão para adicionar nova série
        def add_new_series():
            new_row = self._create_series_row(len(series_rows) + 1, series_container, series_rows)
            series_rows.append(new_row)
        
        add_series_btn.clicked.connect(add_new_series)
        b_lay.addWidget(add_series_btn)

        self._ex_container.addWidget(block)
        self._ex_widgets.append({
            "name": name_edit,
            "series_rows": series_rows,
            "series_container": series_container
        })

    def _create_series_row(self, series_num: int, parent_layout: QVBoxLayout, series_rows_list: list) -> dict:
        """Cria uma linha individual de série com número, peso e reps."""
        row = QHBoxLayout()
        row.setSpacing(12)
        row.setContentsMargins(0, 0, 0, 0)
        
        # Número da série (destaque verde neon)
        num_lbl = QLabel(str(series_num))
        num_lbl.setFixedWidth(50)
        num_lbl.setAlignment(Qt.AlignCenter)
        num_lbl.setStyleSheet("""
            font-size: 16px;
            color: #a2ff00;
            font-weight: bold;
            background: transparent;
        """)
        row.addWidget(num_lbl)
        
        # Input de Peso (estilo neon consistente)
        peso_input = QLineEdit()
        peso_input.setPlaceholderText("0")
        peso_input.setFixedHeight(36)
        peso_input.setStyleSheet("""
            QLineEdit {
                border: none;
                border-bottom: 2px solid #333333;
                background: transparent;
                color: #ccc;
                padding: 6px;
                font-size: 13px;
            }
            QLineEdit:focus { 
                border-bottom: 2px solid #a2ff00;
                color: white;
            }
        """)
        row.addWidget(peso_input, 1)
        
        # Input de Reps (estilo neon consistente)
        reps_input = QLineEdit()
        reps_input.setPlaceholderText("10-12")
        reps_input.setFixedHeight(36)
        reps_input.setStyleSheet("""
            QLineEdit {
                border: none;
                border-bottom: 2px solid #333333;
                background: transparent;
                color: #ccc;
                padding: 6px;
                font-size: 13px;
            }
            QLineEdit:focus { 
                border-bottom: 2px solid #a2ff00;
                color: white;
            }
        """)
        row.addWidget(reps_input, 1)
        
        # Cria o dicionário da série ANTES de criar o botão
        series_dict = {
            "num_label": num_lbl,
            "peso": peso_input,
            "reps": reps_input,
            "layout": row
        }
        
        # Botão de remover série (lixeira)
        remove_btn = QPushButton()
        remove_btn.setIcon(qta.icon("fa5s.trash", color="#ff4444"))
        remove_btn.setFixedSize(36, 36)
        remove_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #333333;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: rgba(255, 68, 68, 0.1);
                border-color: #ff4444;
            }
            QPushButton:pressed {
                background: rgba(255, 68, 68, 0.2);
            }
        """)
        remove_btn.setCursor(Qt.PointingHandCursor)
        
        # Conecta o botão para remover a série
        def remove_series():
            # Remove da lista primeiro
            if series_dict in series_rows_list:
                series_rows_list.remove(series_dict)
            
            # Remove os widgets do layout
            for i in range(row.count()):
                item = row.itemAt(i)
                if item.widget():
                    item.widget().deleteLater()
            parent_layout.removeItem(row)
            
            # Renumera as séries restantes
            for i, series_data in enumerate(series_rows_list):
                series_data["num_label"].setText(str(i + 1))
        
        remove_btn.clicked.connect(remove_series)
        series_dict["remove_btn"] = remove_btn
        row.addWidget(remove_btn)
        
        parent_layout.addLayout(row)
        
        return series_dict

    def _show_create_form(self):
        # Limpa o formulário antes de exibir
        self._name.clear()
        # Desmarca todos os botões de dias
        for btn in self._day_buttons:
            btn.setChecked(False)
        # Remove blocos de exercício existentes
        while self._ex_container.count():
            item = self._ex_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._ex_widgets.clear()
        self._add_exercise_block()
        self._stack.setCurrentIndex(1)

    def _save_workout(self):
        """Salva o treino com estrutura granular de exercícios e séries."""
        
        # ===== 1. COLETA DE DADOS DOS EXERCÍCIOS =====
        exercises = []
        for idx, w in enumerate(self._ex_widgets):
            exercise_name = w["name"].text().strip()
            
            if not exercise_name:
                continue  # Pula exercícios sem nome
            
            # Coleta dados de cada série individual
            series_data = []
            for series_idx, series_row in enumerate(w["series_rows"]):
                peso = series_row["peso"].text().strip()
                reps = series_row["reps"].text().strip()
                
                # Só adiciona séries que tenham pelo menos peso OU reps preenchidos
                if peso or reps:
                    series_data.append({
                        "serie_num": series_idx + 1,
                        "peso": peso if peso else "0",
                        "reps": reps if reps else "10-12"
                    })
            
            # Só adiciona o exercício se tiver pelo menos uma série com dados
            if series_data:
                exercises.append({
                    "name": exercise_name,
                    "series_count": len(series_data),
                    "series_data": series_data,
                    "reps": series_data[0]["reps"],  # Usa a primeira série como padrão
                    "rest": "60s"  # Valor padrão de descanso
                })
        
        # ===== 2. VALIDAÇÃO =====
        workout_name = self._name.text().strip()
        
        if not workout_name:
            QMessageBox.warning(
                self, 
                "Atenção", 
                "Por favor, informe o nome do treino."
            )
            return
        
        if not exercises:
            QMessageBox.warning(
                self, 
                "Atenção", 
                "Adicione pelo menos um exercício com séries preenchidas."
            )
            return
        
        # ===== 3. COLETA DOS DIAS SELECIONADOS =====
        day_labels = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        selected_days = [day_labels[i] for i, btn in enumerate(self._day_buttons) if btn.isChecked()]
        days_str = ", ".join(selected_days) if selected_days else "Não especificado"
        
        # ===== 4. SALVAMENTO NO BANCO =====
        try:
            ex_ids = [self._norm.get_or_create(e["name"]).id for e in exercises]
            default_sets_list = [e["series_count"] for e in exercises]
            self._rm.create_routine(workout_name, ex_ids, default_sets_list)
            
            # Busca a rotina recém-criada para poder iniciá-la depois
            routines = self._rm.list_routines()
            self._last_created_routine = next((r for r in routines if r.name == workout_name), None)
            
            # Prepara dados para a tela de sucesso
            total_series = sum(e["series_count"] for e in exercises)
            
            # Atualiza os labels da página de sucesso
            self._success_title.setText("Treino Criado!")
            self._success_workout_name.setText(workout_name)
            
            # Atualiza os badges de estatísticas
            # Badge 1: Exercícios
            self._badge_exercises.value_label.setText(str(len(exercises)))
            self._badge_exercises.desc_label.setText("exercício" if len(exercises) == 1 else "exercícios")
            
            # Badge 2: Séries
            self._badge_series.value_label.setText(str(total_series))
            self._badge_series.desc_label.setText("série" if total_series == 1 else "séries")
            
            # Badge 3: Dias
            if selected_days:
                # Se houver apenas um dia, mostra o nome completo
                if len(selected_days) == 1:
                    self._badge_days.value_label.setText(selected_days[0])
                    self._badge_days.desc_label.setText("")
                else:
                    # Se houver múltiplos dias, mostra a quantidade
                    self._badge_days.value_label.setText(str(len(selected_days)))
                    self._badge_days.desc_label.setText("dias")
            else:
                self._badge_days.value_label.setText("—")
                self._badge_days.desc_label.setText("sem dias")
            
            # Mostra a página de sucesso com animação
            self._stack.setCurrentIndex(4)
            
            # Inicia a animação após um pequeno delay para garantir que a página foi renderizada
            QTimer.singleShot(50, self._animate_success_page)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erro ao Salvar",
                f"Ocorreu um erro ao salvar o treino:\n{str(e)}"
            )



    def reload(self):
        self._all_cards.clear()
        while self._list_lay.count() > 1:
            item = self._list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        routines = self._rm.list_routines()
        if not routines:
            empty = label(
                "Nenhum treino criado ainda.\nClique em '+ Novo Treino' para começar.",
                "sub",
            )
            empty.setAlignment(Qt.AlignCenter)
            self._list_lay.insertWidget(0, empty)
            return

        for i, r in enumerate(routines):
            exercises_with_sets = self._rm.get_routine_exercises(r.id)
            c = RoutineCard(r, exercises_with_sets)
            c.start_clicked.connect(self._on_start)
            c.edit_clicked.connect(self._on_edit)
            self._list_lay.insertWidget(i, c)
            self._all_cards.append((r, c))

        # Reaplica filtro se houver texto na busca
        if self._search.text():
            self._filter_routines(self._search.text())

    def _on_start(self, routine: Routine):
        session_id = self._db.execute_write(
            "INSERT INTO workout_sessions (routine_id) VALUES (?)", (routine.id,)
        )
        self.start_workout.emit(routine, session_id)

    def _on_edit(self, routine: Routine):
        """Abre tela inline para editar nome e exercícios da rotina."""
        self._edit_widget.load_routine(routine)
        self._stack.setCurrentIndex(3)

    def _on_edit_saved(self):
        self.reload()
        self._stack.setCurrentIndex(0)
