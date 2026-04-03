"""
database.py - GYMNight Performance Engine
Schema SQLite otimizado para agregação temporal + classe de conexão.
"""

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS muscle_groups (
    id        INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL UNIQUE,
    icon_path TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS exercises (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name   TEXT    NOT NULL,
    user_input_name  TEXT    NOT NULL,
    muscle_group_id  INTEGER NOT NULL REFERENCES muscle_groups(id),
    created_at       INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_exercises_canonical ON exercises(canonical_name);
CREATE INDEX        IF NOT EXISTS idx_exercises_muscle    ON exercises(muscle_group_id);

-- Rotinas (templates de treino)
CREATE TABLE IF NOT EXISTS routines (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (unixepoch())
);

-- Exercícios de uma rotina, com ordem definida
CREATE TABLE IF NOT EXISTS routine_exercises (
    routine_id  INTEGER NOT NULL REFERENCES routines(id) ON DELETE CASCADE,
    exercise_id INTEGER NOT NULL REFERENCES exercises(id),
    order_index INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (routine_id, exercise_id)
);

CREATE INDEX IF NOT EXISTS idx_routine_exercises_routine ON routine_exercises(routine_id, order_index);

-- Sessões de treino (agrupa séries de um mesmo treino)
CREATE TABLE IF NOT EXISTS workout_sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at       INTEGER NOT NULL DEFAULT (unixepoch()),
    routine_id       INTEGER REFERENCES routines(id),   -- opcional: sessão baseada em rotina
    duration_seconds INTEGER,                           -- preenchido ao encerrar a sessão
    notes            TEXT
);

-- Log atômico: cada linha = uma série
CREATE TABLE IF NOT EXISTS workout_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id INTEGER NOT NULL REFERENCES exercises(id),
    session_id  INTEGER NOT NULL REFERENCES workout_sessions(id),
    weight_kg   REAL    NOT NULL CHECK(weight_kg > 0),
    reps        INTEGER NOT NULL CHECK(reps >= 1),
    timestamp   INTEGER NOT NULL DEFAULT (unixepoch())
);

-- Índices críticos para queries de agregação temporal
CREATE INDEX IF NOT EXISTS idx_logs_exercise_time ON workout_logs(exercise_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_session       ON workout_logs(session_id);

-- View: volume por sessão por exercício (base do SMA)
CREATE VIEW IF NOT EXISTS session_volume AS
SELECT
    exercise_id,
    session_id,
    SUM(weight_kg * reps) AS volume,
    MIN(timestamp)        AS session_ts
FROM workout_logs
GROUP BY exercise_id, session_id;
"""

SEED_SQL = """
INSERT OR IGNORE INTO muscle_groups (id, name, icon_path) VALUES
    (1, 'Peito',    'icons/chest.png'),
    (2, 'Costas',   'icons/back.png'),
    (3, 'Ombros',   'icons/shoulders.png'),
    (4, 'Bíceps',   'icons/biceps.png'),
    (5, 'Tríceps',  'icons/triceps.png'),
    (6, 'Pernas',   'icons/legs.png'),
    (7, 'Abdômen',  'icons/abs.png');
"""


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
            check_same_thread=False,  # QThread acessa via lock externo
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row

    def _apply_schema(self) -> None:
        with self._conn:
            self._conn.executescript(SCHEMA_SQL)
            self._conn.executescript(SEED_SQL)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Executa uma query parametrizada (sem SQL injection)."""
        return self._conn.execute(sql, params)

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        """Executa INSERT/UPDATE/DELETE dentro de transação. Retorna lastrowid."""
        with self._conn:
            cur = self._conn.execute(sql, params)
            return cur.lastrowid

    def execute_many(self, sql: str, params_list: list[tuple]) -> None:
        """Executa múltiplas escritas em uma única transação."""
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
