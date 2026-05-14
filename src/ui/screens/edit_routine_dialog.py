"""
ui/screens/edit_routine_dialog.py
Widget inline para editar nome e exercícios de uma rotina existente.
"""
from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QScrollArea, QCheckBox,
    QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout, QWidget, QSpinBox, QLabel,
)

from engine import NormalizationEngine, Routine, RoutineManager
from src.ui.theme import (
    C_BORDER, C_GREEN, C_GREEN_BG, C_TEXT, C_TEXT2, C_CARD, C_CARD2, C_BG,
    label, separator, RADIUS_MD, RADIUS_LG, neon_glow, card
)


class EditRoutineWidget(QWidget):
    """Edita nome e lista de exercícios de uma rotina (tela inline)."""

    saved     = Signal()  # emitido ao salvar com sucesso
    cancelled = Signal()  # emitido ao cancelar

    def __init__(self, rm: RoutineManager, norm: NormalizationEngine, parent=None):
        super().__init__(parent)
        self._rm      = rm
        self._norm    = norm
        self._routine: Routine | None = None
        self._ex_ids: list[int] = []
        self._ex_names: list[str] = []
        self._ex_sets: list[int] = []  # Armazena o número de séries de cada exercício
        self._build()

    def load_routine(self, routine: Routine):
        """Carrega os dados da rotina para edição."""
        self._routine = routine
        self._ex_ids.clear()
        self._ex_names.clear()
        self._ex_sets.clear()
        self._list.clear()
        self._search.clear()
        self._popup.hide()
        self._name.setText(routine.name)
        exercises_with_sets = self._rm.get_routine_exercises(routine.id)
        met_exercises = self._get_exercises_with_met()
        for ex, default_sets in exercises_with_sets:
            self._ex_ids.append(ex.id)
            self._ex_names.append(ex.canonical_name)
            self._ex_sets.append(default_sets)
            # Cria widget customizado para o item
            self._add_exercise_to_list(ex, default_sets, met_exercises)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"QScrollArea {{ background: {C_BG}; border: none; }}")
        
        content = QWidget()
        content.setStyleSheet(f"QWidget {{ background: {C_BG}; }}")
        lay = QVBoxLayout(content)
        lay.setContentsMargins(32, 32, 32, 32)
        lay.setSpacing(24)

        # Header com botão voltar e título
        hdr = QHBoxLayout()
        hdr.setSpacing(16)
        
        back_btn = QPushButton()
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color=C_TEXT2))
        back_btn.setObjectName("ghost")
        back_btn.setFixedSize(44, 44)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_CARD};
                border: 2px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {C_CARD2};
                border-color: {C_GREEN};
            }}
        """)
        back_btn.clicked.connect(self.cancelled.emit)
        hdr.addWidget(back_btn)
        
        title_lbl = label("EDITAR TREINO", "h2")
        title_lbl.setStyleSheet(f"""
            QLabel {{
                color: {C_TEXT};
                font-size: 28px;
                font-weight: 800;
                letter-spacing: -0.5px;
            }}
        """)
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        lay.addLayout(hdr)

        # Card principal com todos os campos
        main_card = card()
        main_card.setStyleSheet(f"""
            QFrame {{
                background: {C_CARD};
                border: none;
                border-radius: {RADIUS_LG}px;
            }}
        """)
        card_lay = QVBoxLayout(main_card)
        card_lay.setContentsMargins(28, 28, 28, 28)
        card_lay.setSpacing(24)

        # Nome do treino
        name_section = QVBoxLayout()
        name_section.setSpacing(10)
        
        name_label = QLabel("Nome do Treino")
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {C_TEXT};
                font-size: 15px;
                font-weight: 700;
            }}
        """)
        name_section.addWidget(name_label)
        
        self._name = QLineEdit()
        self._name.setPlaceholderText("Ex: Treino A - Peito e Tríceps")
        self._name.setStyleSheet(f"""
            QLineEdit {{
                background: {C_BG};
                color: {C_TEXT};
                border: 1px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 14px 18px;
                font-size: 15px;
            }}
            QLineEdit:focus {{
                border-color: {C_GREEN};
            }}
        """)
        name_section.addWidget(self._name)
        card_lay.addLayout(name_section)

        # Separador
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background: {C_BORDER}; max-height: 1px;")
        card_lay.addWidget(sep)

        # Seção de exercícios
        ex_label = QLabel("Exercícios do Treino")
        ex_label.setStyleSheet(f"""
            QLabel {{
                color: {C_TEXT};
                font-size: 15px;
                font-weight: 700;
            }}
        """)
        card_lay.addWidget(ex_label)
        
        # Checkbox para filtrar apenas exercícios com MET
        self._filter_met = QCheckBox("  Mostrar apenas exercícios com cálculo de calorias 🔥")
        self._filter_met.setChecked(True)
        self._filter_met.setStyleSheet(f"""
            QCheckBox {{
                color: {C_TEXT2};
                font-size: 14px;
                spacing: 8px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid {C_BORDER};
                border-radius: 6px;
                background: {C_CARD2};
            }}
            QCheckBox::indicator:checked {{
                background: {C_GREEN};
                border-color: {C_GREEN};
                image: url(none);
            }}
            QCheckBox::indicator:hover {{
                border-color: {C_GREEN};
            }}
        """)
        self._filter_met.stateChanged.connect(self._on_search_changed)
        card_lay.addWidget(self._filter_met)
        
        # Busca de exercício
        search_row = QHBoxLayout()
        search_row.setSpacing(12)
        
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍 Buscar exercício para adicionar...")
        self._search.returnPressed.connect(self._add_exercise)
        self._search.textChanged.connect(self._on_search_changed)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background: {C_BG};
                color: {C_TEXT};
                border: 1px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 14px 18px;
                font-size: 15px;
            }}
            QLineEdit:focus {{
                border-color: {C_GREEN};
            }}
        """)
        search_row.addWidget(self._search, 1)
        
        add_btn = QPushButton(" Adicionar")
        add_btn.setIcon(qta.icon("fa5s.plus", color="#000000"))
        add_btn.setFixedHeight(48)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_GREEN};
                color: #000000;
                border: none;
                border-radius: {RADIUS_MD}px;
                padding: 0 24px;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: #8ad900;
            }}
        """)
        add_btn.clicked.connect(self._add_exercise)
        search_row.addWidget(add_btn)
        card_lay.addLayout(search_row)

        # Popup de resultados
        self._popup = QListWidget(self)
        self._popup.setWindowFlags(Qt.ToolTip)
        self._popup.setFocusPolicy(Qt.NoFocus)
        self._popup.setMaximumHeight(280)
        self._popup.setStyleSheet(f"""
            QListWidget {{
                background: {C_CARD};
                border: 2px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                font-size: 14px;
            }}
            QListWidget::item {{ 
                padding: 12px 16px; 
                color: {C_TEXT2};
                border-bottom: 1px solid {C_BORDER};
            }}
            QListWidget::item:hover {{ 
                background: {C_CARD2}; 
                color: {C_TEXT}; 
            }}
            QListWidget::item:selected {{ 
                background: {C_GREEN_BG}; 
                color: {C_GREEN}; 
            }}
        """)
        self._popup.hide()
        self._popup.itemClicked.connect(self._on_popup_click)

        # Lista de exercícios da rotina
        self._list = QListWidget()
        self._list.setMinimumHeight(400)
        self._list.setStyleSheet(f"""
            QListWidget {{
                background: #151515;
                border: none;
                border-radius: {RADIUS_MD}px;
                font-size: 14px;
            }}
            QListWidget::item {{
                padding: 0px;
                margin: 6px 4px;
                border: none;
                background: transparent;
            }}
            QListWidget::item:hover {{
                background: transparent;
            }}
            QListWidget::item:selected {{
                background: transparent;
            }}
        """)
        card_lay.addWidget(self._list)

        # Botão remover
        remove_btn = QPushButton(" Remover Selecionado")
        remove_btn.setIcon(qta.icon("fa5s.trash", color=C_TEXT2))
        remove_btn.setObjectName("ghost")
        remove_btn.setFixedHeight(44)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C_BG};
                color: {C_TEXT2};
                border: none;
                border-radius: {RADIUS_MD}px;
                padding: 0 20px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #121212;
                color: {C_TEXT};
            }}
        """)
        remove_btn.clicked.connect(self._remove_selected)
        card_lay.addWidget(remove_btn)

        lay.addWidget(main_card)

        # Footer com botões de ação
        footer = QHBoxLayout()
        footer.setSpacing(12)

        btn_cancel = QPushButton(" Cancelar")
        btn_cancel.setIcon(qta.icon("fa5s.times", color=C_TEXT2))
        btn_cancel.setFixedHeight(48)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: {C_CARD};
                color: {C_TEXT2};
                border: none;
                border-radius: {RADIUS_MD}px;
                padding: 0 28px;
                font-size: 15px;
                font-weight: 600;
            }}
            QPushButton:hover {{ 
                background: {C_CARD2};
                color: {C_TEXT};
            }}
        """)
        btn_cancel.clicked.connect(self.cancelled.emit)

        btn_save = QPushButton(" Salvar Alterações")
        btn_save.setIcon(qta.icon("fa5s.check", color="#000000"))
        btn_save.setFixedHeight(48)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background: {C_GREEN};
                color: #000000;
                border: none;
                border-radius: {RADIUS_MD}px;
                padding: 0 32px;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton:hover {{ 
                background: #8ad900;
            }}
        """)
        neon_glow(btn_save, C_GREEN, blur=30, opacity=120)
        btn_save.clicked.connect(self._save)

        footer.addStretch()
        footer.addWidget(btn_cancel)
        footer.addWidget(btn_save)
        lay.addLayout(footer)

        lay.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll)

    def _get_exercises_with_met(self) -> set[int]:
        """Retorna conjunto de IDs de exercícios que possuem valores MET parametrizados."""
        rows = self._rm._db.fetchall("SELECT exercise_id FROM exercise_met_values")
        return {row["exercise_id"] for row in rows}

    def _add_exercise_to_list(self, ex, default_sets: int, met_exercises: set[int]):
        """Adiciona um exercício à lista com widget customizado incluindo spinbox para séries."""
        # Cria o item da lista
        item = QListWidgetItem(self._list)
        item.setData(Qt.UserRole, ex.id)
        
        # Cria widget customizado
        widget = QWidget()
        widget.setStyleSheet(f"""
            QWidget {{
                background: transparent;
                border: none;
                border-radius: {RADIUS_MD}px;
            }}
            QWidget:hover {{
                background: #0f0f0f;
            }}
        """)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(18)
        
        # Ícone do grupo muscular
        icon_map = {
            "Peito": "fa5s.heart",
            "Costas": "fa5s.user",
            "Ombros": "fa5s.angle-double-up",
            "Bíceps": "fa5s.fist-raised",
            "Tríceps": "fa5s.hand-rock",
            "Pernas": "fa5s.running",
            "Abdômen": "fa5s.square",
        }
        icon_name = icon_map.get(ex.muscle_group_name, "fa5s.dumbbell")
        icon_label = QLabel()
        icon_label.setPixmap(qta.icon(icon_name, color=C_GREEN).pixmap(24, 24))
        icon_label.setFixedSize(32, 32)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # Container de informações do exercício
        info_container = QVBoxLayout()
        info_container.setSpacing(4)
        
        # Nome do exercício
        met_indicator = " 🔥" if ex.id in met_exercises else ""
        name_label = QLabel(f"{ex.canonical_name.title()}{met_indicator}")
        name_label.setStyleSheet(f"""
            QLabel {{
                color: {C_TEXT};
                font-size: 16px;
                font-weight: 600;
                background: transparent;
            }}
        """)
        info_container.addWidget(name_label)
        
        # Grupo muscular
        muscle_label = QLabel(ex.muscle_group_name)
        muscle_label.setStyleSheet(f"""
            QLabel {{
                color: {C_TEXT2};
                font-size: 13px;
                background: transparent;
            }}
        """)
        info_container.addWidget(muscle_label)
        
        layout.addLayout(info_container, 1)
        
        # Container de séries
        sets_container = QHBoxLayout()
        sets_container.setSpacing(12)
        
        # Label "Séries:"
        sets_label = QLabel("Séries:")
        sets_label.setStyleSheet(f"""
            QLabel {{
                color: {C_TEXT2};
                font-size: 14px;
                font-weight: 600;
                background: transparent;
            }}
        """)
        sets_container.addWidget(sets_label)
        
        # SpinBox para número de séries
        spinbox = QSpinBox()
        spinbox.setMinimum(1)
        spinbox.setMaximum(10)
        spinbox.setFixedWidth(75)
        spinbox.setFixedHeight(38)
        spinbox.setStyleSheet(f"""
            QSpinBox {{
                background: #0a0a0a;
                color: {C_TEXT};
                border: 1px solid {C_BORDER};
                border-radius: 8px;
                padding: 6px 10px;
                font-size: 16px;
                font-weight: 700;
            }}
            QSpinBox:focus {{
                border-color: {C_GREEN};
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: transparent;
                border: none;
                width: 20px;
            }}
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background: {C_BORDER};
                border-radius: 4px;
            }}
            QSpinBox::up-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 6px solid {C_GREEN};
                width: 0;
                height: 0;
            }}
            QSpinBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {C_GREEN};
                width: 0;
                height: 0;
            }}
        """)
        
        sets_container.addWidget(spinbox)
        layout.addLayout(sets_container)
        
        # Define o tamanho do item
        item.setSizeHint(widget.sizeHint())
        
        # Adiciona o item e o widget
        self._list.addItem(item)
        self._list.setItemWidget(item, widget)
        
        # Conecta mudança de valor DEPOIS de adicionar à lista
        # Usa o índice correto baseado na posição final
        final_row = self._list.count() - 1
        spinbox.valueChanged.connect(lambda value, r=final_row: self._update_sets(r, value))
        
        # Define o valor DEPOIS de conectar o sinal para garantir que o índice está correto
        spinbox.setValue(default_sets)
    
    def _update_sets(self, row: int, value: int):
        """Atualiza o número de séries para um exercício específico."""
        if 0 <= row < len(self._ex_sets):
            self._ex_sets[row] = value

    def _on_search_changed(self, text: str = None):
        # Se text não foi passado, pega do campo de busca
        if text is None:
            text = self._search.text()
            
        if not text.strip():
            self._popup.hide()
            return
        
        # Normaliza o texto de busca (lowercase, sem acentos)
        search_normalized = self._norm._normalize_text(text)
        
        # Busca todos os exercícios
        rows = self._norm._db.fetchall(
            "SELECT id, canonical_name, user_input_name FROM exercises ORDER BY canonical_name"
        )
        
        # Filtra por substring (busca "rem" encontra "remada", "supino reto remador", etc)
        matches = []
        met_exercises = self._get_exercises_with_met()
        
        for row in rows:
            canonical = row["canonical_name"]
            # Verifica se o texto de busca está contido no nome do exercício
            if search_normalized in canonical:
                # Filtra por MET se checkbox estiver marcado
                if self._filter_met.isChecked() and row["id"] not in met_exercises:
                    continue
                    
                ex = self._norm._load_exercise(row["id"], canonical, row["user_input_name"])
                matches.append(ex)
                
                # Limita a 20 resultados
                if len(matches) >= 20:
                    break
        
        if not matches:
            self._popup.hide()
            return
            
        self._popup.clear()
        for ex in matches:
            # Adiciona indicador visual de MET
            met_indicator = " 🔥" if ex.id in met_exercises else ""
            item = QListWidgetItem(f"{ex.canonical_name.title()}  [{ex.muscle_group_name}]{met_indicator}")
            item.setData(Qt.UserRole, ex)
            self._popup.addItem(item)
            
        pos = self._search.mapToGlobal(self._search.rect().bottomLeft())
        self._popup.setFixedWidth(self._search.width())
        row_h = self._popup.sizeHintForRow(0) if self._popup.count() > 0 else 30
        self._popup.setFixedHeight(min(200, row_h * min(self._popup.count(), 7) + 8))
        self._popup.move(pos)
        self._popup.show()
        self._popup.raise_()

    def _on_popup_click(self, item: QListWidgetItem):
        ex = item.data(Qt.UserRole)
        if ex and ex.id not in self._ex_ids:
            self._ex_ids.append(ex.id)
            self._ex_names.append(ex.canonical_name)
            self._ex_sets.append(3)  # Valor padrão de 3 séries
            met_exercises = self._get_exercises_with_met()
            self._add_exercise_to_list(ex, 3, met_exercises)
        self._search.clear()
        self._popup.hide()

    def _add_exercise(self):
        text = self._search.text().strip()
        if not text:
            return
        if self._popup.isVisible() and self._popup.currentItem():
            self._on_popup_click(self._popup.currentItem())
            return
        matches = self._norm.resolve(text, threshold=0.4)
        
        # Filtra por MET se checkbox estiver marcado
        if self._filter_met.isChecked():
            met_exercises = self._get_exercises_with_met()
            matches = [m for m in matches if m.exercise.id in met_exercises]
        
        ex = matches[0].exercise if matches else self._norm.get_or_create(text)
        if ex.id not in self._ex_ids:
            self._ex_ids.append(ex.id)
            self._ex_names.append(ex.canonical_name)
            self._ex_sets.append(3)  # Valor padrão de 3 séries
            met_exercises = self._get_exercises_with_met()
            self._add_exercise_to_list(ex, 3, met_exercises)
        self._search.clear()
        self._popup.hide()

    def _remove_selected(self):
        row = self._list.currentRow()
        if row >= 0:
            self._list.takeItem(row)
            self._ex_ids.pop(row)
            self._ex_names.pop(row)
            self._ex_sets.pop(row)

    def _save(self):
        name = self._name.text().strip()
        if not name:
            QMessageBox.warning(self, "Atenção", "Informe o nome do treino.")
            return
        if not self._ex_ids:
            QMessageBox.warning(self, "Atenção", "Adicione ao menos um exercício.")
            return
        self._rm._db.execute_write(
            "UPDATE routines SET name=? WHERE id=?",
            (name, self._routine.id),
        )
        self._rm.update_routine_template(self._routine.id, self._ex_ids, self._ex_sets)
        self.saved.emit()
