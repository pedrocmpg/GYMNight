"""
ui/dialogs.py
Diálogos modais: CreateWorkoutDialog com autocomplete de exercícios.
"""
from __future__ import annotations
import unicodedata

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QCompleter, QDialog, QFrame, QHBoxLayout, QLineEdit,
    QListView, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from engine import NormalizationEngine
from ui.theme import C_BORDER, C_CARD, C_CARD2, C_GREEN, C_TEXT, C_TEXT2, label, separator


def _norm(text: str) -> str:
    """Lowercase + remove acentos."""
    nfd = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------------------
# ExerciseLineEdit — QLineEdit com QCompleter que filtra por substring
# ---------------------------------------------------------------------------

class ExerciseLineEdit(QLineEdit):
    """
    Campo de texto com autocomplete de exercícios.
    - Filtra por substring (MatchContains), case-insensitive, sem acentos
    - Exibe "nome [Grupo Muscular]" na lista
    - Popup abre ao digitar qualquer caractere
    - Não auto-preenche antes do usuário confirmar
    """

    def __init__(self, norm: NormalizationEngine, parent=None):
        super().__init__(parent)
        self._norm = norm
        self.setPlaceholderText("Digite para buscar exercício...")
        self._build_completer()

    def _build_completer(self):
        # Carrega todos os exercícios
        rows = self._norm._db.fetchall(
            "SELECT id, canonical_name, user_input_name FROM exercises ORDER BY canonical_name"
        )
        exercises = [
            self._norm._load_exercise(r["id"], r["canonical_name"], r["user_input_name"])
            for r in rows
        ]

        # Modelo com display "nome [Grupo]" e dado normalizado para filtro
        self._model = QStandardItemModel()
        for ex in exercises:
            muscle = ex.muscle_group_name or "—"
            display = f"{ex.canonical_name.title()}  [{muscle}]"
            item = QStandardItem(display)
            # Armazena nome normalizado para filtro sem acentos
            item.setData(_norm(ex.canonical_name), Qt.UserRole)
            item.setData(ex.canonical_name, Qt.UserRole + 1)  # nome original
            self._model.appendRow(item)

        # QCompleter com MatchContains
        self._completer = QCompleter(self._model, self)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self._completer.setFilterMode(Qt.MatchContains)
        self._completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._completer.setMaxVisibleItems(14)
        self._completer.setCompletionRole(Qt.DisplayRole)

        # Popup estilizado
        popup = QListView()
        popup.setStyleSheet(f"""
            QListView {{
                background: {C_CARD};
                border: 1px solid {C_GREEN};
                border-radius: 8px;
                outline: none;
                font-size: 13px;
                padding: 4px;
            }}
            QListView::item {{
                padding: 8px 14px;
                color: {C_TEXT2};
                border-bottom: 1px solid {C_BORDER};
            }}
            QListView::item:hover {{
                background: {C_CARD2};
                color: {C_TEXT};
            }}
            QListView::item:selected {{
                background: #1a2e1a;
                color: {C_GREEN};
            }}
        """)
        self._completer.setPopup(popup)
        self.setCompleter(self._completer)

        # Ao confirmar, preenche com o nome canônico (sem o "[Grupo]")
        self._completer.activated[str].connect(self._on_activated)

    def _on_activated(self, display_text: str):
        """Extrai só o nome do exercício do display 'nome  [Grupo]'."""
        name = display_text.split("  [")[0].strip()
        self.blockSignals(True)
        self.setText(name)
        self.blockSignals(False)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        # Força o popup a abrir mesmo com texto curto
        if self.text() and self._completer:
            self._completer.setCompletionPrefix(self.text())
            if self._completer.completionCount() > 0:
                self._completer.complete()


# ---------------------------------------------------------------------------
# CreateWorkoutDialog
# ---------------------------------------------------------------------------

class CreateWorkoutDialog(QDialog):
    def __init__(self, norm: NormalizationEngine, parent=None):
        super().__init__(parent)
        self._norm = norm
        self._ex_widgets: list[dict] = []
        self.setWindowTitle("Criar Treino")
        self.setMinimumWidth(500)
        self.setMaximumHeight(700)
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(16)

        lay.addWidget(label("CRIAR TREINO", "h2"))
        lay.addWidget(label("Monte seu treino personalizado com exercícios, séries e repetições.", "sub"))
        lay.addWidget(separator())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        form_w = QWidget()
        self._form_lay = QVBoxLayout(form_w)
        self._form_lay.setSpacing(14)
        scroll.setWidget(form_w)
        lay.addWidget(scroll)

        # Nome
        self._form_lay.addWidget(label("Nome do treino", "h3"))
        self._name = QLineEdit()
        self._name.setPlaceholderText("Ex: Treino D — Ombro")
        self._form_lay.addWidget(self._name)

        # Dia + Músculos
        row = QHBoxLayout()
        for attr, lbl_txt, ph in [
            ("_days",    "Dia(s)",    "Ex: Segunda"),
            ("_muscles", "Músculos",  "Ex: Ombro & Trapézio"),
        ]:
            col = QVBoxLayout()
            col.addWidget(label(lbl_txt, "h3"))
            edit = QLineEdit()
            edit.setPlaceholderText(ph)
            setattr(self, attr, edit)
            col.addWidget(edit)
            row.addLayout(col)
        self._form_lay.addLayout(row)

        # Exercícios
        self._form_lay.addWidget(label("Exercícios", "h3"))
        self._ex_container = QVBoxLayout()
        self._ex_container.setSpacing(10)
        self._form_lay.addLayout(self._ex_container)
        self._add_exercise_block()

        add_ex = QPushButton("+ Adicionar exercício")
        add_ex.setObjectName("ghost")
        add_ex.clicked.connect(self._add_exercise_block)
        self._form_lay.addWidget(add_ex)

        save = QPushButton("Salvar Treino")
        save.setMinimumHeight(44)
        save.clicked.connect(self.accept)
        lay.addWidget(save)

    def _add_exercise_block(self):
        idx = len(self._ex_widgets) + 1
        block = QFrame()
        block.setObjectName("card")
        b_lay = QVBoxLayout(block)
        b_lay.setContentsMargins(12, 12, 12, 12)
        b_lay.setSpacing(8)
        b_lay.addWidget(label(f"Exercício {idx}", "sub"))

        # Campo com autocomplete
        name_edit = ExerciseLineEdit(self._norm, block)
        b_lay.addWidget(name_edit)

        row = QHBoxLayout()
        series = QSpinBox()
        series.setRange(1, 20)
        series.setValue(3)
        reps = QLineEdit("10-12")
        rest = QLineEdit("60s")
        for w, lbl_txt in [(series, "Séries"), (reps, "Reps"), (rest, "Descanso")]:
            col = QVBoxLayout()
            col.addWidget(label(lbl_txt, "sub"))
            col.addWidget(w)
            row.addLayout(col)
        b_lay.addLayout(row)

        self._ex_container.addWidget(block)
        self._ex_widgets.append({"name": name_edit, "series": series, "reps": reps, "rest": rest})

    def get_data(self) -> dict:
        exercises = []
        for w in self._ex_widgets:
            n = w["name"].text().strip()
            if n:
                exercises.append({
                    "name": n,
                    "series": w["series"].value(),
                    "reps": w["reps"].text(),
                    "rest": w["rest"].text(),
                })
        return {
            "name": self._name.text().strip(),
            "days": self._days.text().strip(),
            "muscles": self._muscles.text().strip(),
            "exercises": exercises,
        }
