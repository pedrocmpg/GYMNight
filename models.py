"""
Backward compatibility wrapper for models module
"""
from src.ui_models.models import (
    COL_EXERCISE,
    COL_REPS,
    COL_SET_NUM,
    COL_SET_TYPE,
    COL_WEIGHT,
    EX_COL_MUSCLE,
    EX_COL_NAME,
    EX_COLUMNS,
    SET_TYPE_LABELS,
    SET_TYPES,
    WE_COLUMNS,
    ExerciseModel,
    ExerciseRole,
    SuggestionRole,
    WorkoutEntryModel,
)

__all__ = [
    "SuggestionRole",
    "ExerciseRole",
    "COL_EXERCISE",
    "COL_WEIGHT",
    "COL_REPS",
    "COL_SET_TYPE",
    "COL_SET_NUM",
    "WE_COLUMNS",
    "SET_TYPES",
    "SET_TYPE_LABELS",
    "EX_COL_NAME",
    "EX_COL_MUSCLE",
    "EX_COLUMNS",
    "ExerciseModel",
    "WorkoutEntryModel",
]
