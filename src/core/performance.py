"""
Performance analysis and tracking
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from src.core.models import LastPerformance, MuscleVolumeResult, PerformanceResult


class PerformanceAnalyzer(QObject):
    """
    Worker para análise de performance com volume proporcional por músculo.
    Deve ser movido para QThread via moveToThread().

    Volume muscular = peso * reps * contribution  (N:N)
    SMA exclui a sessão atual para média puramente histórica.
    """

    analysis_complete = Signal(int, object)  # (exercise_id, PerformanceResult)

    def __init__(self, db) -> None:
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
        sma_volumes = self._compute_sma_volume(exercise_id, n, exclude_session_id=session_id)
        muscle_volumes = self._compute_muscle_volumes_current(exercise_id, session_id)

        if not sma_volumes:
            historical_avg = 0.0
            delta_pct = 0.0
        else:
            historical_avg = sum(sma_volumes) / len(sma_volumes)
            delta_pct = (
                (current_volume - historical_avg) / historical_avg * 100 if historical_avg > 0 else 0.0
            )

        return PerformanceResult(
            exercise_id=exercise_id,
            current_volume=current_volume,
            sma_volume=sma_volumes,
            historical_avg=historical_avg,
            delta_pct=delta_pct,
            muscle_volumes=muscle_volumes,
        )
