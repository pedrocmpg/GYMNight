"""
Database schema definitions
"""

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
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    created_at  INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS routine_exercises (
    routine_id   INTEGER NOT NULL REFERENCES routines(id)  ON DELETE CASCADE,
    exercise_id  INTEGER NOT NULL REFERENCES exercises(id),
    order_index  INTEGER NOT NULL DEFAULT 0,
    default_sets INTEGER NOT NULL DEFAULT 3,
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
-- set_type: 'N' Normal | 'W' Aquecimento | 'D' Dropset | 'F' Falha
CREATE TABLE IF NOT EXISTS workout_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id INTEGER NOT NULL REFERENCES exercises(id),
    session_id  INTEGER NOT NULL REFERENCES workout_sessions(id),
    weight_kg   REAL    NOT NULL CHECK(weight_kg > 0),
    reps        INTEGER NOT NULL CHECK(reps >= 1),
    set_type    TEXT    NOT NULL DEFAULT 'N' CHECK(set_type IN ('N','W','D','F')),
    timestamp   INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_logs_exercise_time ON workout_logs(exercise_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_logs_session       ON workout_logs(session_id);

-- View: volume PROPORCIONAL por músculo, por sessão
-- Séries de Aquecimento (set_type='W') são EXCLUÍDAS — não contaminam a métrica de hipertrofia
CREATE VIEW IF NOT EXISTS session_muscle_volume AS
SELECT
    wl.session_id,
    wl.exercise_id,
    emm.muscle_group_id,
    SUM(wl.weight_kg * wl.reps * emm.contribution) AS muscle_volume,
    MIN(wl.timestamp)                               AS session_ts
FROM workout_logs wl
JOIN exercise_muscle_map emm ON wl.exercise_id = emm.exercise_id
WHERE wl.set_type != 'W'
GROUP BY wl.session_id, wl.exercise_id, emm.muscle_group_id;

-- View: volume bruto por exercício por sessão (exclui aquecimento)
CREATE VIEW IF NOT EXISTS session_volume AS
SELECT
    exercise_id,
    session_id,
    SUM(weight_kg * reps) AS volume,
    MIN(timestamp)        AS session_ts
FROM workout_logs
WHERE set_type != 'W'
GROUP BY exercise_id, session_id;

-- Logs de cardio (métricas diferentes da musculação)
CREATE TABLE IF NOT EXISTS cardio_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  INTEGER NOT NULL REFERENCES workout_sessions(id),
    cardio_type TEXT    NOT NULL,
    duration_min REAL   NOT NULL CHECK(duration_min > 0),
    distance_km  REAL,
    pse          INTEGER CHECK(pse BETWEEN 1 AND 10),
    timestamp   INTEGER NOT NULL DEFAULT (unixepoch())
);

CREATE INDEX IF NOT EXISTS idx_cardio_session ON cardio_logs(session_id);

-- Tabela de valores MET por exercício (para cálculo de calorias)
CREATE TABLE IF NOT EXISTS exercise_met_values (
    exercise_id INTEGER PRIMARY KEY REFERENCES exercises(id) ON DELETE CASCADE,
    met_value   REAL NOT NULL CHECK(met_value > 0)
);

CREATE INDEX IF NOT EXISTS idx_met_exercise ON exercise_met_values(exercise_id);
"""

SEED_SQL = """
INSERT OR IGNORE INTO muscle_groups (id, name, icon_path) VALUES
    (1, 'Peito',    'assets/icons/chest.png'),
    (2, 'Costas',   'assets/icons/back.png'),
    (3, 'Ombros',   'assets/icons/shoulders.png'),
    (4, 'Bíceps',   'assets/icons/biceps.png'),
    (5, 'Tríceps',  'assets/icons/triceps.png'),
    (6, 'Pernas',   'assets/icons/legs.png'),
    (7, 'Abdômen',  'assets/icons/abs.png');
"""
