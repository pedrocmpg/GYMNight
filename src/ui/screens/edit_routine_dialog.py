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
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from engine import NormalizationEngine, Routine, RoutineManager
from src.ui.theme import C_BORDER, C_GREEN, C_GREEN_BG, C_TEXT, C_TEXT2, label, separator, RADIUS_MD


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
        self._build()

    def load_routine(self, routine: Routine):
        """Carrega os dados da rotina para edição."""
        self._routine = routine
        self._ex_ids.clear()
        self._ex_names.clear()
        self._list.clear()
        self._search.clear()
        self._popup.hide()
        self._name.setText(routine.name)
        exercises_with_sets = self._rm.get_routine_exercises(routine.id)
        exercises = [ex for ex, _ in exercises_with_sets]  # Extrai apenas os exercícios
        met_exercises = self._get_exercises_with_met()
        for ex in exercises:
            self._ex_ids.append(ex.id)
            self._ex_names.append(ex.canonical_name)
            # Adiciona indicador visual de MET
            met_indicator = " 🔥" if ex.id in met_exercises else ""
            item = QListWidgetItem(f"{ex.canonical_name.title()}  [{ex.muscle_group_name}]{met_indicator}")
            item.setData(Qt.UserRole, ex.id)
            self._list.addItem(item)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        # Header com botão voltar
        hdr = QHBoxLayout()
        back_btn = QPushButton(" Voltar")
        back_btn.setIcon(qta.icon("fa5s.arrow-left", color=C_TEXT2))
        back_btn.setObjectName("ghost")
        back_btn.setFixedWidth(90)
        back_btn.clicked.connect(self.cancelled.emit)
        hdr.addWidget(back_btn)
        hdr.addStretch()
        lay.addLayout(hdr)

        lay.addWidget(label("EDITAR TREINO", "h2"))
        lay.addWidget(separator())

        # Nome
        lay.addWidget(label("Nome do treino", "h3"))
        self._name = QLineEdit()
        self._name.setPlaceholderText("Nome do treino")
        lay.addWidget(self._name)

        # Busca de exercício com popup
        lay.addWidget(label("Exercícios", "h3"))
        
        # Checkbox para filtrar apenas exercícios com MET
        self._filter_met = QCheckBox("Mostrar apenas exercícios com cálculo de calorias")
        self._filter_met.setChecked(True)  # Ativado por padrão
        self._filter_met.setStyleSheet(f"""
            QCheckBox {{
                color: {C_TEXT2};
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {C_BORDER};
                border-radius: 4px;
                background: #1e1e1e;
            }}
            QCheckBox::indicator:checked {{
                background: {C_GREEN};
                border-color: {C_GREEN};
            }}
            QCheckBox::indicator:hover {{
                border-color: {C_GREEN};
            }}
        """)
        self._filter_met.stateChanged.connect(self._on_search_changed)
        lay.addWidget(self._filter_met)
        
        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Buscar exercício para adicionar...")
        self._search.returnPressed.connect(self._add_exercise)
        self._search.textChanged.connect(self._on_search_changed)
        add_btn = QPushButton(" Adicionar")
        add_btn.setIcon(qta.icon("fa5s.plus", color="#000000"))
        add_btn.setFixedHeight(38)
        add_btn.clicked.connect(self._add_exercise)
        search_row.addWidget(self._search)
        search_row.addWidget(add_btn)
        lay.addLayout(search_row)

        # Popup de resultados
        self._popup = QListWidget(self)
        self._popup.setWindowFlags(Qt.ToolTip)
        self._popup.setFocusPolicy(Qt.NoFocus)
        self._popup.setMaximumHeight(200)
        self._popup.setStyleSheet(f"""
            QListWidget {{
                background: #1e1e1e;
                border: 1px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                font-size: 14px;
            }}
            QListWidget::item {{ padding: 8px 12px; color: {C_TEXT2}; }}
            QListWidget::item:hover {{ background: #2a2a2a; color: {C_TEXT}; }}
            QListWidget::item:selected {{ background: #1a2e1a; color: {C_GREEN}; }}
        """)
        self._popup.hide()
        self._popup.itemClicked.connect(self._on_popup_click)

        # Lista de exercícios da rotina
        self._list = QListWidget()
        self._list.setMinimumHeight(180)
        lay.addWidget(self._list)

        # Botão remover
        remove_btn = QPushButton(" Remover Selecionado")
        remove_btn.setIcon(qta.icon("fa5s.trash", color="#ffffff"))
        remove_btn.setObjectName("danger")
        remove_btn.clicked.connect(self._remove_selected)
        lay.addWidget(remove_btn)

        # Confirmar / Cancelar
        footer = QHBoxLayout()
        footer.setSpacing(10)

        btn_cancel = QPushButton(" Cancelar")
        btn_cancel.setIcon(qta.icon("fa5s.times", color=C_TEXT2))
        btn_cancel.setFixedHeight(36)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C_TEXT2};
                border: 1px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 0 16px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background: {C_BORDER}; }}
        """)
        btn_cancel.clicked.connect(self.cancelled.emit)

        btn_save = QPushButton(" Salvar")
        btn_save.setIcon(qta.icon("fa5s.save", color="#000000"))
        btn_save.setFixedHeight(36)
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background: {C_GREEN};
                color: #000000;
                border: none;
                border-radius: {RADIUS_MD}px;
                padding: 0 20px;
                font-size: 13px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background: #bef264; }}
        """)
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
            # Adiciona indicador visual de MET
            met_indicator = " 🔥" if ex.id in self._get_exercises_with_met() else ""
            list_item = QListWidgetItem(f"{ex.canonical_name.title()}  [{ex.muscle_group_name}]{met_indicator}")
            list_item.setData(Qt.UserRole, ex.id)
            self._list.addItem(list_item)
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
            # Adiciona indicador visual de MET
            met_indicator = " 🔥" if ex.id in self._get_exercises_with_met() else ""
            item = QListWidgetItem(f"{ex.canonical_name.title()}  [{ex.muscle_group_name}]{met_indicator}")
            item.setData(Qt.UserRole, ex.id)
            self._list.addItem(item)
        self._search.clear()
        self._popup.hide()

    def _remove_selected(self):
        row = self._list.currentRow()
        if row >= 0:
            self._list.takeItem(row)
            self._ex_ids.pop(row)
            self._ex_names.pop(row)

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
        self._rm.update_routine_template(self._routine.id, self._ex_ids)
        self.saved.emit()
