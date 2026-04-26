"""
Core data models for GYMNight
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MuscleGroup:
    id: int
    name: str
    icon_path: str


@dataclass
class MuscleContribution:
    """Contribuição de um grupo muscular em um exercício."""
    muscle_group_id: int
    muscle_group_name: str
    contribution: float  # 0.0 – 1.0


@dataclass
class Exercise:
    id: int
    canonical_name: str
    user_input_name: str
    # Sem muscle_group_id — relação N:N via exercise_muscle_map
    muscles: list[MuscleContribution] = field(default_factory=list)

    @property
    def primary_muscle(self) -> MuscleContribution | None:
        """Retorna o músculo com maior contribuição (para ícone/display)."""
        return max(self.muscles, key=lambda m: m.contribution, default=None)

    @property
    def muscle_group_name(self) -> str:
        pm = self.primary_muscle
        return pm.muscle_group_name if pm else ""

    @property
    def icon_path(self) -> str:
        pm = self.primary_muscle
        if pm is None:
            return ""
        icons = {
            1: "assets/icons/chest.png",
            2: "assets/icons/back.png",
            3: "assets/icons/shoulders.png",
            4: "assets/icons/biceps.png",
            5: "assets/icons/triceps.png",
            6: "assets/icons/legs.png",
            7: "assets/icons/abs.png",
        }
        return icons.get(pm.muscle_group_id, "")


@dataclass
class ExerciseMatch:
    exercise: Exercise
    similarity: float  # 0.0 – 1.0


@dataclass
class WorkoutSet:
    id: int
    exercise_id: int
    session_id: int
    weight_kg: float
    reps: int
    timestamp: datetime


@dataclass
class MuscleVolumeResult:
    """Volume proporcional por grupo muscular em uma sessão."""
    muscle_group_id: int
    muscle_group_name: str
    volume: float  # peso * reps * contribution


@dataclass
class PerformanceResult:
    exercise_id: int
    current_volume: float  # volume bruto da sessão atual (peso × reps)
    sma_volume: list[float]  # SMA bruto das últimas N sessões
    historical_avg: float
    delta_pct: float  # (current - avg) / avg * 100
    muscle_volumes: list[MuscleVolumeResult] = field(default_factory=list)


@dataclass
class Routine:
    id: int
    name: str
    created_at: int


@dataclass
class LastPerformance:
    """Último peso e reps registrados — Ghost Value para a UI."""
    exercise_id: int
    weight_kg: float
    reps: int
    session_id: int
    timestamp: int
