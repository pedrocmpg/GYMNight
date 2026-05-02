"""
ui/dialogs.py
Diálogos modais: CreateWorkoutDialog com autocomplete de exercícios.
"""
from __future__ import annotations
import unicodedata

import qtawesome as qta
from PySide6.QtCore import Qt, QPoint, QTimer, QEvent
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget, QCheckBox,
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
    Campo de texto com popup de busca de exercícios.
    - Filtra por substring (busca "rem" encontra "remada")
    - Exibe "nome [Grupo Muscular]" na lista
    - Popup abre ao digitar qualquer caractere
    - Opcionalmente filtra apenas exercícios com valores MET
    """

    def __init__(self, norm: NormalizationEngine, parent=None, filter_met: bool = False):
        super().__init__(parent)
        self._norm = norm
        self._filter_met = filter_met
        self._popup = None  # Será criado quando necessário
        self.setPlaceholderText("Digite para buscar exercício...")
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            QLineEdit {{
                background: {C_CARD2};
                color: {C_TEXT};
                border: 2px solid {C_BORDER};
                border-radius: {RADIUS_MD}px;
                padding: 10px 14px;
                font-size: 14px;
            }}
            QLineEdit:focus {{ border-color: {C_GREEN}; }}
        """)
        
        self.textChanged.connect(self._on_text_changed)

    def _ensure_popup(self):
        """Cria o popup se ainda não existir."""
        if self._popup is not None:
            return
        
        # Popup de resultados - agora como widget normal, não ToolTip
        self._popup = QListWidget(self.parent())
        self._popup.setMaximumHeight(250)
        self._popup.setStyleSheet(f"""
            QListWidget {{
                background: #1e1e1e;
                border: 2px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                font-size: 14px;
            }}
            QListWidget::item {{ padding: 10px 14px; color: {C_TEXT2}; }}
            QListWidget::item:hover {{ background: #2a2a2a; color: {C_TEXT}; }}
            QListWidget::item:selected {{ background: #1a2e1a; color: {C_GREEN}; }}
        """)
        self._popup.hide()
        self._popup.itemClicked.connect(self._on_popup_click)
        
        # Adiciona o popup ao layout do parent
        if self.parent() and hasattr(self.parent(), 'layout') and self.parent().layout():
            parent_layout = self.parent().layout()
            # Encontra o índice deste widget no layout
            for i in range(parent_layout.count()):
                item = parent_layout.itemAt(i)
                if item and item.widget() == self:
                    # Insere o popup logo após este widget
                    parent_layout.insertWidget(i + 1, self._popup)
                    break

    def _get_exercises_with_met(self) -> set[int]:
        """Retorna conjunto de IDs de exercícios que possuem valores MET parametrizados."""
        rows = self._norm._db.fetchall("SELECT exercise_id FROM exercise_met_values")
        return {row["exercise_id"] for row in rows}

    def _on_text_changed(self, text: str):
        """Atualiza o popup conforme o usuário digita."""
        if not text.strip():
            if self._popup:
                self._popup.hide()
            return
        
        # Garante que o popup existe
        self._ensure_popup()
        
        # Busca direta no banco usando LIKE (case-insensitive)
        search_pattern = f"%{text.lower()}%"
        
        # Query SQL com LIKE para busca por substring
        if self._filter_met:
            # Busca apenas exercícios com MET
            rows = self._norm._db.fetchall("""
                SELECT e.id, e.canonical_name, e.user_input_name
                FROM exercises e
                JOIN exercise_met_values m ON e.id = m.exercise_id
                WHERE LOWER(e.canonical_name) LIKE ?
                ORDER BY e.canonical_name
                LIMIT 20
            """, (search_pattern,))
        else:
            # Busca todos os exercícios
            rows = self._norm._db.fetchall("""
                SELECT e.id, e.canonical_name, e.user_input_name
                FROM exercises e
                WHERE LOWER(e.canonical_name) LIKE ?
                ORDER BY e.canonical_name
                LIMIT 20
            """, (search_pattern,))
        
        if not rows:
            self._popup.hide()
            return
        
        # Busca exercícios com MET para indicador visual
        met_exercises = self._get_exercises_with_met()
            
        self._popup.clear()
        for row in rows:
            ex = self._norm._load_exercise(row["id"], row["canonical_name"], row["user_input_name"])
            # Adiciona indicador visual de MET
            met_indicator = " 🔥" if ex.id in met_exercises else ""
            item = QListWidgetItem(f"{ex.canonical_name.title()}  [{ex.muscle_group_name}]{met_indicator}")
            item.setData(Qt.UserRole, ex.canonical_name)
            self._popup.addItem(item)
        
        # Calcula tamanho do popup
        row_h = self._popup.sizeHintForRow(0) if self._popup.count() > 0 else 30
        self._popup.setFixedHeight(min(250, row_h * min(self._popup.count(), 8) + 8))
        self._popup.show()

    def _on_popup_click(self, item: QListWidgetItem):
        """Quando o usuário clica em um item do popup."""
        canonical_name = item.data(Qt.UserRole)
        if canonical_name:
            self.blockSignals(True)
            self.setText(canonical_name.title())
            self.blockSignals(False)
        if self._popup:
            self._popup.hide()

    def focusOutEvent(self, event):
        """Esconde o popup quando o campo perde o foco."""
        # Pequeno delay para permitir clique no popup
        if self._popup:
            QTimer.singleShot(200, self._popup.hide)
        super().focusOutEvent(event)


# ---------------------------------------------------------------------------
# CreateWorkoutDialog
# ---------------------------------------------------------------------------

class CreateWorkoutDialog(FramelessDialog):
    def __init__(self, norm: NormalizationEngine, parent=None):
        super().__init__("CRIAR TREINO", parent)
        self._norm = norm
        self._ex_widgets: list[dict] = []
        self._day_buttons: list[QPushButton] = []
        self._filter_met = True  # Filtro ativado por padrão
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
        
        # Checkbox para filtrar apenas exercícios com MET
        self._filter_met_checkbox = QCheckBox("Mostrar apenas exercícios com cálculo de calorias")
        self._filter_met_checkbox.setChecked(self._filter_met)
        self._filter_met_checkbox.setStyleSheet(f"""
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
        self._filter_met_checkbox.stateChanged.connect(self._on_filter_changed)
        self._form_lay.addWidget(self._filter_met_checkbox)
        
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

    def _on_filter_changed(self, state):
        """Atualiza o filtro MET e reconstrói todos os campos de exercício."""
        self._filter_met = self._filter_met_checkbox.isChecked()
        # Reconstrói todos os campos de exercício com o novo filtro
        for w in self._ex_widgets:
            old_text = w["name"].text()
            # Remove o widget antigo
            w["name"].deleteLater()
            # Cria novo widget com filtro atualizado
            new_name_edit = ExerciseLineEdit(self._norm, w["name"].parent(), filter_met=self._filter_met)
            new_name_edit.setText(old_text)
            # Substitui no layout
            layout = w["name"].parent().layout()
            layout.insertWidget(1, new_name_edit)  # Insere após o label
            w["name"] = new_name_edit

    def _add_exercise_block(self):
        idx = len(self._ex_widgets) + 1
        block = QFrame()
        block.setObjectName("card")
        b_lay = QVBoxLayout(block)
        b_lay.setContentsMargins(12, 12, 12, 12)
        b_lay.setSpacing(8)
        b_lay.addWidget(label(f"Exercício {idx}", "sub"))

        # Campo com autocomplete (usa o filtro atual)
        name_edit = ExerciseLineEdit(self._norm, block, filter_met=self._filter_met)
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
