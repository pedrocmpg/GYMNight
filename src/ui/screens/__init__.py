"""
UI Screens module
"""
from src.ui.screens.dashboard import DashboardTab
from src.ui.screens.statistics import StatisticsTab
from src.ui.screens.workouts import WorkoutsTab
from src.ui.screens.setup import SetupScreen
from src.ui.screens.active_workout import ActiveWorkoutScreen

__all__ = [
    "DashboardTab",
    "StatisticsTab",
    "WorkoutsTab",
    "SetupScreen",
    "ActiveWorkoutScreen",
]
