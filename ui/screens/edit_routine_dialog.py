"""
ui/screens/edit_routine_dialog.py
Diálogo para editar nome e exercícios de uma rotina existente.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QVBoxLayout,
)

from engine import NormalizationEngine, Routine, RoutineManager
from ui.theme import C_BORDER, C_GREEN, C_GREEN_BG, C_RED, C_TEXT, C_TEXT2, C_TEXT3, label, separator


class EditRoutineDialog(QDialog):
    """Edita nome e lista de exercícios de uma rotina."""

    def __init__(self, routine: Routine, rm: RoutineManager,
                 norm: NormalizationEngine, parent=None):
        super().__init__(parent)
        self._routine = routine
        self._rm      = rm
        self._norm    = norm
        self._ex_ids: list[int] = []
        self._ex_names: list[str] = []
        self.setWindowTitle("Editar Treino")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.resize(640, 560)
        self._build()
        self._load_current()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        lay.addWidget(label("EDITAR TREINO", "h2"))
        lay.addWidget(separator())

        # Nome
        lay.addWidget(label("Nome do treino", "h3"))
        self._name = QLineEdit()
        self._name.setPlaceholderText("Nome do treino")
        lay.addWidget(self._name)

        # Busca de exercício com popup
        lay.addWidget(label("Exercícios", "h3"))
        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Buscar exercício para adicionar...")
        self._search.returnPressed.connect(self._add_exercise)
        self._search.textChanged.connect(self._on_search_changed)
        add_btn = QPushButton("Adicionar")
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
                border-radius: 8px;
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
        remove_btn = QPushButton("X Remover Selecionado")
        remove_btn.setObjectName("danger")
        remove_btn.clicked.connect(self._remove_selected)
        lay.addWidget(remove_btn)

        # Confirmar / Cancelar
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _load_current(self):
        """Preenche o diálogo com os dados atuais da rotina."""
        self._name.setText(self._routine.name)
        exercises = self._rm.get_routine_exercises(self._routine.id)
        for ex in exercises:
            self._ex_ids.append(ex.id)
            self._ex_names.append(ex.canonical_name)
            item = QListWidgetItem(f"{ex.canonical_name.title()}  [{ex.muscle_group_name}]")
            item.setData(Qt.UserRole, ex.id)
            self._list.addItem(item)

    def _on_search_changed(self, text: str):
        """Filtra exercícios em tempo real e mostra popup."""
        if not text.strip():
            self._popup.hide()
            return
        matches = self._norm.resolve(text, threshold=0.3)
        if not matches:
            self._popup.hide()
            return
        self._popup.clear()
        for m in matches[:12]:
            ex = m.exercise
            item = QListWidgetItem(f"{ex.canonical_name.title()}  [{ex.muscle_group_name}]")
            item.setData(Qt.UserRole, ex)
            self._popup.addItem(item)
        # Posiciona abaixo do campo de busca
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
            list_item = QListWidgetItem(f"{ex.canonical_name.title()}  [{ex.muscle_group_name}]")
            list_item.setData(Qt.UserRole, ex.id)
            self._list.addItem(list_item)
        self._search.clear()
        self._popup.hide()

    def _add_exercise(self):
        """Adiciona o primeiro resultado da busca ou o que está no campo."""
        text = self._search.text().strip()
        if not text:
            return
        # Se popup tem item selecionado, usa ele
        if self._popup.isVisible() and self._popup.currentItem():
            self._on_popup_click(self._popup.currentItem())
            return
        matches = self._norm.resolve(text, threshold=0.4)
        ex = matches[0].exercise if matches else self._norm.get_or_create(text)
        if ex.id not in self._ex_ids:
            self._ex_ids.append(ex.id)
            self._ex_names.append(ex.canonical_name)
            item = QListWidgetItem(f"{ex.canonical_name.title()}  [{ex.muscle_group_name}]")
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
        # Atualiza nome
        self._rm._db.execute_write(
            "UPDATE routines SET name=? WHERE id=?",
            (name, self._routine.id),
        )
        # Atualiza exercícios
        self._rm.update_routine_template(self._routine.id, self._ex_ids)
        self.accept()
