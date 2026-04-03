"""
models.py - GYMNight Performance Engine
ExerciseModel (read-only, thread-safe) + WorkoutEntryModel (editable, validado, pré-populado).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QMutex,
    QMutexLocker,
    Qt,
    Signal,
)
from PySide6.QtGui import QIcon

from database import DatabaseConnection
from engine import Exercise, LastPerformance, PerformanceAnalyzer, PerformanceResult


# ---------------------------------------------------------------------------
# Custom Role
# ---------------------------------------------------------------------------

# Role para retornar o Ghost Value (sugestão de peso/reps da última sessão)
SuggestionRole = Qt.UserRole + 1


# ---------------------------------------------------------------------------
# Constantes de colunas
# ---------------------------------------------------------------------------

# ExerciseModel
EX_COL_NAME   = 0
EX_COL_MUSCLE = 1
EX_COLUMNS    = 2

# WorkoutEntryModel
COL_EXERCISE = 0
COL_WEIGHT   = 1
COL_REPS     = 2
COL_SET_NUM  = 3
WE_COLUMNS   = 4


# ---------------------------------------------------------------------------
# ExerciseModel – Read-Only, Thread-Safe
# ---------------------------------------------------------------------------

class ExerciseModel(QAbstractTableModel):
    """
    Modelo read-only para listagem e seleção de exercícios.

    Roles:
      Qt.DisplayRole    → canonical_name / muscle_group_name
      Qt.DecorationRole → QIcon do grupo muscular
      Qt.UserRole       → Exercise dataclass completo

    Thread-safety: _data protegido por QMutex.
    Updates via dataChanged + beginResetModel/endResetModel.
    """

    def __init__(self, db: DatabaseConnection, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._mutex = QMutex()
        self._data: list[Exercise] = []
        self._performance_cache: dict[int, PerformanceResult] = {}
        self._icon_cache: dict[str, QIcon] = {}
        self.refresh_from_db()

    # ------------------------------------------------------------------
    # QAbstractTableModel interface
    # ------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        with QMutexLocker(self._mutex):
            return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else EX_COLUMNS

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None

        with QMutexLocker(self._mutex):
            if index.row() >= len(self._data):
                return None
            exercise = self._data[index.row()]

        if role == Qt.DisplayRole:
            if index.column() == EX_COL_NAME:
                return exercise.canonical_name
            if index.column() == EX_COL_MUSCLE:
                return exercise.muscle_group_name

        if role == Qt.DecorationRole and index.column() == EX_COL_NAME:
            return self._get_icon(exercise.icon_path)

        if role == Qt.UserRole:
            return exercise

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole,
    ) -> Any:
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        return ("Exercício", "Grupo Muscular")[section] if section < EX_COLUMNS else None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable  # read-only

    # ------------------------------------------------------------------
    # Atualização thread-safe
    # ------------------------------------------------------------------

    def refresh_from_db(self) -> None:
        """
        Recarrega todos os exercícios do banco.
        Seguro para chamar de qualquer thread via QMetaObject.invokeMethod.
        """
        rows = self._db.fetchall(
            """
            SELECT e.id, e.canonical_name, e.user_input_name, e.muscle_group_id,
                   mg.name AS muscle_group_name, mg.icon_path
            FROM exercises e
            JOIN muscle_groups mg ON e.muscle_group_id = mg.id
            ORDER BY e.canonical_name
            """,
        )

        new_data = [
            Exercise(
                id=row["id"],
                canonical_name=row["canonical_name"],
                user_input_name=row["user_input_name"],
                muscle_group_id=row["muscle_group_id"],
                muscle_group_name=row["muscle_group_name"],
                icon_path=row["icon_path"],
            )
            for row in rows
        ]

        self.beginResetModel()
        with QMutexLocker(self._mutex):
            self._data = new_data
        self.endResetModel()

    def add_exercise(self, exercise: Exercise) -> None:
        """Insere exercício no modelo com beginInsertRows/endInsertRows granular."""
        with QMutexLocker(self._mutex):
            insert_pos = len(self._data)

        self.beginInsertRows(QModelIndex(), insert_pos, insert_pos)
        with QMutexLocker(self._mutex):
            self._data.append(exercise)
        self.endInsertRows()

    # ------------------------------------------------------------------
    # Slot: recebe resultado do PerformanceAnalyzer (main thread via AutoConnection)
    # ------------------------------------------------------------------

    def _on_analysis_complete(self, exercise_id: int, result: PerformanceResult) -> None:
        """
        Atualiza cache de performance e emite dataChanged para a linha afetada.
        Sempre executado no main thread (Qt.AutoConnection).
        """
        with QMutexLocker(self._mutex):
            row = next(
                (i for i, ex in enumerate(self._data) if ex.id == exercise_id),
                -1,
            )

        if row == -1:
            return

        self._performance_cache[exercise_id] = result

        top_left     = self.index(row, 0)
        bottom_right = self.index(row, self.columnCount() - 1)
        self.dataChanged.emit(top_left, bottom_right, [Qt.UserRole])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_icon(self, icon_path: str) -> QIcon:
        if icon_path not in self._icon_cache:
            self._icon_cache[icon_path] = QIcon(icon_path)
        return self._icon_cache[icon_path]


# ---------------------------------------------------------------------------
# WorkoutEntryModel – Editable, pré-populado, com SuggestionRole
# ---------------------------------------------------------------------------

class WorkoutEntryModel(QAbstractTableModel):
    """
    Modelo editável para entrada de séries/reps/peso.

    Colunas: exercise_id | weight_kg (float) | reps (int) | set_number (int)

    Funcionalidades:
      - Pré-populado via lista de exercícios de uma rotina no __init__
      - SuggestionRole: retorna LastPerformance como Ghost Value para a UI
      - Validação estrita antes de commit (float/int)
      - Thread-safe no commit via transações do DatabaseConnection

    Propriedades garantidas:
      P5: setData retorna False para tipos inválidos
      P6: dataChanged emitido somente após commit bem-sucedido
    """

    # Emitido após commit bem-sucedido: (exercise_id, session_id)
    set_committed = Signal(int, int)

    HEADERS = ("Exercício ID", "Peso (kg)", "Reps", "Série")

    def __init__(
        self,
        db: DatabaseConnection,
        session_id: int,
        analyzer: PerformanceAnalyzer | None = None,
        exercises: list[Exercise] | None = None,  # pré-popula a partir de uma rotina
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._session_id = session_id
        self._analyzer = analyzer
        self._rows: list[dict] = []
        self._suggestion_cache: dict[int, LastPerformance | None] = {}

        # Pré-popula linhas se uma lista de exercícios foi fornecida (rotina)
        if exercises:
            self._prepopulate(exercises)

    def _prepopulate(self, exercises: list[Exercise]) -> None:
        """Cria uma linha por exercício da rotina, com set_number = 1."""
        self.beginInsertRows(QModelIndex(), 0, len(exercises) - 1)
        for idx, exercise in enumerate(exercises):
            self._rows.append({
                "exercise_id": exercise.id,
                "exercise_name": exercise.canonical_name,
                "weight_kg":   None,
                "reps":        None,
                "set_number":  1,
            })
        self.endInsertRows()

    # ------------------------------------------------------------------
    # QAbstractTableModel interface
    # ------------------------------------------------------------------

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else WE_COLUMNS

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or index.row() >= len(self._rows):
            return None

        row = self._rows[index.row()]

        if role in (Qt.DisplayRole, Qt.EditRole):
            col = index.column()
            if col == COL_EXERCISE:
                return row.get("exercise_name") or row.get("exercise_id")
            if col == COL_WEIGHT:
                return row.get("weight_kg")
            if col == COL_REPS:
                return row.get("reps")
            if col == COL_SET_NUM:
                return row.get("set_number")

        if role == Qt.UserRole:
            return row

        # SuggestionRole: retorna LastPerformance para exibição como texto cinza
        if role == SuggestionRole:
            exercise_id = row.get("exercise_id")
            if exercise_id is None:
                return None
            if exercise_id not in self._suggestion_cache:
                self._suggestion_cache[exercise_id] = (
                    self._analyzer.get_last_performance(exercise_id)
                    if self._analyzer
                    else None
                )
            return self._suggestion_cache[exercise_id]

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole,
    ) -> Any:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section] if section < WE_COLUMNS else None
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() in (COL_WEIGHT, COL_REPS):
            return base | Qt.ItemIsEditable
        return base

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """
        Valida e commita o dado no banco.
        Retorna True somente se validação + commit tiveram sucesso.
        Emite dataChanged apenas após commit bem-sucedido.  [P6]
        """
        if not index.isValid() or role != Qt.EditRole:
            return False

        col = index.column()

        if col == COL_WEIGHT:
            validated = self._validate_weight(value)
            if validated is None:
                return False  # [P5]
            self._rows[index.row()]["weight_kg"] = validated

        elif col == COL_REPS:
            validated = self._validate_reps(value)
            if validated is None:
                return False  # [P5]
            self._rows[index.row()]["reps"] = validated

        else:
            return False

        # Tenta commit se a linha estiver completa
        if self._is_row_complete(index.row()):
            if not self._commit_set(index.row()):
                return False

        self.dataChanged.emit(index, index, [Qt.EditRole])
        return True

    # ------------------------------------------------------------------
    # Inserção de linhas
    # ------------------------------------------------------------------

    def insertRow(self, row: int, parent: QModelIndex = QModelIndex()) -> bool:
        self.beginInsertRows(parent, row, row)
        self._rows.insert(row, {
            "exercise_id":   None,
            "exercise_name": None,
            "weight_kg":     None,
            "reps":          None,
            "set_number":    len(self._rows) + 1,
        })
        self.endInsertRows()
        return True

    def set_exercise(self, row: int, exercise: Exercise) -> None:
        """Define o exercício de uma linha e invalida o cache de sugestão."""
        if 0 <= row < len(self._rows):
            self._rows[row]["exercise_id"]   = exercise.id
            self._rows[row]["exercise_name"] = exercise.canonical_name
            # Invalida cache para forçar nova busca do ghost value
            self._suggestion_cache.pop(exercise.id, None)
            idx = self.index(row, COL_EXERCISE)
            self.dataChanged.emit(idx, idx, [Qt.DisplayRole, SuggestionRole])

    # ------------------------------------------------------------------
    # Validação
    # ------------------------------------------------------------------

    def _validate_weight(self, value: Any) -> float | None:
        """float > 0, máximo 999.9. Retorna None se inválido."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None
        if v <= 0 or v > 999.9:
            return None
        return round(v, 2)

    def _validate_reps(self, value: Any) -> int | None:
        """int >= 1, máximo 999. Rejeita floats não-inteiros (ex: 3.7). [P5]"""
        try:
            if isinstance(value, str) and "." in value:
                f = float(value)
                if f != int(f):
                    return None
                value = int(f)
            v = int(value)
        except (TypeError, ValueError):
            return None
        if v < 1 or v > 999:
            return None
        return v

    # ------------------------------------------------------------------
    # Commit no banco
    # ------------------------------------------------------------------

    def _is_row_complete(self, row: int) -> bool:
        r = self._rows[row]
        return (
            r.get("exercise_id") is not None
            and r.get("weight_kg") is not None
            and r.get("reps") is not None
        )

    def _commit_set(self, row: int) -> bool:
        """
        Insere a série no banco dentro de transação.
        Retorna False e faz rollback em caso de erro.
        """
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
