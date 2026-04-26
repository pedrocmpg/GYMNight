"""
Database connection management
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from src.database.schema import SCHEMA_SQL, SEED_SQL


class DatabaseConnection:
    """Gerencia a conexão SQLite com suporte a WAL e foreign keys."""

    def __init__(self, db_path: str = "gymnight.db") -> None:
        self._path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        self._connect()
        self._apply_schema()

    def _connect(self) -> None:
        self._conn = sqlite3.connect(
            str(self._path),
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row

    def _apply_schema(self) -> None:
        with self._conn:
            self._conn.executescript(SCHEMA_SQL)
            self._conn.executescript(SEED_SQL)
            self._migrate()

    def _migrate(self) -> None:
        """Migrações incrementais para bancos existentes."""
        with self._conn:
            # Adiciona set_type se não existir
            cols = [r[1] for r in self._conn.execute("PRAGMA table_info(workout_logs)").fetchall()]
            if "set_type" not in cols:
                self._conn.execute("ALTER TABLE workout_logs ADD COLUMN set_type TEXT NOT NULL DEFAULT 'N'")

            # Adiciona description em routines
            cols_r = [r[1] for r in self._conn.execute("PRAGMA table_info(routines)").fetchall()]
            if "description" not in cols_r:
                self._conn.execute("ALTER TABLE routines ADD COLUMN description TEXT NOT NULL DEFAULT ''")

            # Adiciona default_sets em routine_exercises
            cols_re = [r[1] for r in self._conn.execute("PRAGMA table_info(routine_exercises)").fetchall()]
            if "default_sets" not in cols_re:
                self._conn.execute(
                    "ALTER TABLE routine_exercises ADD COLUMN default_sets INTEGER NOT NULL DEFAULT 3"
                )

            # Cria tabela exercise_met_values se não existir
            tables = [
                r[0] for r in self._conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            ]
            if "exercise_met_values" not in tables:
                self._conn.execute(
                    """
                    CREATE TABLE exercise_met_values (
                        exercise_id INTEGER PRIMARY KEY REFERENCES exercises(id) ON DELETE CASCADE,
                        met_value   REAL NOT NULL CHECK(met_value > 0)
                    )
                """
                )
                self._conn.execute("CREATE INDEX idx_met_exercise ON exercise_met_values(exercise_id)")

            # Recria views para incluir filtro set_type != 'W'
            self._conn.execute("DROP VIEW IF EXISTS session_muscle_volume")
            self._conn.execute("DROP VIEW IF EXISTS session_volume")
            self._conn.executescript(
                """
CREATE VIEW session_muscle_volume AS
SELECT wl.session_id, wl.exercise_id, emm.muscle_group_id,
       SUM(wl.weight_kg * wl.reps * emm.contribution) AS muscle_volume,
       MIN(wl.timestamp) AS session_ts
FROM workout_logs wl
JOIN exercise_muscle_map emm ON wl.exercise_id = emm.exercise_id
WHERE wl.set_type != 'W'
GROUP BY wl.session_id, wl.exercise_id, emm.muscle_group_id;

CREATE VIEW session_volume AS
SELECT exercise_id, session_id,
       SUM(weight_kg * reps) AS volume,
       MIN(timestamp) AS session_ts
FROM workout_logs
WHERE set_type != 'W'
GROUP BY exercise_id, session_id;
"""
            )

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._conn.execute(sql, params)

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        with self._conn:
            cur = self._conn.execute(sql, params)
            return cur.lastrowid

    def execute_many(self, sql: str, params_list: list[tuple]) -> None:
        with self._conn:
            self._conn.executemany(sql, params_list)

    def fetchall(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return self._conn.execute(sql, params).fetchall()

    def fetchone(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        return self._conn.execute(sql, params).fetchone()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "DatabaseConnection":
        return self

    def __exit__(self, *_) -> None:
        self.close()
