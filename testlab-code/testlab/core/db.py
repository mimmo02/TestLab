"""
testlab.core.db
---------------
Repository SQLite per progetti, testtype e run.
Usa solo sqlite3 della stdlib — nessuna dipendenza esterna.

Utilizzo rapido:
    from testlab.core.db import TestLabDB
    db = TestLabDB("db/testlab.sqlite")
    db.add_project("motore_v2", "Progetto motore seconda versione")
    db.add_testtype("motore_v2", "rendimento", "rendimento_std")
    run_id = db.add_run("motore_v2", "rendimento",
                        condition="carico50",
                        data_path="projects/motore_v2/rendimento/001_carico50/data.csv")
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any


_SCHEMA_PATH = Path(__file__).parent.parent.parent / "db" / "schema.sql"


class TestLabDB:
    def __init__(self, db_path: str | Path = "db/testlab.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ------------------------------------------------------------------
    # Connessione
    # ------------------------------------------------------------------

    @contextmanager
    def _conn(self):
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON")
        try:
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    def _init_schema(self):
        schema = _SCHEMA_PATH.read_text(encoding="utf-8")
        with self._conn() as con:
            con.executescript(schema)

    # ------------------------------------------------------------------
    # Progetti
    # ------------------------------------------------------------------

    def add_project(
        self,
        name: str,
        description: str = "",
        dvc_remote: str = "",
    ) -> int:
        """Inserisce un nuovo progetto. Restituisce l'id."""
        with self._conn() as con:
            cur = con.execute(
                "INSERT INTO projects (name, description, dvc_remote) "
                "VALUES (?, ?, ?)",
                (name, description, dvc_remote),
            )
            return cur.lastrowid

    def get_project(self, name: str) -> dict | None:
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM projects WHERE name = ?", (name,)
            ).fetchone()
            return dict(row) if row else None

    def list_projects(self) -> list[dict]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM projects ORDER BY name"
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_project(self, name: str):
        """Elimina progetto e tutti i suoi run (cascade)."""
        with self._conn() as con:
            con.execute("DELETE FROM projects WHERE name = ?", (name,))

    # ------------------------------------------------------------------
    # TestType
    # ------------------------------------------------------------------

    def add_testtype(
        self,
        project_name: str,
        testtype_name: str,
        script_name: str,
    ) -> int:
        pid = self._project_id(project_name)
        with self._conn() as con:
            cur = con.execute(
                "INSERT OR REPLACE INTO testtypes (project_id, name, script_name) "
                "VALUES (?, ?, ?)",
                (pid, testtype_name, script_name),
            )
            return cur.lastrowid

    def list_testtypes(self, project_name: str) -> list[dict]:
        pid = self._project_id(project_name)
        with self._conn() as con:
            rows = con.execute(
                "SELECT * FROM testtypes WHERE project_id = ? ORDER BY name",
                (pid,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def add_run(
        self,
        project_name: str,
        testtype_name: str,
        condition: str,
        data_path: str,
        notes: str = "",
        dvc_hash: str = "",
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> int:
        """
        Inserisce un run con run_id autoincrementato per (progetto, testtype).
        Restituisce l'id del run inserito.
        """
        pid  = self._project_id(project_name)
        ttid = self._testtype_id(pid, testtype_name)
        next_run_id = self._next_run_id(pid, ttid)

        with self._conn() as con:
            cur = con.execute(
                "INSERT INTO runs "
                "(project_id, testtype_id, run_id, condition, notes, data_path, dvc_hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, ttid, next_run_id, condition, notes, data_path, dvc_hash),
            )
            run_db_id = cur.lastrowid

            if tags:
                for tag in tags:
                    con.execute(
                        "INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,)
                    )
                    tag_id = con.execute(
                        "SELECT id FROM tags WHERE name = ?", (tag,)
                    ).fetchone()["id"]
                    con.execute(
                        "INSERT OR IGNORE INTO run_tags (run_id, tag_id) "
                        "VALUES (?, ?)",
                        (run_db_id, tag_id),
                    )

            if extra:
                for k, v in extra.items():
                    con.execute(
                        "INSERT OR REPLACE INTO run_extra (run_id, key, value) "
                        "VALUES (?, ?, ?)",
                        (run_db_id, k, str(v)),
                    )

        return run_db_id

    def get_run(self, run_db_id: int) -> dict | None:
        with self._conn() as con:
            row = con.execute(
                "SELECT * FROM v_runs WHERE id = ?", (run_db_id,)
            ).fetchone()
            if not row:
                return None
            result = dict(row)
            result["tags"]  = self._get_tags(run_db_id)
            result["extra"] = self._get_extra(run_db_id)
            return result

    def list_runs(
        self,
        project_name: str,
        testtype_name: str | None = None,
        tags: list[str] | None = None,
        condition: str | None = None,
    ) -> list[dict]:
        """
        Elenca i run con filtri opzionali.
        Tutti i parametri sono opzionali eccetto project_name.
        """
        sql  = "SELECT * FROM v_runs WHERE project = ?"
        args: list[Any] = [project_name]

        if testtype_name:
            sql += " AND testtype = ?"
            args.append(testtype_name)
        if condition:
            sql += " AND condition = ?"
            args.append(condition)

        sql += " ORDER BY testtype, run_id"

        with self._conn() as con:
            rows = con.execute(sql, args).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["tags"]  = self._get_tags(d["id"])
                d["extra"] = self._get_extra(d["id"])
                result.append(d)

        if tags:
            tag_set = set(tags)
            result = [r for r in result if tag_set.issubset(set(r["tags"]))]

        return result

    def update_run_notes(self, run_db_id: int, notes: str):
        with self._conn() as con:
            con.execute(
                "UPDATE runs SET notes = ? WHERE id = ?", (notes, run_db_id)
            )

    def update_dvc_hash(self, run_db_id: int, dvc_hash: str):
        with self._conn() as con:
            con.execute(
                "UPDATE runs SET dvc_hash = ? WHERE id = ?",
                (dvc_hash, run_db_id),
            )

    def delete_run(self, run_db_id: int):
        with self._conn() as con:
            con.execute("DELETE FROM runs WHERE id = ?", (run_db_id,))

    # ------------------------------------------------------------------
    # Helpers privati
    # ------------------------------------------------------------------

    def _project_id(self, name: str) -> int:
        with self._conn() as con:
            row = con.execute(
                "SELECT id FROM projects WHERE name = ?", (name,)
            ).fetchone()
        if not row:
            raise ValueError(f"Progetto '{name}' non trovato nel DB.")
        return row["id"]

    def _testtype_id(self, project_id: int, testtype_name: str) -> int:
        with self._conn() as con:
            row = con.execute(
                "SELECT id FROM testtypes WHERE project_id = ? AND name = ?",
                (project_id, testtype_name),
            ).fetchone()
        if not row:
            raise ValueError(
                f"TestType '{testtype_name}' non trovato per project_id={project_id}."
            )
        return row["id"]

    def _next_run_id(self, project_id: int, testtype_id: int) -> str:
        """Calcola il prossimo run_id come stringa zero-padded a 3 cifre."""
        with self._conn() as con:
            row = con.execute(
                "SELECT COUNT(*) AS cnt FROM runs "
                "WHERE project_id = ? AND testtype_id = ?",
                (project_id, testtype_id),
            ).fetchone()
        return f"{(row['cnt'] + 1):03d}"

    def _get_tags(self, run_db_id: int) -> list[str]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT t.name FROM tags t "
                "JOIN run_tags rt ON rt.tag_id = t.id "
                "WHERE rt.run_id = ?",
                (run_db_id,),
            ).fetchall()
        return [r["name"] for r in rows]

    def _get_extra(self, run_db_id: int) -> dict[str, str]:
        with self._conn() as con:
            rows = con.execute(
                "SELECT key, value FROM run_extra WHERE run_id = ?",
                (run_db_id,),
            ).fetchall()
        return {r["key"]: r["value"] for r in rows}
