"""
engine.py - GYMNight Performance Engine
NormalizationEngine + PerformanceAnalyzer (volume proporcional N:N) + RoutineManager.
"""

from __future__ import annotations

import time
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from database import DatabaseConnection


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

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
        icons = {1: "icons/chest.png", 2: "icons/back.png", 3: "icons/shoulders.png",
                 4: "icons/biceps.png", 5: "icons/triceps.png", 6: "icons/legs.png",
                 7: "icons/abs.png"}
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
    current_volume: float        # volume bruto da sessão atual (peso × reps)
    sma_volume: list[float]      # SMA bruto das últimas N sessões
    historical_avg: float
    delta_pct: float             # (current - avg) / avg * 100
    muscle_volumes: list[MuscleVolumeResult] = field(default_factory=list)  # breakdown muscular


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


# ---------------------------------------------------------------------------
# NormalizationEngine
# ---------------------------------------------------------------------------

class NormalizationEngine:
    """
    Resolve texto livre para canonical_name existente via Jaccard/trigrams.
    Adaptado para exercises sem muscle_group_id (relação N:N).

    Propriedades:
      P1: normalize_text é idempotente
      P2: trigram_similarity é simétrica
      P3: trigram_similarity(s, s) == 1.0
      P7: resolve() nunca retorna matches abaixo do threshold
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def resolve(self, user_input: str, threshold: float = 0.75) -> list[ExerciseMatch]:
        """Retorna matches rankeados por similarity DESC, todos >= threshold."""
        normalized = self._normalize_text(user_input)
        if not normalized:
            return []

        rows = self._db.fetchall("SELECT id, canonical_name, user_input_name FROM exercises")

        matches: list[ExerciseMatch] = []
        for row in rows:
            sim = self._trigram_similarity(normalized, row["canonical_name"])
            if sim >= threshold:
                exercise = self._load_exercise(row["id"], row["canonical_name"], row["user_input_name"])
                matches.append(ExerciseMatch(exercise=exercise, similarity=sim))

        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches

    def get_or_create(self, user_input: str, muscle_contributions: list[tuple[int, float]] | None = None) -> Exercise:
        """
        Retorna exercício existente (match exato) ou cria novo.
        muscle_contributions: lista de (muscle_group_id, contribution) para novos exercícios.
        """
        canonical = self._normalize_text(user_input)

        row = self._db.fetchone(
            "SELECT id, canonical_name, user_input_name FROM exercises WHERE canonical_name = ?",
            (canonical,),
        )

        if row:
            return self._load_exercise(row["id"], row["canonical_name"], row["user_input_name"])

        # Cria novo exercício
        new_id = self._db.execute_write(
            "INSERT INTO exercises (canonical_name, user_input_name) VALUES (?, ?)",
            (canonical, user_input.strip()),
        )

        # Insere mapeamento muscular se fornecido
        if muscle_contributions:
            self._db.execute_many(
                "INSERT OR IGNORE INTO exercise_muscle_map (exercise_id, muscle_group_id, contribution) VALUES (?, ?, ?)",
                [(new_id, mg_id, contrib) for mg_id, contrib in muscle_contributions],
            )

        return self._load_exercise(new_id, canonical, user_input.strip())

    def _load_exercise(self, exercise_id: int, canonical_name: str, user_input_name: str) -> Exercise:
        """Carrega Exercise com lista de MuscleContribution do mapa N:N."""
        muscle_rows = self._db.fetchall(
            """
            SELECT emm.muscle_group_id, mg.name AS muscle_group_name, emm.contribution
            FROM exercise_muscle_map emm
            JOIN muscle_groups mg ON emm.muscle_group_id = mg.id
            WHERE emm.exercise_id = ?
            ORDER BY emm.contribution DESC
            """,
            (exercise_id,),
        )
        muscles = [
            MuscleContribution(
                muscle_group_id=r["muscle_group_id"],
                muscle_group_name=r["muscle_group_name"],
                contribution=r["contribution"],
            )
            for r in muscle_rows
        ]
        return Exercise(
            id=exercise_id,
            canonical_name=canonical_name,
            user_input_name=user_input_name,
            muscles=muscles,
        )

    # ------------------------------------------------------------------
    # Algoritmos internos
    # ------------------------------------------------------------------

    def _normalize_text(self, text: str) -> str:
        """Lowercase + remove acentos (NFD) + strip. Idempotente [P1]."""
        nfd = unicodedata.normalize("NFD", text.lower().strip())
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

    def _trigram_similarity(self, a: str, b: str) -> float:
        """Jaccard sobre trigrams. Simétrica [P2], sim(s,s)==1.0 [P3]."""
        set_a = self._trigrams(a)
        set_b = self._trigrams(b)
        union = set_a | set_b
        if not union:
            return 0.0
        return len(set_a & set_b) / len(union)

    @staticmethod
    def _trigrams(text: str) -> set[str]:
        if len(text) < 3:
            return {text[i:i + 2] for i in range(len(text) - 1)} if len(text) >= 2 else {text}
        return {text[i:i + 3] for i in range(len(text) - 2)}


# ---------------------------------------------------------------------------
# RoutineManager
# ---------------------------------------------------------------------------

class RoutineManager:
    """Gerencia rotinas: criação, listagem, consulta e encerramento de sessão."""

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db
        self._norm = NormalizationEngine(db)

    def create_routine(self, name: str, exercise_ids: list[int]) -> Routine:
        routine_id = self._db.execute_write(
            "INSERT INTO routines (name) VALUES (?)", (name.strip(),)
        )
        self._db.execute_many(
            "INSERT INTO routine_exercises (routine_id, exercise_id, order_index) VALUES (?, ?, ?)",
            [(routine_id, ex_id, idx) for idx, ex_id in enumerate(exercise_ids)],
        )
        row = self._db.fetchone("SELECT id, name, created_at FROM routines WHERE id = ?", (routine_id,))
        return Routine(id=row["id"], name=row["name"], created_at=row["created_at"])

    def list_routines(self) -> list[Routine]:
        rows = self._db.fetchall("SELECT id, name, created_at FROM routines ORDER BY name")
        return [Routine(id=r["id"], name=r["name"], created_at=r["created_at"]) for r in rows]

    def get_routine_exercises(self, routine_id: int) -> list[Exercise]:
        rows = self._db.fetchall(
            """
            SELECT e.id, e.canonical_name, e.user_input_name
            FROM routine_exercises re
            JOIN exercises e ON re.exercise_id = e.id
            WHERE re.routine_id = ?
            ORDER BY re.order_index ASC
            """,
            (routine_id,),
        )
        return [
            self._norm._load_exercise(r["id"], r["canonical_name"], r["user_input_name"])
            for r in rows
        ]

    def update_routine_template(self, routine_id: int, new_exercise_ids: list[int]) -> None:
        """Substitui exercícios da rotina atomicamente (DELETE + INSERT)."""
        with self._db._conn:
            self._db._conn.execute(
                "DELETE FROM routine_exercises WHERE routine_id = ?", (routine_id,)
            )
            self._db._conn.executemany(
                "INSERT INTO routine_exercises (routine_id, exercise_id, order_index) VALUES (?, ?, ?)",
                [(routine_id, ex_id, idx) for idx, ex_id in enumerate(new_exercise_ids)],
            )

    def end_session(self, session_id: int) -> int:
        """Calcula e persiste duration_seconds. Retorna a duração."""
        row = self._db.fetchone(
            "SELECT started_at FROM workout_sessions WHERE id = ?", (session_id,)
        )
        if not row:
            return 0
        duration = int(time.time()) - row["started_at"]
        self._db.execute_write(
            "UPDATE workout_sessions SET duration_seconds = ? WHERE id = ?",
            (duration, session_id),
        )
        return duration


# ---------------------------------------------------------------------------
# PerformanceAnalyzer (QObject – roda em QThread separado)
# ---------------------------------------------------------------------------

class PerformanceAnalyzer(QObject):
    """
    Worker para análise de performance com volume proporcional por músculo.
    Deve ser movido para QThread via moveToThread().

    Volume muscular = peso * reps * contribution  (N:N)
    SMA exclui a sessão atual para média puramente histórica.
    """

    analysis_complete = Signal(int, object)  # (exercise_id, PerformanceResult)

    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__()
        self._db = db

    def analyze(self, exercise_id: int, session_id: int, window_n: int = 5) -> None:
        """Calcula performance e emite analysis_complete."""
        result = self._compute_performance_delta(exercise_id, session_id, window_n)
        self.analysis_complete.emit(exercise_id, result)

    def get_last_performance(self, exercise_id: int) -> LastPerformance | None:
        """Retorna peso e reps da série mais recente — Ghost Value para a UI."""
        row = self._db.fetchone(
            """
            SELECT exercise_id, session_id, weight_kg, reps, timestamp
            FROM workout_logs
            WHERE exercise_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (exercise_id,),
        )
        if not row:
            return None
        return LastPerformance(
            exercise_id=row["exercise_id"],
            weight_kg=float(row["weight_kg"]),
            reps=int(row["reps"]),
            session_id=row["session_id"],
            timestamp=row["timestamp"],
        )

    def get_muscle_volume_breakdown(self, session_id: int) -> list[MuscleVolumeResult]:
        """
        Retorna o volume proporcional por grupo muscular para uma sessão inteira.
        Usa a view session_muscle_volume (peso * reps * contribution).
        """
        rows = self._db.fetchall(
            """
            SELECT smv.muscle_group_id, mg.name AS muscle_group_name,
                   SUM(smv.muscle_volume) AS total_volume
            FROM session_muscle_volume smv
            JOIN muscle_groups mg ON smv.muscle_group_id = mg.id
            WHERE smv.session_id = ?
            GROUP BY smv.muscle_group_id
            ORDER BY total_volume DESC
            """,
            (session_id,),
        )
        return [
            MuscleVolumeResult(
                muscle_group_id=r["muscle_group_id"],
                muscle_group_name=r["muscle_group_name"],
                volume=float(r["total_volume"]),
            )
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Algoritmos internos
    # ------------------------------------------------------------------

    def _compute_sma_volume(
        self, exercise_id: int, n: int, exclude_session_id: int | None = None
    ) -> list[float]:
        """
        SMA bruto (peso * reps) das últimas N sessões, mais antigo → recente.
        exclude_session_id: exclui sessão atual para média puramente histórica.
        Postcondition: todos os valores >= 0  [P4]
        """
        if exclude_session_id is not None:
            rows = self._db.fetchall(
                """
                SELECT volume FROM session_volume
                WHERE exercise_id = ? AND session_id != ?
                ORDER BY session_ts DESC LIMIT ?
                """,
                (exercise_id, exclude_session_id, n),
            )
        else:
            rows = self._db.fetchall(
                """
                SELECT volume FROM session_volume
                WHERE exercise_id = ?
                ORDER BY session_ts DESC LIMIT ?
                """,
                (exercise_id, n),
            )
        volumes = [float(r["volume"]) for r in rows]
        volumes.reverse()
        return volumes

    def _compute_current_volume(self, exercise_id: int, session_id: int) -> float:
        """Volume bruto da sessão atual para o exercício."""
        row = self._db.fetchone(
            """
            SELECT COALESCE(SUM(weight_kg * reps), 0.0) AS volume
            FROM workout_logs WHERE exercise_id = ? AND session_id = ?
            """,
            (exercise_id, session_id),
        )
        return float(row["volume"]) if row else 0.0

    def _compute_muscle_volumes_current(
        self, exercise_id: int, session_id: int
    ) -> list[MuscleVolumeResult]:
        """
        Volume proporcional por músculo da sessão atual.
        Volume = peso * reps * contribution  (N:N)
        """
        rows = self._db.fetchall(
            """
            SELECT emm.muscle_group_id, mg.name AS muscle_group_name,
                   SUM(wl.weight_kg * wl.reps * emm.contribution) AS muscle_volume
            FROM workout_logs wl
            JOIN exercise_muscle_map emm ON wl.exercise_id = emm.exercise_id
            JOIN muscle_groups mg ON emm.muscle_group_id = mg.id
            WHERE wl.exercise_id = ? AND wl.session_id = ?
            GROUP BY emm.muscle_group_id
            ORDER BY muscle_volume DESC
            """,
            (exercise_id, session_id),
        )
        return [
            MuscleVolumeResult(
                muscle_group_id=r["muscle_group_id"],
                muscle_group_name=r["muscle_group_name"],
                volume=float(r["muscle_volume"]),
            )
            for r in rows
        ]

    def _compute_performance_delta(
        self, exercise_id: int, session_id: int, n: int
    ) -> PerformanceResult:
        """
        Delta entre volume atual e SMA histórico.
        Sessão atual excluída do SMA (correção do bug).
        Se histórico vazio: delta_pct = 0.0  [P8]
        """
        current_volume = self._compute_current_volume(exercise_id, session_id)
        sma_volumes    = self._compute_sma_volume(exercise_id, n, exclude_session_id=session_id)
        muscle_volumes = self._compute_muscle_volumes_current(exercise_id, session_id)

        if not sma_volumes:
            historical_avg = 0.0
            delta_pct = 0.0
        else:
            historical_avg = sum(sma_volumes) / len(sma_volumes)
            delta_pct = (
                (current_volume - historical_avg) / historical_avg * 100
                if historical_avg > 0 else 0.0
            )

        return PerformanceResult(
            exercise_id=exercise_id,
            current_volume=current_volume,
            sma_volume=sma_volumes,
            historical_avg=historical_avg,
            delta_pct=delta_pct,
            muscle_volumes=muscle_volumes,
        )
