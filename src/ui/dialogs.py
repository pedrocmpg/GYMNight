"""
ui/dialogs.py
Diálogos modais: CreateWorkoutDialog com autocomplete de exercícios.
"""
from __future__ import annotations
import unicodedata

import qtawesome as qta
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QCompleter, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListView, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

from engine import NormalizationEngine
from src.ui.theme import C_BORDER, C_CARD, C_CARD2, C_GREEN, C_TEXT, C_TEXT2, label, separator, RADIUS_MD, RADIUS_LG
from src.ui.titlebar import build_dialog_titlebar


def _norm(text: str) -> str:
    """Lowercase + remove acentos."""
    nfd = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------------------
# FramelessDialog — base para todos os diálogos sem borda nativa
# ---------------------------------------------------------------------------

class FramelessDialog(QDialog):
    """
    QDialog sem borda nativa com titlebar customizada (drag + botão fechar).
    Todos os diálogos do app devem herdar desta classe.
    """

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Titlebar com drag + botão fechar (centralizado em ui/titlebar.py)
        root.addWidget(build_dialog_titlebar(self, title))

        # Área de conteúdo
        self._content_w = QWidget()
        self._content_w.setStyleSheet(
            "background: #0f0f0f;"
            f"border-bottom-left-radius: {RADIUS_LG}px;"
            f"border-bottom-right-radius: {RADIUS_LG}px;"
        )
        self._content_lay = QVBoxLayout(self._content_w)
        self._content_lay.setContentsMargins(24, 20, 24, 24)
        self._content_lay.setSpacing(16)
        root.addWidget(self._content_w)

        self.setStyleSheet(
            f"QDialog {{ border: 1px solid {C_BORDER}; border-radius: {RADIUS_LG}px; }}"
        )

    def content_layout(self) -> QVBoxLayout:
        return self._content_lay


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
                border-radius: {RADIUS_MD}px;
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

class CreateWorkoutDialog(FramelessDialog):
    def __init__(self, norm: NormalizationEngine, parent=None):
        super().__init__("CRIAR TREINO", parent)
        self._norm = norm
        self._ex_widgets: list[dict] = []
        self._day_buttons: list[QPushButton] = []
        self.setMinimumWidth(500)
        self.setMaximumHeight(700)
        
        # Force background color
        self.setStyleSheet("background-color: #0f0f0f;")
        self._build()

    def _build(self):
        lay = self.content_layout()

        # Título com espaçamento generoso
        title_label = label("CRIAR TREINO", "h2")
        lay.addWidget(title_label)
        lay.addSpacing(20)
        lay.addWidget(label("Monte seu treino personalizado com exercícios, séries e repetições.", "sub"))
        lay.addWidget(separator())
        lay.addSpacing(24)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: #0f0f0f; border: none; }")
        form_w = QWidget()
        form_w.setStyleSheet("background: #0f0f0f;")
        self._form_lay = QVBoxLayout(form_w)
        self._form_lay.setSpacing(24)
        scroll.setWidget(form_w)
        lay.addWidget(scroll)

        # ===== NOME DO TREINO - FLOATING INPUT =====
        self._form_lay.addWidget(label("Nome do treino", "h3"))
        self._name = QLineEdit()
        self._name.setPlaceholderText("Ex: Treino D — Ombro")
        self._name.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                border-bottom: 2px solid #333333;
                color: white;
                padding: 10px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border-bottom: 2px solid #39FF14;
            }
        """)
        self._form_lay.addWidget(self._name)
        self._form_lay.addSpacing(20)

        # ===== MÚSCULOS - FLOATING INPUT =====
        self._form_lay.addWidget(label("Músculos", "h3"))
        self._muscles = QLineEdit()
        self._muscles.setPlaceholderText("Ex: Ombro & Trapézio")
        self._muscles.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                border-bottom: 2px solid #333333;
                color: white;
                padding: 10px;
                font-size: 16px;
            }
            QLineEdit:focus {
                border-bottom: 2px solid #39FF14;
            }
        """)
        self._form_lay.addWidget(self._muscles)
        self._form_lay.addSpacing(20)

        # ===== SELEÇÃO DE DIAS - BOTÕES CIRCULARES =====
        self._form_lay.addWidget(label("Dia(s) da Semana", "h3"))
        days_layout = QHBoxLayout()
        days_layout.setSpacing(12)
        
        day_labels = ["S", "T", "Q", "Q", "S", "S", "D"]
        day_names = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
        
        for day_label, day_name in zip(day_labels, day_names):
            day_btn = QPushButton(day_label)
            day_btn.setCheckable(True)
            day_btn.setProperty("day_name", day_name)
            day_btn.setFixedSize(40, 40)
            day_btn.setStyleSheet("""
                QPushButton {
                    width: 40px;
                    height: 40px;
                    border-radius: 20px;
                    border: 1px solid #333333;
                    color: #888888;
                    background: transparent;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    border: 1px solid #555555;
                }
                QPushButton:checked {
                    background: #000000;
                    border: 2px solid #39FF14;
                    color: #39FF14;
                }
            """)
            self._day_buttons.append(day_btn)
            days_layout.addWidget(day_btn)
        
        days_layout.addStretch()
        self._form_lay.addLayout(days_layout)
        self._form_lay.addSpacing(20)

        # ===== EXERCÍCIOS =====
        self._form_lay.addWidget(label("Exercícios", "h3"))
        self._ex_container = QVBoxLayout()
        self._ex_container.setSpacing(10)
        self._form_lay.addLayout(self._ex_container)
        self._add_exercise_block()

        add_ex = QPushButton(" Adicionar exercício")
        add_ex.setIcon(qta.icon("fa5s.plus", color=C_TEXT2, options=[{"scale_factor": 0.6}]))
        add_ex.setObjectName("ghost")
        add_ex.clicked.connect(self._add_exercise_block)
        self._form_lay.addWidget(add_ex)

        save = QPushButton(" Salvar Treino")
        save.setIcon(qta.icon("fa5s.save", color="#000000"))
        save.setMinimumHeight(56)
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
        
        # Coleta os dias selecionados dos botões circulares
        selected_days = [btn.property("day_name") for btn in self._day_buttons if btn.isChecked()]
        days_str = ", ".join(selected_days) if selected_days else ""
        
        return {
            "name": self._name.text().strip(),
            "days": days_str,
            "muscles": self._muscles.text().strip(),
            "exercises": exercises,
        }
