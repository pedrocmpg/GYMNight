"""
engine.py - GYMNight Performance Engine
NormalizationEngine (Fuzzy Search / Trigrams) + PerformanceAnalyzer (QThread).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QObject, Signal, QThread

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

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

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
        """
        Lowercase + remove acentos (NFD decomposition) + strip.
        Idempotente: normalize(normalize(s)) == normalize(s)  [P1]
        """
        nfd = unicodedata.normalize("NFD", text.lower().strip())
        return "".join(c for c in nfd if unicodedata.category(c) != "Mn")

    def _trigram_similarity(self, a: str, b: str) -> float:
        """
        Jaccard similarity sobre conjuntos de trigrams.
        Simétrica [P2] e trigram_similarity(s, s) == 1.0 [P3].
        """
        set_a = self._trigrams(a)
        set_b = self._trigrams(b)

        union = set_a | set_b
        if not union:
            return 0.0

        intersection = set_a & set_b
        return len(intersection) / len(union)

    @staticmethod
    def _trigrams(text: str) -> set[str]:
        """Gera conjunto de substrings de tamanho 3."""
        if len(text) < 3:
            # Para strings curtas, usa bigramas ou o próprio token
            return {text[i:i + 2] for i in range(len(text) - 1)} if len(text) >= 2 else {text}
        return {text[i:i + 3] for i in range(len(text) - 2)}


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
        """
        Calcula volume atual e SMA histórico para o exercício.
        Emite analysis_complete ao terminar.
        """
        result = self._compute_performance_delta(exercise_id, session_id, window_n)
        self.analysis_complete.emit(exercise_id, result)

    # ------------------------------------------------------------------
    # Algoritmos internos
    # ------------------------------------------------------------------

    def _compute_sma_volume(self, exercise_id: int, n: int) -> list[float]:
        """
        Retorna lista de volumes das últimas N sessões, do mais antigo ao mais recente.
        Cada elemento = SUM(weight_kg * reps) de uma sessão distinta.

        Postcondition: todos os valores >= 0  [P4]
        """
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
        # Inverte para ordem cronológica (mais antigo primeiro)
        volumes = [float(row["volume"]) for row in rows]
        volumes.reverse()
        return volumes

    def _compute_current_volume(self, exercise_id: int, session_id: int) -> float:
        """Volume total da sessão atual para o exercício."""
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
        Calcula delta percentual entre volume atual e média histórica (SMA).
        Se histórico vazio: delta_pct = 0.0  [P8]
        """
        current_volume = self._compute_current_volume(exercise_id, session_id)
        sma_volumes = self._compute_sma_volume(exercise_id, n)

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
