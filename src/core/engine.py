"""
GYMNight Performance Engine
Consolidated exports for backward compatibility
"""
from src.core.normalization import NormalizationEngine
from src.core.performance import PerformanceAnalyzer
from src.core.routine import RoutineManager

__all__ = [
    "NormalizationEngine",
    "PerformanceAnalyzer",
    "RoutineManager",
]
