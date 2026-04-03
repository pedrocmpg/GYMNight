"""
models.py - GYMNight Performance Engine
WorkoutEntryModel + ExerciseModel + ExerciseSearchDelegate (busca estilo Google).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QMutex,
    QMutexLocker,
    QPersistentModelIndex,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCompleter,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QWidget,
)

from database import DatabaseConnection
from engine import (
    Exercise,
    LastPerformance,
    NormalizationEngine,
    PerformanceAnalyzer,
    PerformanceResult,
)

# ---------------------------------------------------------------------------
# Custom Roles
# ---------------------------------------------------------------------------

SuggestionRole = Qt.UserRole + 1   # LastPerformance (Ghost Value)
ExerciseRole   = Qt.UserRole + 2   # Exercise dataclass completo

# ---------------------------------------------------------------------------
# Constantes de colunas — WorkoutEntryModel
# ---------------------------------------------------------------------------

COL_EXERCISE = 0
COL_WEIGHT   = 1
COL_REPS     = 2
COL_SET_NUM  = 3
WE_COLUMNS   = 4

# Constantes de colunas — ExerciseModel
EX_COL_NAME   = 0
EX_COL_MUSCLE = 1
EX_COLUMNS    = 2

# Ordem dos grupos musculares para os cabeçalhos da lista suspensa
MUSCLE_GROUP_ORDER = [
    (1, "PEITO"),
    (2, "COSTAS"),
    (3, "OMBROS"),
    (4, "BÍCEPS"),
    (5, "TRÍCEPS"),
    (6, "PERNAS"),
    (7, "ABDÔMEN"),
]


# ---------------------------------------------------------------------------
# ExerciseSearchPopup — lista suspensa com cabeçalhos por grupo muscular
# ---------------------------------------------------------------------------

class ExerciseSearchPopup(QListWidget):
    """
    Lista flutuante que exibe exercícios agrupados por músculo primário.
    Filtra em tempo real via NormalizationEngine (trigrams).
    """

    exercise_chosen = Signal(object)  # Exercise

    # Cores
    _HEADER_BG    = QColor("#0d0d0d")
    _HEADER_FG    = QColor("#39FF14")
    _ITEM_BG      = QColor("#111111")
    _ITEM_FG      = QColor("#cccccc")
    _ITEM_SEL_BG  = QColor("#1a2e1a")
    _ITEM_SEL_FG  = QColor("#39FF14")

    def __init__(self, norm: NormalizationEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._norm = norm
        self._all_exercises: list[Exercise] = []

        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setFocusPolicy(Qt.NoFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("""
            QListWidget {
                background: #111111;
                border: 1px solid #39FF14;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item { padding: 5px 10px; color: #cccccc; }
            QListWidget::item:selected { background: #1a2e1a; color: #39FF14; }
        """)
        self.itemClicked.connect(self._on_item_clicked)
        self._load_all()

    def _load_all(self) -> None:
        """Carrega todos os exercícios do banco uma vez."""
        rows = self._norm._db.fetchall(
            "SELECT id, canonical_name, user_input_name FROM exercises ORDER BY canonical_name"
        )
        self._all_exercises = [
            self._norm._load_exercise(r["id"], r["canonical_name"], r["user_input_name"])
            for r in rows
        ]

    def refresh_exercises(self) -> None:
        """Recarrega a lista (chamar após seed ou criação de novo exercício)."""
        self._load_all()

    def show_filtered(self, query: str, anchor: QWidget, width: int) -> None:
        """Filtra e exibe a lista abaixo do widget âncora."""
        self.clear()

        if query.strip():
            matches = self._norm.resolve(query, threshold=0.25)
            exercises = [m.exercise for m in matches[:30]]
        else:
            exercises = self._all_exercises[:60]

        if not exercises:
            self.hide()
            return

        # Agrupa por músculo primário
        groups: dict[int, list[Exercise]] = {}
        ungrouped: list[Exercise] = []
        for ex in exercises:
            pm = ex.primary_muscle
            if pm:
                groups.setdefault(pm.muscle_group_id, []).append(ex)
            else:
                ungrouped.append(ex)

        # Insere na ordem definida
        added = 0
        for mg_id, mg_label in MUSCLE_GROUP_ORDER:
            exs = groups.get(mg_id, [])
            if not exs:
                continue
            # Cabeçalho do grupo
            header = QListWidgetItem(f"── {mg_label} ──")
            header.setFlags(Qt.NoItemFlags)
            header.setForeground(self._HEADER_FG)
            header.setBackground(self._HEADER_BG)
            font = QFont("Consolas", 9)
            font.setBold(True)
            header.setFont(font)
            self.addItem(header)
            for ex in exs:
                item = QListWidgetItem(f"  {ex.canonical_name}")
                item.setData(Qt.UserRole, ex)
                item.setForeground(self._ITEM_FG)
                item.setBackground(self._ITEM_BG)
                self.addItem(item)
                added += 1

        for ex in ungrouped:
            item = QListWidgetItem(f"  {ex.canonical_name}")
            item.setData(Qt.UserRole, ex)
            self.addItem(item)
            added += 1

        if added == 0:
            self.hide()
            return

        # Posiciona abaixo do âncora
        pos = anchor.mapToGlobal(anchor.rect().bottomLeft())
        self.setFixedWidth(width)
        max_h = min(320, self.sizeHintForRow(0) * (self.count() + 1) + 8)
        self.setFixedHeight(max_h)
        self.move(pos)
        self.show()
        self.raise_()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        ex = item.data(Qt.UserRole)
        if ex is not None:
            self.exercise_chosen.emit(ex)
            self.hide()

    def keyPressEvent(self, event) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            item = self.currentItem()
            if item:
                self._on_item_clicked(item)
        elif event.key() == Qt.Key_Escape:
            self.hide()
        else:
            super().keyPressEvent(event)


# ---------------------------------------------------------------------------
# ExerciseSearchDelegate — delegate para COL_EXERCISE
# ---------------------------------------------------------------------------

class ExerciseSearchDelegate(QStyledItemDelegate):
    """
    Delegate para a coluna Exercício do WorkoutEntryModel.
    Cria um QLineEdit com popup de busca fuzzy ao entrar em modo de edição.
    Ao confirmar, pula o foco para COL_WEIGHT da mesma linha.
    """

    exercise_committed = Signal(int, object)  # (row, Exercise)

    def __init__(self, norm: NormalizationEngine, table_view, parent=None) -> None:
        super().__init__(parent)
        self._norm  = norm
        self._view  = table_view
        self._popup = ExerciseSearchPopup(norm)
        self._current_editor: QLineEdit | None = None
        self._current_index: QModelIndex | None = None
        self._popup.exercise_chosen.connect(self._on_exercise_chosen)

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        editor = QLineEdit(parent)
        editor.setStyleSheet("""
            QLineEdit {
                background: #1a1a1a;
                color: #e0e0e0;
                border: 1px solid #39FF14;
                border-radius: 3px;
                padding: 4px 8px;
                font-family: Consolas;
                font-size: 13px;
            }
        """)
        editor.setPlaceholderText("Digite para buscar...")
        self._current_editor = editor
        self._current_index  = QPersistentModelIndex(index)

        # Filtra em tempo real com debounce de 120ms
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(120)
        self._timer.timeout.connect(self._do_search)
        editor.textChanged.connect(lambda _: self._timer.start())

        # Mostra lista completa ao abrir
        QTimer.singleShot(0, self._do_search)
        return editor

    def _do_search(self) -> None:
        if self._current_editor is None:
            return
        query = self._current_editor.text()
        self._popup.show_filtered(
            query,
            anchor=self._current_editor,
            width=max(self._current_editor.width(), 320),
        )

    def _on_exercise_chosen(self, exercise: Exercise) -> None:
        if self._current_index is None:
            return
        row = self._current_index.row()
        # Atualiza o modelo diretamente
        model = self._view.model()
        if model and hasattr(model, "set_exercise"):
            model.set_exercise(row, exercise)

        # Fecha editor e pula para COL_WEIGHT
        self._popup.hide()
        if self._current_editor:
            self._current_editor.setText(exercise.canonical_name)
        self.commitData.emit(self._current_editor)
        self.closeEditor.emit(self._current_editor, QStyledItemDelegate.NoHint)

        # Foco automático para coluna de Peso na mesma linha
        QTimer.singleShot(0, lambda: self._jump_to_weight(row))

    def _jump_to_weight(self, row: int) -> None:
        model = self._view.model()
        if model is None:
            return
        weight_index = model.index(row, COL_WEIGHT)
        self._view.setCurrentIndex(weight_index)
        self._view.edit(weight_index)

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        val = index.data(Qt.DisplayRole)
        if isinstance(editor, QLineEdit):
            editor.setText(val or "")

    def setModelData(self, editor: QWidget, model, index: QModelIndex) -> None:
        # O modelo já foi atualizado via set_exercise — não faz nada aqui
        pass

    def destroyEditor(self, editor: QWidget, index: QModelIndex) -> None:
        self._popup.hide()
        self._current_editor = None
        super().destroyEditor(editor, index)


# ---------------------------------------------------------------------------
# GhostValueDelegate — exibe sugestão em cinza quando célula está vazia
# ---------------------------------------------------------------------------

class GhostValueDelegate(QStyledItemDelegate):
    """Mostra o último peso/reps em cinza itálico quando a célula está vazia."""

    GHOST_COLOR = QColor("#444444")

    def paint(self, painter, option, index: QModelIndex) -> None:
        value = index.data(Qt.DisplayRole)
        if value is not None:
            super().paint(painter, option, index)
            return

        suggestion = index.data(SuggestionRole)
        if suggestion is None:
            super().paint(painter, option, index)
            return

        col = index.column()
        ghost_text = (
            f"{suggestion.weight_kg:.1f}" if col == COL_WEIGHT
            else str(suggestion.reps) if col == COL_REPS
            else None
        )
        if ghost_text is None:
            super().paint(painter, option, index)
            return

        self.initStyleOption(option, index)
        painter.save()
        if option.state & option.state.Selected:
            painter.fillRect(option.rect, QColor("#1a2e1a"))
        painter.setPen(self.GHOST_COLOR)
        font = painter.font()
        font.setItalic(True)
        painter.setFont(font)
        painter.drawText(option.rect.adjusted(6, 0, -6, 0), Qt.AlignVCenter | Qt.AlignLeft, ghost_text)
        painter.restore()


# ---------------------------------------------------------------------------
# ExerciseModel — Read-Only, Thread-Safe
# ---------------------------------------------------------------------------

class ExerciseModel(QAbstractTableModel):
    """Modelo read-only para listagem de exercícios. Thread-safe via QMutex."""

    def __init__(self, db: DatabaseConnection, parent=None) -> None:
        super().__init__(parent)
        self._db    = db
        self._norm  = NormalizationEngine(db)
        self._mutex = QMutex()
        self._data: list[Exercise] = []
        self._performance_cache: dict[int, PerformanceResult] = {}
        self._icon_cache: dict[str, QIcon] = {}
        self.refresh_from_db()

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid(): return 0
        with QMutexLocker(self._mutex): return len(self._data)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else EX_COLUMNS

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid(): return None
        with QMutexLocker(self._mutex):
            if index.row() >= len(self._data): return None
            ex = self._data[index.row()]
        if role == Qt.DisplayRole:
            return ex.canonical_name if index.column() == EX_COL_NAME else ex.muscle_group_name
        if role == Qt.DecorationRole and index.column() == EX_COL_NAME:
            return self._get_icon(ex.icon_path)
        if role == Qt.UserRole:
            return ex
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole) -> Any:
        if role != Qt.DisplayRole or orientation != Qt.Horizontal: return None
        return ("Exercício", "Grupo Muscular")[section] if section < EX_COLUMNS else None

    def flags(self, index):
        if not index.isValid(): return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def refresh_from_db(self) -> None:
        rows = self._db.fetchall("SELECT id, canonical_name, user_input_name FROM exercises ORDER BY canonical_name")
        new_data = [self._norm._load_exercise(r["id"], r["canonical_name"], r["user_input_name"]) for r in rows]
        self.beginResetModel()
        with QMutexLocker(self._mutex): self._data = new_data
        self.endResetModel()

    def add_exercise(self, exercise: Exercise) -> None:
        with QMutexLocker(self._mutex): pos = len(self._data)
        self.beginInsertRows(QModelIndex(), pos, pos)
        with QMutexLocker(self._mutex): self._data.append(exercise)
        self.endInsertRows()

    def _on_analysis_complete(self, exercise_id: int, result: PerformanceResult) -> None:
        with QMutexLocker(self._mutex):
            row = next((i for i, ex in enumerate(self._data) if ex.id == exercise_id), -1)
        if row == -1: return
        self._performance_cache[exercise_id] = result
        self.dataChanged.emit(self.index(row, 0), self.index(row, self.columnCount() - 1), [Qt.UserRole])

    def _get_icon(self, icon_path: str) -> QIcon:
        if icon_path not in self._icon_cache:
            self._icon_cache[icon_path] = QIcon(icon_path)
        return self._icon_cache[icon_path]


# ---------------------------------------------------------------------------
# WorkoutEntryModel — Editable, pré-populado
# ---------------------------------------------------------------------------

class WorkoutEntryModel(QAbstractTableModel):
    """
    Modelo editável para séries/reps/peso.
    COL_EXERCISE: gerenciado pelo ExerciseSearchDelegate (não editável via setData padrão).
    COL_WEIGHT / COL_REPS: editáveis com validação de tipo.
    """

    set_committed = Signal(int, int)  # (exercise_id, session_id)

    HEADERS = ("Exercício", "Peso (kg)", "Reps", "Série")

    def __init__(
        self,
        db: DatabaseConnection,
        session_id: int,
        analyzer: PerformanceAnalyzer | None = None,
        exercises: list[Exercise] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db         = db
        self._session_id = session_id
        self._analyzer   = analyzer
        self._rows: list[dict] = []
        self._suggestion_cache: dict[int, LastPerformance | None] = {}
        if exercises:
            self._prepopulate(exercises)

    def _prepopulate(self, exercises: list[Exercise]) -> None:
        self.beginInsertRows(QModelIndex(), 0, len(exercises) - 1)
        for ex in exercises:
            self._rows.append({
                "exercise_id": ex.id, "exercise_name": ex.canonical_name,
                "weight_kg": None, "reps": None, "set_number": 1,
            })
        self.endInsertRows()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else WE_COLUMNS

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._rows): return None
        row = self._rows[index.row()]
        col = index.column()

        if role in (Qt.DisplayRole, Qt.EditRole):
            if col == COL_EXERCISE: return row.get("exercise_name") or ""
            if col == COL_WEIGHT:   return row.get("weight_kg")
            if col == COL_REPS:     return row.get("reps")
            if col == COL_SET_NUM:  return row.get("set_number")

        if role == Qt.UserRole:
            return row

        if role == SuggestionRole:
            ex_id = row.get("exercise_id")
            if ex_id is None: return None
            if ex_id not in self._suggestion_cache:
                self._suggestion_cache[ex_id] = (
                    self._analyzer.get_last_performance(ex_id) if self._analyzer else None
                )
            return self._suggestion_cache[ex_id]

        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section] if section < WE_COLUMNS else None
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid(): return Qt.NoItemFlags
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() in (COL_EXERCISE, COL_WEIGHT, COL_REPS):
            return base | Qt.ItemIsEditable
        return base

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not index.isValid() or role != Qt.EditRole: return False
        col = index.column()

        if col == COL_WEIGHT:
            v = self._validate_weight(value)
            if v is None: return False
            self._rows[index.row()]["weight_kg"] = v
        elif col == COL_REPS:
            v = self._validate_reps(value)
            if v is None: return False
            self._rows[index.row()]["reps"] = v
        else:
            return False

        if self._is_row_complete(index.row()):
            if not self._commit_set(index.row()): return False

        self.dataChanged.emit(index, index, [Qt.EditRole])
        return True

    def insertRow(self, row: int, parent=QModelIndex()) -> bool:
        self.beginInsertRows(parent, row, row)
        self._rows.insert(row, {
            "exercise_id": None, "exercise_name": None,
            "weight_kg": None, "reps": None,
            "set_number": len(self._rows) + 1,
        })
        self.endInsertRows()
        return True

    def set_exercise(self, row: int, exercise: Exercise) -> None:
        """Chamado pelo delegate após seleção no popup."""
        if 0 <= row < len(self._rows):
            self._rows[row]["exercise_id"]   = exercise.id
            self._rows[row]["exercise_name"] = exercise.canonical_name
            self._suggestion_cache.pop(exercise.id, None)
            idx = self.index(row, COL_EXERCISE)
            self.dataChanged.emit(idx, idx, [Qt.DisplayRole, SuggestionRole])

    # ------------------------------------------------------------------
    # Validação
    # ------------------------------------------------------------------

    def _validate_weight(self, value: Any) -> float | None:
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None
        return round(v, 2) if 0 < v <= 999.9 else None

    def _validate_reps(self, value: Any) -> int | None:
        try:
            if isinstance(value, str) and "." in value:
                f = float(value)
                if f != int(f): return None
                value = int(f)
            v = int(value)
        except (TypeError, ValueError):
            return None
        return v if 1 <= v <= 999 else None

    # ------------------------------------------------------------------
    # Commit
    # ------------------------------------------------------------------

    def _is_row_complete(self, row: int) -> bool:
        r = self._rows[row]
        return r.get("exercise_id") is not None and r.get("weight_kg") is not None and r.get("reps") is not None

    def _commit_set(self, row: int) -> bool:
        r = self._rows[row]
        try:
            self._db.execute_write(
                "INSERT INTO workout_logs (exercise_id, session_id, weight_kg, reps) VALUES (?, ?, ?, ?)",
                (r["exercise_id"], self._session_id, r["weight_kg"], r["reps"]),
            )
            self.set_committed.emit(r["exercise_id"], self._session_id)
            return True
        except Exception:
            return False
