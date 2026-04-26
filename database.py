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

# Mapa de valores MET por exercício (do gasto_calorico_exercicio.md)
_EXERCISE_MET_MAP = {
    # Peito
    "supino reto (barra)": 6.0, "supino inclinado (barra)": 6.0, "supino declinado (barra)": 6.0,
    "supino com halteres": 6.0, "supino inclinado halteres": 6.0, "supino declinado halteres": 6.0,
    "crucifixo reto": 6.0, "crucifixo inclinado": 6.0, "crucifixo declinado": 6.0,
    "voador (pec deck)": 6.0, "crossover polia alta": 6.0, "crossover polia baixa": 6.0,
    "crossover polia media": 6.0, "flexao de braco (push-up)": 7.5, "flexao diamante": 7.5,
    "flexao inclinada (maos no banco)": 7.5, "flexao declinada (pes no banco)": 7.5,
    "flexao arqueiro": 7.5, "flexao explosiva (clap)": 11.0, "paralelas (foco peito)": 7.5,
    "pullover (halter)": 6.0, "pullover (barra)": 6.0, "chest press maquina": 6.0,
    "chest press inclinado maquina": 6.0, "floor press (barra)": 6.0, "floor press (halteres)": 6.0,
    "svend press": 6.0, "landmine press (peito)": 6.0, "crucifixo maquina": 6.0,
    "supino pegada invertida": 6.0, "supino articulado": 6.0, "fly com cabos inclinado": 6.0,
    "flexao com peso (anilha)": 7.5,
    
    # Costas
    "barra fixa (pronada)": 7.5, "barra fixa (supinada/chin-up)": 7.5, "barra fixa (neutra)": 7.5,
    "puxada alta (lat pulldown)": 6.0, "puxada triangulo": 6.0, "puxada supinada": 6.0,
    "puxada por tras": 6.0, "remada curvada (barra)": 6.0, "remada curvada (supinada)": 6.0,
    "remada unilateral (serrote)": 6.0, "remada baixa (polia)": 6.0, "remada cavalinho (t-bar)": 6.0,
    "remada cavalinho apoiada": 6.0, "pulldown (bracos estendidos)": 6.0, "remada articulada": 6.0,
    "remada pendlay": 6.0, "remada meadow": 6.0, "remada seal (banco alto)": 6.0,
    "remada invertida (calistenia)": 6.0, "face pull (foco posterior)": 6.0,
    "levantamento terra (convencional)": 5.0, "rack pull": 6.0, "hiperextensao lombar": 6.0,
    "bom dia (good morning)": 6.0, "superman (isometria)": 6.0, "remada alta (pegada larga)": 6.0,
    "puxada unilateral cabo": 6.0, "remada com halteres (banco inclinado)": 6.0,
    "remada renegade": 6.0, "muscle up (fase puxada)": 7.5, "remada t-bar livre": 6.0,
    "puxada com corda": 6.0, "remada na maquina hammer": 6.0,
    
    # Ombros
    "desenvolvimento barra (militar)": 3.5, "desenvolvimento halteres": 3.5,
    "desenvolvimento arnold": 3.5, "desenvolvimento maquina": 3.5, "elevacao lateral (halter)": 3.5,
    "elevacao lateral (polia)": 3.5, "elevacao lateral inclinada": 3.5,
    "elevacao frontal (halter)": 3.5, "elevacao frontal (barra)": 3.5,
    "elevacao frontal (anilha)": 3.5, "crucifixo inverso (halter)": 3.5,
    "crucifixo inverso (maquina)": 3.5, "crucifixo inverso (polia)": 3.5,
    "encolhimento (barra)": 3.5, "encolhimento (halteres)": 3.5,
    "z-press (sentado no chao)": 3.5, "push press": 3.5, "bradford press": 3.5,
    "elevacao lateral \"y\"": 3.5, "face pull corda": 3.5, "remada alta (barra ez)": 3.5,
    "desenvolvimento por tras": 3.5, "pike push-up": 7.5, "handstand push-up": 7.5,
    "elevacao lateral unilateral cabo": 3.5, "crucifixo inverso unilateral cabo": 3.5,
    "landmine press unilateral": 3.5, "snatch grip high pull": 11.0,
    "clean and press": 11.0, "thruster": 11.0, "elevacao frontal cabo": 3.5,
    "desenvolvimento smith": 3.5, "face pull polia alta": 3.5,
    
    # Bíceps
    "rosca direta (barra)": 3.5, "rosca direta (barra ez)": 3.5, "rosca martelo": 3.5,
    "rosca scott (barra ez)": 3.5, "rosca inclinada (halter)": 3.5, "rosca concentrada": 3.5,
    "rosca alternada": 3.5, "rosca zottman": 3.5, "rosca aranha (spider curl)": 3.5,
    "rosca no cabo (polia baixa)": 3.5, "rosca martelo com corda": 3.5,
    "rosca inversa (barra)": 3.5, "rosca 21": 3.5, "rosca drag": 3.5,
    "rosca hercules (crossover alto)": 3.5, "rosca maquina": 3.5,
    "rosca alternada com rotacao": 3.5, "rosca direta com halteres": 3.5,
    "rosca martelo inclinada": 3.5, "rosca scott unilateral": 3.5,
    "rosca paje (antebraco)": 3.5, "flexao de punho": 7.5, "extensao de punho": 3.5,
    "rosca direta na polia alta": 3.5, "rosca concentrada no cabo": 3.5,
    "rosca martelo alternada": 3.5, "rosca direta pegada larga": 3.5,
    "rosca direta pegada estreita": 3.5, "rosca scott maquina": 3.5,
    "rosca martelo com halteres": 3.5, "rosca direta com anilha": 3.5,
    "rosca martelo com anilha": 3.5, "rosca direta com kettlebell": 3.5,
    
    # Tríceps
    "triceps testa (barra ez)": 3.5, "triceps pulley (barra reta)": 3.5,
    "triceps pulley (corda)": 3.5, "triceps frances (halter)": 3.5,
    "triceps frances (polia baixa)": 3.5, "triceps coice (halter)": 3.5,
    "triceps coice (polia)": 3.5, "supino fechado (close grip)": 3.5,
    "mergulho no banco (dips)": 3.5, "paralelas (foco triceps)": 7.5,
    "triceps testa (halteres)": 3.5, "triceps invertido (polia)": 3.5,
    "triceps unilateral (polia)": 3.5, "triceps maquina": 3.5,
    "triceps testa inclinado": 3.5, "triceps testa declinado": 3.5,
    "extensao de triceps sobre a cabeca": 3.5, "triceps corda unilateral": 3.5,
    "triceps frances com barra ez": 3.5, "triceps pulley com barra v": 3.5,
    "triceps coice com halteres": 3.5, "triceps testa com kettlebell": 3.5,
    "triceps frances sentado": 3.5, "triceps frances em pe": 3.5,
    "triceps pulley pegada invertida": 3.5, "triceps testa no cabo": 3.5,
    "triceps frances no cabo": 3.5, "triceps coice no cabo": 3.5,
    "triceps maquina sentado": 3.5, "triceps mergulho maquina": 3.5,
    "triceps extensao unilateral halter": 3.5, "triceps extensao com anilha": 3.5,
    "triceps extensao com elastico": 3.5,
    
    # Pernas
    "agachamento livre (back squat)": 5.0, "agachamento frontal": 5.0, "leg press 45": 5.0,
    "hack squat": 5.0, "cadeira extensora": 3.5, "mesa flexora": 3.5, "cadeira flexora": 3.5,
    "stiff (rdl)": 5.0, "levantamento terra sumo": 5.0, "agachamento bulgaro": 5.0,
    "passada (lunges)": 5.0, "elevacao pelvica (hip thrust)": 3.5, "panturrilha em pe": 3.5,
    "panturrilha sentado": 3.5, "cadeira abdutora": 3.5, "cadeira adutora": 3.5,
    "agachamento goblet": 5.0, "agachamento sumo (halter)": 5.0, "flexor em pe unilateral": 3.5,
    "panturrilha no leg press": 5.0, "sissy squat": 3.5, "gluteo na polia": 3.5,
    "abducao de quadril polia": 3.5, "aducao de quadril polia": 3.5, "agachamento smith": 5.0,
    "step up (subida no banco)": 3.5, "agachamento cossaco": 5.0, "pistol squat": 3.5,
    "flexao nordica": 7.5, "extensao de quadril (gluteo maquina)": 3.5,
    
    # Abdômen
    "abdominal supra": 3.8, "abdominal infra": 3.8, "prancha isometrica (plank)": 2.8,
    "abdominal roda (ab wheel)": 3.8, "elevacao de pernas pendurado": 3.8,
    "russian twist": 3.8, "pallof press": 3.8, "prancha lateral": 3.8,
    "abdominal obliquo": 3.8, "dead bug": 3.8, "bird dog": 3.8,
    "abdominal canivete": 3.8, "prancha com toque no ombro": 3.8,
    "mountain climbers": 11.0, "abdominal bicicleta": 3.8,
}


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
            
            # Insere valor MET se disponível
            met_value = _EXERCISE_MET_MAP.get(canonical_name)
            if met_value:
                db._conn.execute(
                    "INSERT OR IGNORE INTO exercise_met_values (exercise_id, met_value) VALUES (?, ?)",
                    (exercise_id, met_value),
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
                self._conn.execute("ALTER TABLE routine_exercises ADD COLUMN default_sets INTEGER NOT NULL DEFAULT 3")

            # Cria tabela exercise_met_values se não existir
            tables = [r[0] for r in self._conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            if "exercise_met_values" not in tables:
                self._conn.execute("""
                    CREATE TABLE exercise_met_values (
                        exercise_id INTEGER PRIMARY KEY REFERENCES exercises(id) ON DELETE CASCADE,
                        met_value   REAL NOT NULL CHECK(met_value > 0)
                    )
                """)
                self._conn.execute("CREATE INDEX idx_met_exercise ON exercise_met_values(exercise_id)")

            # Recria views para incluir filtro set_type != 'W'
            self._conn.execute("DROP VIEW IF EXISTS session_muscle_volume")
            self._conn.execute("DROP VIEW IF EXISTS session_volume")
            self._conn.executescript("""
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
""")

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
