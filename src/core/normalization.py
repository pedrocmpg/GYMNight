"""
Text normalization and exercise matching engine
"""
from __future__ import annotations

import unicodedata

from src.core.models import Exercise, ExerciseMatch, MuscleContribution


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

    def __init__(self, db) -> None:
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

    def get_or_create(
        self, user_input: str, muscle_contributions: list[tuple[int, float]] | None = None
    ) -> Exercise:
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
            return {text[i : i + 2] for i in range(len(text) - 1)} if len(text) >= 2 else {text}
        return {text[i : i + 3] for i in range(len(text) - 2)}
