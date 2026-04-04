-- testlab/db/schema.sql
-- Schema SQLite per il registro leggero di progetti, testtype e run.
-- I file dati restano su disco (e su DVC remote): qui si tracciano
-- solo metadati e puntatori ai path locali.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- -------------------------------------------------------------------
-- Progetti
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT '',
    dvc_remote  TEXT DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now'))
);

-- -------------------------------------------------------------------
-- TestType per progetto
-- (collega il nome logico del testtype al nome dello script condiviso)
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS testtypes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,           -- es. "rendimento"
    script_name TEXT NOT NULL,           -- es. "rendimento_std"
    UNIQUE(project_id, name)
);

-- -------------------------------------------------------------------
-- TestRun
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS runs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    testtype_id  INTEGER NOT NULL REFERENCES testtypes(id) ON DELETE CASCADE,
    run_id       TEXT NOT NULL,          -- es. "003" (numerazione per testtype)
    condition    TEXT NOT NULL DEFAULT '',
    date         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
    notes        TEXT DEFAULT '',
    data_path    TEXT NOT NULL,          -- path relativo alla root del repo dati
    dvc_hash     TEXT DEFAULT '',        -- hash DVC per verifica integrità
    UNIQUE(project_id, testtype_id, run_id)
);

-- -------------------------------------------------------------------
-- Tag (molti-a-molti con runs)
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tags (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS run_tags (
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    tag_id INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    PRIMARY KEY (run_id, tag_id)
);

-- -------------------------------------------------------------------
-- Campi extra per run (chiave-valore libero)
-- -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS run_extra (
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    key    TEXT NOT NULL,
    value  TEXT NOT NULL,
    PRIMARY KEY (run_id, key)
);

-- -------------------------------------------------------------------
-- Viste utili
-- -------------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_runs AS
SELECT
    r.id,
    p.name          AS project,
    tt.name         AS testtype,
    tt.script_name,
    r.run_id,
    r.condition,
    r.date,
    r.notes,
    r.data_path,
    r.dvc_hash
FROM runs r
JOIN projects  p  ON p.id  = r.project_id
JOIN testtypes tt ON tt.id = r.testtype_id;
