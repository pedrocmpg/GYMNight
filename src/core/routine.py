"""
Routine management and session handling
"""
from __future__ import annotations

import time

from src.core.models import Exercise, Routine
from src.core.normalization import NormalizationEngine


class RoutineManager:
    """Gerencia rotinas: criação, listagem, consulta e encerramento de sessão."""

    def __init__(self, db) -> None:
        self._db = db
        self._norm = NormalizationEngine(db)

    def calculate_session_calories(self, session_id: int, user_weight_kg: float = 70.0) -> float:
        """
        Calcula calorias totais de uma sessão usando a fórmula MET.
        Fórmula: Calorias = (MET × Peso_kg × Tempo_min) / 60
        Tempo por repetição: 4 segundos (0.0667 minutos)

        Args:
            session_id: ID da sessão
            user_weight_kg: Peso do usuário em kg (padrão 70kg)

        Returns:
            Total de calorias queimadas na sessão
        """
        rows = self._db.fetchall(
            """
            SELECT wl.reps, emv.met_value
            FROM workout_logs wl
            LEFT JOIN exercise_met_values emv ON wl.exercise_id = emv.exercise_id
            WHERE wl.session_id = ? AND wl.set_type != 'W'
            """,
            (session_id,),
        )

        total_calories = 0.0
        for row in rows:
            reps = row["reps"]
            met_value = row["met_value"]

            if met_value is None:
                # Se não tiver MET, usa valor padrão conservador
                met_value = 5.0

            # Tempo em minutos: 4 segundos por rep
            time_min = reps * 4.0 / 60.0

            # Fórmula MET: (MET × Peso_kg × Tempo_min) / 60
            calories = (met_value * user_weight_kg * time_min) / 60.0
            total_calories += calories

        return total_calories

    def create_routine(self, name: str, exercise_ids: list[int], default_sets_list: list[int] = None) -> Routine:
        """
        Cria uma nova rotina com exercícios.
        
        Args:
            name: Nome da rotina
            exercise_ids: Lista de IDs dos exercícios
            default_sets_list: Lista com número de séries para cada exercício (opcional, padrão 3)
        """
        routine_id = self._db.execute_write("INSERT INTO routines (name) VALUES (?)", (name.strip(),))
        
        # Se não foi fornecido, usa 3 séries para todos
        if default_sets_list is None:
            default_sets_list = [3] * len(exercise_ids)
        
        self._db.execute_many(
            "INSERT INTO routine_exercises (routine_id, exercise_id, order_index, default_sets) VALUES (?, ?, ?, ?)",
            [(routine_id, ex_id, idx, default_sets_list[idx]) for idx, ex_id in enumerate(exercise_ids)],
        )
        row = self._db.fetchone("SELECT id, name, created_at FROM routines WHERE id = ?", (routine_id,))
        return Routine(id=row["id"], name=row["name"], created_at=row["created_at"])

    def list_routines(self) -> list[Routine]:
        rows = self._db.fetchall("SELECT id, name, created_at FROM routines ORDER BY name")
        return [Routine(id=r["id"], name=r["name"], created_at=r["created_at"]) for r in rows]

    def get_routine_exercises(self, routine_id: int) -> list[tuple[Exercise, int]]:
        """
        Retorna lista de tuplas (Exercise, default_sets) para uma rotina.
        
        Returns:
            Lista de tuplas (Exercise, número_de_séries)
        """
        rows = self._db.fetchall(
            """
            SELECT e.id, e.canonical_name, e.user_input_name, re.default_sets
            FROM routine_exercises re
            JOIN exercises e ON re.exercise_id = e.id
            WHERE re.routine_id = ?
            ORDER BY re.order_index ASC
            """,
            (routine_id,),
        )
        return [
            (
                self._norm._load_exercise(r["id"], r["canonical_name"], r["user_input_name"]),
                r["default_sets"]
            )
            for r in rows
        ]

    def update_routine_template(self, routine_id: int, new_exercise_ids: list[int]) -> None:
        """Substitui exercícios da rotina atomicamente (DELETE + INSERT)."""
        with self._db._conn:
            self._db._conn.execute("DELETE FROM routine_exercises WHERE routine_id = ?", (routine_id,))
            self._db._conn.executemany(
                "INSERT INTO routine_exercises (routine_id, exercise_id, order_index) VALUES (?, ?, ?)",
                [(routine_id, ex_id, idx) for idx, ex_id in enumerate(new_exercise_ids)],
            )

    def end_session(self, session_id: int) -> int:
        """Calcula e persiste duration_seconds. Retorna a duração."""
        row = self._db.fetchone("SELECT started_at FROM workout_sessions WHERE id = ?", (session_id,))
        if not row:
            return 0
        duration = int(time.time()) - row["started_at"]
        self._db.execute_write(
            "UPDATE workout_sessions SET duration_seconds = ? WHERE id = ?",
            (duration, session_id),
        )
        return duration
