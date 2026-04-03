"""
database.py - GYMNight Performance Engine
Schema SQLite com mapa de ativação muscular N:N + parser do muscle_usage_map.md.
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# Schema SQL
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS muscle_groups (
    id        INTEGER PRIMARY KEY,
    name      TEXT    NOT NULL UNIQUE,
    icon_path TEXT    NOT NULL DEFAULT ''
);

-- muscle_group_id REMOVIDO: relação agora é N:N via exercise_muscle_map
CREATE TABLE IF NOT EXISTS exercises (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name   TEXT    NOT NULL,
    user_input_name  TEXT    NOT NULL,
    created_at       INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_exercises_canonical ON exercises(canonical_name);

-- Mapa de ativação muscular proporcional (N:N)
-- contribution: decimal 0.0–1.0 (ex: 70% → 0.7)
CREATE TABLE IF NOT EXISTS exercise_muscle_map (
    exercise_id    INTEGER NOT NULL REFERENCES exercises(id)     ON DELETE CASCADE,
    muscle_group_id INTEGER NOT NULL REFERENCES muscle_groups(id) ON DELETE CASCADE,
    contribution   REAL    NOT NULL CHECK(contribution > 0 AND contribution <= 1.0),
    PRIMARY KEY (exercise_id, muscle_group_id)
);

CREATE INDEX IF NOT EXISTS idx_muscle_map_exercise ON exercise_muscle_map(exercise_id);
CREATE INDEX IF NOT EXISTS idx_muscle_map_muscle   ON exercise_muscle_map(muscle_group_id);

-- Rotinas (templates de treino)
CREATE TABLE IF NOT EXISTS routines (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    created_at INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS routine_exercises (
    routine_id  INTEGER NOT NULL REFERENCES routines(id)  ON DELETE CASCADE,
    exercise_id INTEGER NOT NULL REFERENCES exercises(id),
    order_index INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (routine_id, exercise_id)
);

CREATE INDEX IF NOT EXISTS idx_routine_exercises_routine ON routine_exercises(routine_id, order_index);

-- Sessões de treino
CREATE TABLE IF NOT EXISTS workout_sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at       INTEGER NOT NULL DEFAULT (unixepoch()),
    routine_id       INTEGER REFERENCES routines(id),
    duration_seconds INTEGER,
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

CREATE INDEX IF NOT EXISTS idx_logs_exercise_time ON workout_logs(exercise_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_session       ON workout_logs(session_id);

-- View: volume PROPORCIONAL por músculo, por sessão
-- Volume muscular = peso * reps * contribution
CREATE VIEW IF NOT EXISTS session_muscle_volume AS
SELECT
    wl.session_id,
    wl.exercise_id,
    emm.muscle_group_id,
    SUM(wl.weight_kg * wl.reps * emm.contribution) AS muscle_volume,
    MIN(wl.timestamp)                               AS session_ts
FROM workout_logs wl
JOIN exercise_muscle_map emm ON wl.exercise_id = emm.exercise_id
GROUP BY wl.session_id, wl.exercise_id, emm.muscle_group_id;

-- View: volume bruto por exercício por sessão (mantida para SMA geral)
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

# Ordem das colunas no markdown (deve bater com os IDs do SEED_SQL)
_MD_COLUMN_ORDER = [1, 2, 3, 4, 5, 6, 7]  # Peito, Costas, Ombros, Bíceps, Tríceps, Pernas, Abdômen


# ---------------------------------------------------------------------------
# Parser do muscle_usage_map.md
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase + remove acentos + strip — mesmo algoritmo do NormalizationEngine."""
    nfd = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def parse_muscle_map(md_path: str) -> list[tuple[str, int, float]]:
    """
    Lê o muscle_usage_map.md e retorna lista de (canonical_name, muscle_group_id, contribution).
    - Ignora linhas de cabeçalho, separador e seções em negrito (**texto**).
    - Converte porcentagens inteiras para decimais (70 → 0.7).
    - Ignora músculos com contribuição 0.
    """
    path = Path(md_path)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {md_path}")

    records: list[tuple[str, int, float]] = []
    section_re = re.compile(r"^\|\s*\*\*.*\*\*")  # linhas de seção em negrito

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Ignora linhas vazias, cabeçalho e separador (:---:)
            if not line.startswith("|"):
                continue
            if ":---" in line:
                continue
            if section_re.match(line):
                continue

            # Divide células e remove pipes externos
            cells = [c.strip() for c in line.split("|")]
            cells = [c for c in cells if c != ""]  # remove vazios das bordas

            if len(cells) < 8:
                continue

            exercise_name = _normalize(cells[0])
            if not exercise_name:
                continue

            for col_idx, muscle_group_id in enumerate(_MD_COLUMN_ORDER):
                raw = cells[col_idx + 1].replace("%", "").strip()
                try:
                    pct = float(raw)
                except ValueError:
                    continue
                if pct <= 0:
                    continue
                contribution = round(pct / 100.0, 4)
                records.append((exercise_name, muscle_group_id, contribution))

    return records


def seed_muscle_map(db: "DatabaseConnection", md_path: str) -> int:
    """
    Popula exercises + exercise_muscle_map a partir do markdown.
    Usa INSERT OR IGNORE para ser idempotente (seguro rodar múltiplas vezes).
    Retorna o número de exercícios processados.
    """
    records = parse_muscle_map(md_path)

    # Agrupa por exercício para inserir cada um uma vez
    exercises: dict[str, list[tuple[int, float]]] = {}
    for canonical_name, muscle_group_id, contribution in records:
        exercises.setdefault(canonical_name, []).append((muscle_group_id, contribution))

    with db._conn:
        for canonical_name, muscle_map in exercises.items():
            # Insere exercício (sem muscle_group_id — relação N:N)
            db._conn.execute(
                "INSERT OR IGNORE INTO exercises (canonical_name, user_input_name) VALUES (?, ?)",
                (canonical_name, canonical_name),
            )
            row = db._conn.execute(
                "SELECT id FROM exercises WHERE canonical_name = ?",
                (canonical_name,),
            ).fetchone()
            exercise_id = row["id"]

            # Insere mapeamento muscular
            db._conn.executemany(
                "INSERT OR IGNORE INTO exercise_muscle_map (exercise_id, muscle_group_id, contribution) VALUES (?, ?, ?)",
                [(exercise_id, mg_id, contrib) for mg_id, contrib in muscle_map],
            )

    return len(exercises)


# ---------------------------------------------------------------------------
# DatabaseConnection
# ---------------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

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
