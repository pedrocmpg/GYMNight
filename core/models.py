"""
core/models.py
QAbstractTableModel para exercícios e entrada de treino.
"""
from __future__ import annotations
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QMutex, QMutexLocker, QPersistentModelIndex, Qt, QTimer, Signal
from PySide6.QtGui import QIcon

from database import DatabaseConnection
from engine import Exercise, LastPerformance, NormalizationEngine, PerformanceAnalyzer, PerformanceResult

# ---------------------------------------------------------------------------
# Roles e constantes
# ---------------------------------------------------------------------------

SuggestionRole = Qt.UserRole + 1
ExerciseRole   = Qt.UserRole + 2

COL_EXERCISE = 0
COL_WEIGHT   = 1
COL_REPS     = 2
COL_SET_TYPE = 3
COL_SET_NUM  = 4
WE_COLUMNS   = 5

# Tipos de série
SET_TYPES = [
    ("N", "Normal"),
    ("W", "Aquecimento"),
    ("D", "Dropset"),
    ("F", "Falha"),
]
SET_TYPE_LABELS = {code: f"[{code}] {name}" for code, name in SET_TYPES}

EX_COL_NAME   = 0
EX_COL_MUSCLE = 1
EX_COLUMNS    = 2


# ---------------------------------------------------------------------------
# ExerciseModel — read-only, thread-safe
# ---------------------------------------------------------------------------

class ExerciseModel(QAbstractTableModel):
    def __init__(self, db: DatabaseConnection, parent=None):
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

    def refresh_from_db(self):
        rows = self._db.fetchall("SELECT id, canonical_name, user_input_name FROM exercises ORDER BY canonical_name")
        new_data = [self._norm._load_exercise(r["id"], r["canonical_name"], r["user_input_name"]) for r in rows]
        self.beginResetModel()
        with QMutexLocker(self._mutex): self._data = new_data
        self.endResetModel()

    def add_exercise(self, exercise: Exercise):
        with QMutexLocker(self._mutex): pos = len(self._data)
        self.beginInsertRows(QModelIndex(), pos, pos)
        with QMutexLocker(self._mutex): self._data.append(exercise)
        self.endInsertRows()

    def _on_analysis_complete(self, exercise_id: int, result: PerformanceResult):
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
# WorkoutEntryModel — editável, pré-populado
# ---------------------------------------------------------------------------

class WorkoutEntryModel(QAbstractTableModel):
    set_committed = Signal(int, int)
    HEADERS = ("Exercício", "Peso (kg)", "Reps", "Tipo", "Série")

    def __init__(self, db: DatabaseConnection, session_id: int,
                 analyzer: PerformanceAnalyzer | None = None,
                 exercises: list[Exercise] | None = None, parent=None):
        super().__init__(parent)
        self._db         = db
        self._session_id = session_id
        self._analyzer   = analyzer
        self._rows: list[dict] = []
        self._suggestion_cache: dict[int, LastPerformance | None] = {}
        if exercises:
            self._prepopulate(exercises)

    def _prepopulate(self, exercises: list[Exercise]):
        self.beginInsertRows(QModelIndex(), 0, len(exercises) - 1)
        for ex in exercises:
            self._rows.append({"exercise_id": ex.id, "exercise_name": ex.canonical_name,
                                "weight_kg": None, "reps": None, "set_type": "N", "set_number": 1})
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
            if col == COL_SET_TYPE:
                code = row.get("set_type", "N")
                return SET_TYPE_LABELS.get(code, code)
            if col == COL_SET_NUM:  return row.get("set_number")
        if role == Qt.UserRole: return row
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
        if index.column() in (COL_EXERCISE, COL_WEIGHT, COL_REPS, COL_SET_TYPE):
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
        elif col == COL_SET_TYPE:
            # Aceita código direto ("N","W","D","F") ou label completo
            code = value if value in ("N", "W", "D", "F") else "N"
            self._rows[index.row()]["set_type"] = code
        else:
            return False
        if self._is_row_complete(index.row()):
            if not self._commit_set(index.row()): return False
        self.dataChanged.emit(index, index, [Qt.EditRole])
        return True

    def insertRow(self, row: int, parent=QModelIndex()) -> bool:
        self.beginInsertRows(parent, row, row)
        self._rows.insert(row, {"exercise_id": None, "exercise_name": None,
                                 "weight_kg": None, "reps": None,
                                 "set_type": "N",
                                 "set_number": len(self._rows) + 1})
        self.endInsertRows()
        return True

    def set_exercise(self, row: int, exercise: Exercise):
        if 0 <= row < len(self._rows):
            self._rows[row]["exercise_id"]   = exercise.id
            self._rows[row]["exercise_name"] = exercise.canonical_name
            self._suggestion_cache.pop(exercise.id, None)
            idx = self.index(row, COL_EXERCISE)
            self.dataChanged.emit(idx, idx, [Qt.DisplayRole, SuggestionRole])

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

    def _is_row_complete(self, row: int) -> bool:
        r = self._rows[row]
        return r.get("exercise_id") is not None and r.get("weight_kg") is not None and r.get("reps") is not None

    def _commit_set(self, row: int) -> bool:
        r = self._rows[row]
        try:
            self._db.execute_write(
                "INSERT INTO workout_logs (exercise_id, session_id, weight_kg, reps, set_type) VALUES (?,?,?,?,?)",
                (r["exercise_id"], self._session_id, r["weight_kg"], r["reps"], r.get("set_type", "N")),
            )
            self.set_committed.emit(r["exercise_id"], self._session_id)
            return True
        except Exception:
            return False
