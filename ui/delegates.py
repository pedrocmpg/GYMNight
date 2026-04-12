"""
ui/delegates.py
Delegates para a QTableView do WorkoutEntryModel:
- ExerciseSearchDelegate: QCompleter com QSortFilterProxyModel (MatchContains, sem acentos)
- GhostValueDelegate: ghost value em cinza nas colunas Peso/Reps
- SetTypeDelegate: dropdown de tipo de série
"""
from __future__ import annotations
import unicodedata

from PySide6.QtCore import (
    QModelIndex, QPersistentModelIndex, QSortFilterProxyModel,
    QStringListModel, Qt, QTimer, Signal,
)
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QComboBox, QCompleter, QLineEdit, QListView,
    QStyledItemDelegate, QStyleOptionViewItem, QWidget,
)

from engine import Exercise, NormalizationEngine
from core.models import COL_EXERCISE, COL_WEIGHT, COL_REPS, COL_SET_TYPE, SuggestionRole, SET_TYPES
from ui.theme import C_GREEN, C_CARD, C_CARD2, C_BORDER, C_BG, C_TEXT, C_TEXT2, C_TEXT3, RADIUS_SM, RADIUS_MD


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_accents(text: str) -> str:
    """Remove acentos e converte para lowercase — idêntico ao NormalizationEngine."""
    nfd = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------------------
# ExerciseFilterModel — QSortFilterProxyModel com MatchContains sem acentos
# ---------------------------------------------------------------------------

class ExerciseFilterModel(QSortFilterProxyModel):
    """
    Filtra a lista de exercícios por substring, case-insensitive e sem acentos.
    Cada item do source model armazena:
      Qt.DisplayRole  → "nome do exercício [Grupo Muscular]"
      Qt.UserRole     → Exercise dataclass
      Qt.UserRole+10  → canonical_name normalizado (sem acentos, lowercase)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._query_norm = ""

    def set_query(self, query: str):
        self._query_norm = _strip_accents(query)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if not self._query_norm:
            return True
        idx = self.sourceModel().index(source_row, 0, source_parent)
        norm_name: str = self.sourceModel().data(idx, Qt.UserRole + 10) or ""
        return self._query_norm in norm_name


# ---------------------------------------------------------------------------
# ExerciseCompleterModel — QStringListModel estendido com dados de exercício
# ---------------------------------------------------------------------------

class ExerciseCompleterModel(QSortFilterProxyModel):
    """Source model que mantém a lista completa de exercícios."""

    def __init__(self, exercises: list[Exercise], parent=None):
        from PySide6.QtGui import QStandardItemModel, QStandardItem
        super().__init__(parent)
        self._source = QStandardItemModel(parent)
        for ex in exercises:
            item = QStandardItem()
            muscle = ex.muscle_group_name or "—"
            item.setText(f"{ex.canonical_name.title()}  [{muscle}]")
            item.setData(ex, Qt.UserRole)
            item.setData(_strip_accents(ex.canonical_name), Qt.UserRole + 10)
            self._source.appendRow(item)
        self.setSourceModel(self._source)

    def set_query(self, query: str):
        norm = _strip_accents(query)
        self.setFilterRole(Qt.UserRole + 10)
        self.setFilterFixedString(norm)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        idx = self.sourceModel().index(source_row, 0, source_parent)
        norm_name: str = self.sourceModel().data(idx, Qt.UserRole + 10) or ""
        return self._filter_str in norm_name if hasattr(self, "_filter_str") else True

    def set_filter(self, query: str):
        self._filter_str = _strip_accents(query)
        self.invalidateFilter()


# ---------------------------------------------------------------------------
# ExerciseSearchDelegate — QCompleter com popup estilizado
# ---------------------------------------------------------------------------

class ExerciseSearchDelegate(QStyledItemDelegate):
    """
    Delegate para COL_EXERCISE.

    Comportamento:
    - Ao entrar na célula, abre QLineEdit com QCompleter
    - Filtra por substring (MatchContains), case-insensitive, sem acentos
    - Exibe "nome [Grupo Muscular]" na lista
    - Não auto-seleciona — só confirma ao clicar ou pressionar Enter
    - Ao confirmar, pula foco para COL_WEIGHT da mesma linha
    """

    def __init__(self, norm: NormalizationEngine, table_view, parent=None):
        super().__init__(parent)
        self._norm  = norm
        self._view  = table_view
        self._editor: QLineEdit | None = None
        self._index:  QPersistentModelIndex | None = None
        self._exercises: list[Exercise] = []
        self._filter_model: ExerciseCompleterModel | None = None
        self._load_exercises()

    def _load_exercises(self):
        """Carrega todos os exercícios do banco uma vez."""
        rows = self._norm._db.fetchall(
            "SELECT id, canonical_name, user_input_name FROM exercises ORDER BY canonical_name"
        )
        self._exercises = [
            self._norm._load_exercise(r["id"], r["canonical_name"], r["user_input_name"])
            for r in rows
        ]

    def _build_completer(self, editor: QLineEdit) -> QCompleter:
        """Constrói o QCompleter com modelo filtrado e popup estilizado."""
        from PySide6.QtGui import QStandardItemModel, QStandardItem

        # Source model com todos os exercícios
        source = QStandardItemModel()
        for ex in self._exercises:
            item = QStandardItem()
            muscle = ex.muscle_group_name or "—"
            display = f"{ex.canonical_name.title()}  [{muscle}]"
            item.setText(display)
            item.setData(ex, Qt.UserRole)
            item.setData(_strip_accents(ex.canonical_name), Qt.UserRole + 10)
            source.appendRow(item)

        # Proxy model para filtro por substring sem acentos
        proxy = ExerciseFilterModel()
        proxy.setSourceModel(source)

        completer = QCompleter(proxy, editor)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setMaxVisibleItems(12)

        # Estilo do popup
        popup = QListView()
        popup.setStyleSheet(f"""
            QListView {{
                background: {C_CARD};
                border: 1px solid {C_GREEN};
                border-radius: {RADIUS_MD}px;
                outline: none;
                font-size: 13px;
            }}
            QListView::item {{
                padding: 7px 14px;
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
        completer.setPopup(popup)

        # Armazena referência ao proxy para atualizar o filtro
        editor._proxy = proxy

        # Conecta: ao ativar um item, confirma o exercício
        completer.activated[QModelIndex].connect(
            lambda idx: self._on_activated(idx, proxy)
        )

        return completer

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        editor = QLineEdit(parent)
        editor.setStyleSheet(
            f"QLineEdit {{ background:{C_CARD}; color:{C_TEXT};"
            f" border:1px solid {C_GREEN}; border-radius:{RADIUS_SM}px;"
            " padding:4px 10px; font-size:13px; }}"
        )
        editor.setPlaceholderText("Digite para buscar...")
        self._editor = editor
        self._index  = QPersistentModelIndex(index)

        completer = self._build_completer(editor)
        editor.setCompleter(completer)

        # Atualiza o filtro do proxy a cada keystroke (sem debounce — QCompleter já é reativo)
        editor.textChanged.connect(self._on_text_changed)
        editor.installEventFilter(self)

        return editor

    def _on_text_changed(self, text: str):
        if self._editor and hasattr(self._editor, "_proxy"):
            self._editor._proxy.set_filter(text)

    def _on_activated(self, proxy_index: QModelIndex, proxy: ExerciseFilterModel):
        """Chamado quando o usuário clica ou pressiona Enter em um item do popup."""
        source_index = proxy.mapToSource(proxy_index)
        ex: Exercise = proxy.sourceModel().data(source_index, Qt.UserRole)
        if ex is None:
            return
        self._confirm_exercise(ex)

    def _confirm_exercise(self, exercise: Exercise):
        if self._index is None:
            return
        row = self._index.row()
        model = self._view.model()
        if model and hasattr(model, "set_exercise"):
            model.set_exercise(row, exercise)
        if self._editor:
            # Bloqueia signals para não re-disparar o filtro
            self._editor.blockSignals(True)
            self._editor.setText(exercise.canonical_name.title())
            self._editor.blockSignals(False)
        self.commitData.emit(self._editor)
        self.closeEditor.emit(self._editor, QStyledItemDelegate.NoHint)
        QTimer.singleShot(0, lambda: self._jump_to_weight(row))

    def _jump_to_weight(self, row: int):
        model = self._view.model()
        if model:
            idx = model.index(row, COL_WEIGHT)
            self._view.setCurrentIndex(idx)
            self._view.edit(idx)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self._editor and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape:
                if self._editor and self._editor.completer():
                    self._editor.completer().popup().hide()
                self.closeEditor.emit(self._editor, QStyledItemDelegate.NoHint)
                return True
        return super().eventFilter(obj, event)

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        val = index.data(Qt.DisplayRole)
        if isinstance(editor, QLineEdit):
            editor.blockSignals(True)
            editor.setText(val or "")
            editor.selectAll()
            editor.blockSignals(False)

    def setModelData(self, editor, model, index):
        pass  # modelo atualizado via set_exercise

    def destroyEditor(self, editor: QWidget, index: QModelIndex):
        if isinstance(editor, QLineEdit) and editor.completer():
            editor.completer().popup().hide()
        self._editor = None
        super().destroyEditor(editor, index)


# ---------------------------------------------------------------------------
# GhostValueDelegate
# ---------------------------------------------------------------------------

class GhostValueDelegate(QStyledItemDelegate):
    """Exibe último peso/reps em cinza itálico quando a célula está vazia."""

    GHOST_COLOR = QColor("#555555")

    def paint(self, painter, option, index: QModelIndex):
        value = index.data(Qt.DisplayRole)
        if value is not None:
            super().paint(painter, option, index)
            return
        suggestion = index.data(SuggestionRole)
        if suggestion is None:
            super().paint(painter, option, index)
            return
        col = index.column()
        ghost = (
            f"{suggestion.weight_kg:.1f}" if col == COL_WEIGHT
            else str(suggestion.reps) if col == COL_REPS
            else None
        )
        if ghost is None:
            super().paint(painter, option, index)
            return
        self.initStyleOption(option, index)
        painter.save()
        if option.state & option.state.Selected:
            painter.fillRect(option.rect, QColor("#1a2e1a"))
        painter.setPen(self.GHOST_COLOR)
        f = painter.font()
        f.setItalic(True)
        painter.setFont(f)
        painter.drawText(option.rect.adjusted(6, 0, -6, 0), Qt.AlignVCenter | Qt.AlignLeft, ghost)
        painter.restore()


# ---------------------------------------------------------------------------
# SetTypeDelegate — dropdown de tipo de série com cores
# ---------------------------------------------------------------------------

_SET_TYPE_COLORS = {
    "N": "#9ca3af",
    "W": "#60a5fa",
    "D": "#f97316",
    "F": "#ef4444",
}


class SetTypeDelegate(QStyledItemDelegate):
    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        combo = QComboBox(parent)
        combo.setStyleSheet(f"""
            QComboBox {{
                background:{C_CARD}; color:#e0e0e0;
                border:1px solid {C_GREEN}; border-radius:{RADIUS_SM}px;
                padding:4px 8px; font-size:12px; font-weight:600;
            }}
            QComboBox QAbstractItemView {{
                background:{C_CARD}; color:#e0e0e0;
                selection-background-color:#1a2e1a; selection-color:{C_GREEN};
                border:1px solid {C_BORDER};
            }}
        """)
        for code, name in SET_TYPES:
            combo.addItem(f"[{code}] {name}", userData=code)
        return combo

    def setEditorData(self, editor: QWidget, index: QModelIndex):
        if isinstance(editor, QComboBox):
            current = index.data(Qt.EditRole) or "[N] Normal"
            code = current[1] if current.startswith("[") and len(current) > 1 else current
            for i in range(editor.count()):
                if editor.itemData(i) == code:
                    editor.setCurrentIndex(i)
                    break

    def setModelData(self, editor: QWidget, model, index: QModelIndex):
        if isinstance(editor, QComboBox):
            model.setData(index, editor.currentData(), Qt.EditRole)

    def paint(self, painter, option, index: QModelIndex):
        value = index.data(Qt.DisplayRole) or "[N] Normal"
        code  = value[1] if value.startswith("[") and len(value) > 1 else "N"
        color = _SET_TYPE_COLORS.get(code, "#9ca3af")
        self.initStyleOption(option, index)
        painter.save()
        painter.fillRect(option.rect, QColor("#1a2e1a" if option.state & option.state.Selected else C_CARD))
        painter.setPen(QColor(color))
        f = painter.font()
        f.setBold(True)
        f.setPointSize(10)
        painter.setFont(f)
        painter.drawText(option.rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, value)
        painter.restore()

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)
