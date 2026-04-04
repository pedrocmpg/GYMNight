"""
models.py
Re-export de core/models.py para compatibilidade.
"""
from core.models import (
    SuggestionRole,
    ExerciseRole,
    COL_EXERCISE,
    COL_WEIGHT,
    COL_REPS,
    COL_SET_TYPE,
    COL_SET_NUM,
    WE_COLUMNS,
    SET_TYPES,
    SET_TYPE_LABELS,
    EX_COL_NAME,
    EX_COL_MUSCLE,
    EX_COLUMNS,
    ExerciseModel,
    WorkoutEntryModel,
)

__all__ = [
    "SuggestionRole", "ExerciseRole",
    "COL_EXERCISE", "COL_WEIGHT", "COL_REPS", "COL_SET_TYPE", "COL_SET_NUM", "WE_COLUMNS",
    "SET_TYPES", "SET_TYPE_LABELS",
    "EX_COL_NAME", "EX_COL_MUSCLE", "EX_COLUMNS",
    "ExerciseModel", "WorkoutEntryModel",
]
