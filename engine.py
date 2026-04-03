"""
engine.py - GYMNight Performance Engine
NormalizationEngine + PerformanceAnalyzer + RoutineManager.
"""

from __future__ import annotations

import time
import unicodedata
from dataclasses import dataclass
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
class Exercise:
    id: int
    canonical_name: str
    user_input_name: str
    muscle_group_id: int
    muscle_group_name: str
    icon_path: str


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
class PerformanceResult:
    exercise_id: int
    current_volume: float    # peso × reps × séries da sessão atual
    sma_volume: list[float]  # volumes das últimas N sessões (mais antigo → recente)
    historical_avg: float
    delta_pct: float         # (current - avg) / avg * 100


@dataclass
class Routine:
    id: int
    name: str
    created_at: int  # unixepoch


@dataclass
class LastPerformance:
    """Último peso e reps registrados para um exercício — usado como Ghost Value na UI."""
    exercise_id: int
    weight_kg: float
    reps: int
    session_id: int
    timestamp: int  # unixepoch


# ---------------------------------------------------------------------------
# NormalizationEngine
# ---------------------------------------------------------------------------

class NormalizationEngine:
    """
    Resolve texto livre do usuário para um canonical_name existente
    usando Fuzzy Search com similaridade Jaccard sobre trigrams.

    Propriedades garantidas:
      P1: normalize_text é idempotente
      P2: trigram_similarity é simétrica
      P3: trigram_similarity(s, s) == 1.0
      P7: resolve() nunca retorna matches abaixo do threshold
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def resolve(self, user_input: str, threshold: float = 0.75) -> list[ExerciseMatch]:
        """
        Retorna lista de ExerciseMatch ordenada por similarity DESC,
        filtrando apenas itens com similarity >= threshold.
        Não muta o banco de dados.
        """
        normalized = self._normalize_text(user_input)
        if not normalized:
            return []

        rows = self._db.fetchall(
            """
            SELECT e.id, e.canonical_name, e.user_input_name, e.muscle_group_id,
                   mg.name AS muscle_group_name, mg.icon_path
            FROM exercises e
            JOIN muscle_groups mg ON e.muscle_group_id = mg.id
            """,
        )

        matches: list[ExerciseMatch] = []
        for row in rows:
            sim = self._trigram_similarity(normalized, row["canonical_name"])
            if sim >= threshold:
                exercise = Exercise(
                    id=row["id"],
                    canonical_name=row["canonical_name"],
                    user_input_name=row["user_input_name"],
                    muscle_group_id=row["muscle_group_id"],
                    muscle_group_name=row["muscle_group_name"],
                    icon_path=row["icon_path"],
                )
                matches.append(ExerciseMatch(exercise=exercise, similarity=sim))

        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches

    def get_or_create(self, user_input: str, muscle_group_id: int) -> Exercise:
        """
        Retorna exercício existente (match exato no canonical_name)
        ou cria novo registro normalizado.
        """
        canonical = self._normalize_text(user_input)

        row = self._db.fetchone(
            """
            SELECT e.id, e.canonical_name, e.user_input_name, e.muscle_group_id,
                   mg.name AS muscle_group_name, mg.icon_path
            FROM exercises e
            JOIN muscle_groups mg ON e.muscle_group_id = mg.id
            WHERE e.canonical_name = ?
            """,
            (canonical,),
        )

        if row:
            return Exercise(
                id=row["id"],
                canonical_name=row["canonical_name"],
                user_input_name=row["user_input_name"],
                muscle_group_id=row["muscle_group_id"],
                muscle_group_name=row["muscle_group_name"],
                icon_path=row["icon_path"],
            )

        new_id = self._db.execute_write(
            "INSERT INTO exercises (canonical_name, user_input_name, muscle_group_id) VALUES (?, ?, ?)",
            (canonical, user_input.strip(), muscle_group_id),
        )

        mg_row = self._db.fetchone(
            "SELECT name, icon_path FROM muscle_groups WHERE id = ?",
            (muscle_group_id,),
        )

        return Exercise(
            id=new_id,
            canonical_name=canonical,
            user_input_name=user_input.strip(),
            muscle_group_id=muscle_group_id,
            muscle_group_name=mg_row["name"] if mg_row else "",
            icon_path=mg_row["icon_path"] if mg_row else "",
        )

    # ------------------------------------------------------------------
    # Algoritmos internos
    # ------------------------------------------------------------------

    def _normalize_text(self, text: str) -> str:
        """Lowercase + remove acentos (NFD) + strip. Idempotente [P1]."""
        nfd = unicodedata.normalize("NFD", text.lower().strip())
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

    def _trigram_similarity(self, a: str, b: str) -> float:
        """Jaccard similarity sobre trigrams. Simétrica [P2], sim(s,s)==1.0 [P3]."""
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
    """
    Gerencia rotinas (templates de treino): criação, listagem e consulta.
    Todas as operações são síncronas — chamadas do main thread ou de workers.
    """

    def __init__(self, db: DatabaseConnection) -> None:
        self._db = db

    def create_routine(self, name: str, exercise_ids: list[int]) -> Routine:
        """
        Cria uma nova rotina com os exercícios na ordem fornecida.
        Retorna o objeto Routine criado.
        """
        routine_id = self._db.execute_write(
            "INSERT INTO routines (name) VALUES (?)",
            (name.strip(),),
        )
        self._db.execute_many(
            "INSERT INTO routine_exercises (routine_id, exercise_id, order_index) VALUES (?, ?, ?)",
            [(routine_id, ex_id, idx) for idx, ex_id in enumerate(exercise_ids)],
        )
        row = self._db.fetchone("SELECT id, name, created_at FROM routines WHERE id = ?", (routine_id,))
        return Routine(id=row["id"], name=row["name"], created_at=row["created_at"])

    def list_routines(self) -> list[Routine]:
        """Retorna todas as rotinas ordenadas por nome."""
        rows = self._db.fetchall("SELECT id, name, created_at FROM routines ORDER BY name")
        return [Routine(id=r["id"], name=r["name"], created_at=r["created_at"]) for r in rows]

    def get_routine_exercises(self, routine_id: int) -> list[Exercise]:
        """
        Retorna os exercícios de uma rotina na ordem definida (order_index ASC).
        """
        rows = self._db.fetchall(
            """
            SELECT e.id, e.canonical_name, e.user_input_name, e.muscle_group_id,
                   mg.name AS muscle_group_name, mg.icon_path
            FROM routine_exercises re
            JOIN exercises e  ON re.exercise_id  = e.id
            JOIN muscle_groups mg ON e.muscle_group_id = mg.id
            WHERE re.routine_id = ?
            ORDER BY re.order_index ASC
            """,
            (routine_id,),
        )
        return [
            Exercise(
                id=r["id"],
                canonical_name=r["canonical_name"],
                user_input_name=r["user_input_name"],
                muscle_group_id=r["muscle_group_id"],
                muscle_group_name=r["muscle_group_name"],
                icon_path=r["icon_path"],
            )
            for r in rows
        ]

    def update_routine_template(self, routine_id: int, new_exercise_ids: list[int]) -> None:
        """
        Substitui os exercícios de uma rotina existente.
        Permite que o usuário salve permanentemente as mudanças feitas no treino de hoje.
        Operação atômica: DELETE + INSERT em uma única transação via execute_many.
        """
        # Remove exercícios antigos e insere os novos em transação única
        with self._db._conn:
            self._db._conn.execute(
                "DELETE FROM routine_exercises WHERE routine_id = ?",
                (routine_id,),
            )
            self._db._conn.executemany(
                "INSERT INTO routine_exercises (routine_id, exercise_id, order_index) VALUES (?, ?, ?)",
                [(routine_id, ex_id, idx) for idx, ex_id in enumerate(new_exercise_ids)],
            )

    def end_session(self, session_id: int) -> int:
        """
        Calcula duration_seconds = now - started_at e persiste na sessão.
        Retorna a duração em segundos.
        """
        row = self._db.fetchone(
            "SELECT started_at FROM workout_sessions WHERE id = ?",
            (session_id,),
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
    Worker que executa queries de agregação (SMA) sem bloquear a UI.
    Deve ser movido para um QThread via moveToThread() antes de usar.

    Signal analysis_complete é entregue no main thread via Qt.AutoConnection.
    """

    analysis_complete = Signal(int, object)  # (exercise_id, PerformanceResult)

    def __init__(self, db: DatabaseConnection) -> None:
        super().__init__()
        self._db = db

    def analyze(self, exercise_id: int, session_id: int, window_n: int = 5) -> None:
        """Calcula volume atual e SMA histórico. Emite analysis_complete ao terminar."""
        result = self._compute_performance_delta(exercise_id, session_id, window_n)
        self.analysis_complete.emit(exercise_id, result)

    def get_last_performance(self, exercise_id: int) -> LastPerformance | None:
        """
        Retorna o peso e reps da série mais recente do exercício.
        Usado como Ghost Value (sugestão) na UI.
        """
        row = self._db.fetchone(
            """
            SELECT id, exercise_id, session_id, weight_kg, reps, timestamp
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

    # ------------------------------------------------------------------
    # Algoritmos internos
    # ------------------------------------------------------------------

    def _compute_sma_volume(
        self, exercise_id: int, n: int, exclude_session_id: int | None = None
    ) -> list[float]:
        """
        Retorna volumes das últimas N sessões (mais antigo → recente).
        exclude_session_id: ignora essa sessão para que a média seja puramente histórica.
        Postcondition: todos os valores >= 0  [P4]
        """
        if exclude_session_id is not None:
            rows = self._db.fetchall(
                """
                SELECT volume
                FROM session_volume
                WHERE exercise_id = ? AND session_id != ?
                ORDER BY session_ts DESC
                LIMIT ?
                """,
                (exercise_id, exclude_session_id, n),
            )
        else:
            rows = self._db.fetchall(
                """
                SELECT volume
                FROM session_volume
                WHERE exercise_id = ?
                ORDER BY session_ts DESC
                LIMIT ?
                """,
                (exercise_id, n),
            )

        volumes = [float(row["volume"]) for row in rows]
        volumes.reverse()  # mais antigo primeiro para plotagem
        return volumes

    def _compute_current_volume(self, exercise_id: int, session_id: int) -> float:
        row = self._db.fetchone(
            """
            SELECT COALESCE(SUM(weight_kg * reps), 0.0) AS volume
            FROM workout_logs
            WHERE exercise_id = ? AND session_id = ?
            """,
            (exercise_id, session_id),
        )
        return float(row["volume"]) if row else 0.0

    def _compute_performance_delta(
        self, exercise_id: int, session_id: int, n: int
    ) -> PerformanceResult:
        """
        Delta entre volume atual e média histórica (SMA).
        A sessão atual é excluída do SMA para média puramente histórica.
        Se histórico vazio: delta_pct = 0.0  [P8]
        """
        current_volume = self._compute_current_volume(exercise_id, session_id)
        # Exclui a sessão atual do histórico — correção do bug do SMA
        sma_volumes = self._compute_sma_volume(exercise_id, n, exclude_session_id=session_id)

        if not sma_volumes:
            historical_avg = 0.0
            delta_pct = 0.0
        else:
            historical_avg = sum(sma_volumes) / len(sma_volumes)
            delta_pct = (
                (current_volume - historical_avg) / historical_avg * 100
                if historical_avg > 0
                else 0.0
            )

        return PerformanceResult(
            exercise_id=exercise_id,
            current_volume=current_volume,
            sma_volume=sma_volumes,
            historical_avg=historical_avg,
            delta_pct=delta_pct,
        )
