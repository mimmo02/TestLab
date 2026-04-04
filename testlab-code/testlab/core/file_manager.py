"""
testlab.core.file_manager
--------------------------
Gestisce il salvataggio dei file dati su disco e i comandi
Git + DVC dalla GUI senza dover aprire il terminale.

Struttura creata su disco per ogni run:
    <data_root>/projects/<project>/<testtype>/<run_id>_<condition>/
        data.<ext>
        meta.json

I comandi Git e DVC vengono eseguiti come sottoprocessi e
restituiscono un dict {"ok": bool, "output": str, "error": str}.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from .interfaces import RunMeta, ProjectConfig
from .db import TestLabDB


class FileManager:
    """
    Parametri:
        code_root  — root del repo codice (dove sta project.json, core/, scripts/)
        data_root  — root del repo dati (dove stanno i CSV reali)
        db         — istanza TestLabDB già inizializzata
    """

    def __init__(
        self,
        code_root: str | Path,
        data_root: str | Path,
        db: TestLabDB,
    ):
        self.code_root = Path(code_root)
        self.data_root = Path(data_root)
        self.db = db

    # ------------------------------------------------------------------
    # Salvataggio run
    # ------------------------------------------------------------------

    def save_run(
        self,
        src_file: str | Path,
        project_name: str,
        testtype_name: str,
        condition: str,
        notes: str = "",
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> tuple[int, Path]:
        """
        Copia il file sorgente nella directory corretta del data_root,
        scrive meta.json, registra il run nel DB.

        Restituisce (run_db_id, dest_dir).
        """
        src = Path(src_file)
        if not src.exists():
            raise FileNotFoundError(f"File sorgente non trovato: {src}")

        # --- calcola run_id provvisorio leggendo il DB -------------------
        # (il DB assegnerà il run_id definitivo; usiamo lo stesso calcolo)
        pid  = self.db._project_id(project_name)
        ttid = self.db._testtype_id(pid, testtype_name)
        run_id = self.db._next_run_id(pid, ttid)

        # --- crea directory destinazione ---------------------------------
        dir_name  = f"{run_id}_{condition}"
        dest_dir  = (
            self.data_root / "projects" / project_name / testtype_name / dir_name
        )
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest_file = dest_dir / f"data{src.suffix}"
        shutil.copy2(src, dest_file)

        # --- meta.json ---------------------------------------------------
        meta = RunMeta(
            run_id    = run_id,
            project   = project_name,
            testtype  = testtype_name,
            condition = condition,
            date      = datetime.now().isoformat(timespec="seconds"),
            notes     = notes,
            tags      = tags or [],
            extra     = extra or {},
        )
        (dest_dir / "meta.json").write_text(
            json.dumps(meta.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # --- path relativo al data_root per il DB -----------------------
        data_path = str(dest_file.relative_to(self.data_root))

        run_db_id = self.db.add_run(
            project_name  = project_name,
            testtype_name = testtype_name,
            condition     = condition,
            data_path     = data_path,
            notes         = notes,
            tags          = tags,
            extra         = extra,
        )

        return run_db_id, dest_dir

    def load_run(self, run_db_id: int) -> tuple[Path, RunMeta]:
        """
        Restituisce (path_al_file_dati, RunMeta) dato un run_db_id.
        Lancia FileNotFoundError se il file non esiste (non ancora scaricato via DVC).
        """
        run = self.db.get_run(run_db_id)
        if not run:
            raise ValueError(f"Run {run_db_id} non trovato nel DB.")

        data_file = self.data_root / run["data_path"]
        if not data_file.exists():
            raise FileNotFoundError(
                f"File dati non trovato: {data_file}\n"
                f"Prova a eseguire: dvc pull"
            )

        meta = RunMeta(
            run_id    = run["run_id"],
            project   = run["project"],
            testtype  = run["testtype"],
            condition = run["condition"],
            date      = run["date"],
            notes     = run["notes"],
            tags      = run["tags"],
            extra     = run["extra"],
        )
        return data_file, meta

    def delete_run_files(self, run_db_id: int, also_db: bool = True):
        """Rimuove i file dal disco e opzionalmente il record dal DB."""
        run = self.db.get_run(run_db_id)
        if not run:
            raise ValueError(f"Run {run_db_id} non trovato nel DB.")

        data_file = self.data_root / run["data_path"]
        run_dir   = data_file.parent
        if run_dir.exists():
            shutil.rmtree(run_dir)

        if also_db:
            self.db.delete_run(run_db_id)

    # ------------------------------------------------------------------
    # Gestione project.json (nel code_root)
    # ------------------------------------------------------------------

    def write_project_config(self, config: ProjectConfig):
        """Scrive/aggiorna il project.json nel code_root."""
        proj_dir = self.code_root / "projects" / config.name
        proj_dir.mkdir(parents=True, exist_ok=True)
        (proj_dir / "project.json").write_text(
            json.dumps(config.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def read_project_config(self, project_name: str) -> ProjectConfig:
        path = self.code_root / "projects" / project_name / "project.json"
        if not path.exists():
            raise FileNotFoundError(f"project.json non trovato per '{project_name}'")
        data = json.loads(path.read_text(encoding="utf-8"))
        return ProjectConfig.from_dict(data)

    # ------------------------------------------------------------------
    # Git commands
    # ------------------------------------------------------------------

    def git_status(self) -> dict:
        return self._run_cmd(["git", "status", "--short"], cwd=self.code_root)

    def git_add_all(self) -> dict:
        return self._run_cmd(["git", "add", "-A"], cwd=self.code_root)

    def git_commit(self, message: str) -> dict:
        return self._run_cmd(
            ["git", "commit", "-m", message], cwd=self.code_root
        )

    def git_push(self, remote: str = "origin", branch: str = "main") -> dict:
        return self._run_cmd(
            ["git", "push", remote, branch], cwd=self.code_root
        )

    def git_pull(self) -> dict:
        return self._run_cmd(["git", "pull"], cwd=self.code_root)

    def git_log(self, n: int = 10) -> dict:
        return self._run_cmd(
            ["git", "log", f"-{n}", "--oneline"], cwd=self.code_root
        )

    # ------------------------------------------------------------------
    # DVC commands
    # ------------------------------------------------------------------

    def dvc_add(self, path: str | Path) -> dict:
        """Traccia un file o directory con DVC."""
        return self._run_cmd(["dvc", "add", str(path)], cwd=self.data_root)

    def dvc_push(self, remote: str | None = None) -> dict:
        cmd = ["dvc", "push"]
        if remote:
            cmd += ["--remote", remote]
        return self._run_cmd(cmd, cwd=self.data_root)

    def dvc_pull(self, path: str | Path | None = None) -> dict:
        cmd = ["dvc", "pull"]
        if path:
            cmd.append(str(path))
        return self._run_cmd(cmd, cwd=self.data_root)

    def dvc_status(self) -> dict:
        return self._run_cmd(["dvc", "status"], cwd=self.data_root)

    def dvc_diff(self) -> dict:
        return self._run_cmd(["dvc", "diff"], cwd=self.data_root)

    # ------------------------------------------------------------------
    # Workflow combinato: salva run + traccia con DVC + commit codice
    # ------------------------------------------------------------------

    def save_and_track(
        self,
        src_file: str | Path,
        project_name: str,
        testtype_name: str,
        condition: str,
        commit_message: str | None = None,
        notes: str = "",
        tags: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict:
        """
        Pipeline completa:
          1. Salva il file dati su disco
          2. dvc add sulla directory del run
          3. git add + commit del .dvc pointer nel code_root
        Restituisce un dict con esito di ogni step.
        """
        results: dict[str, Any] = {}

        # 1. salva
        run_db_id, dest_dir = self.save_run(
            src_file, project_name, testtype_name, condition,
            notes=notes, tags=tags, extra=extra,
        )
        results["run_db_id"] = run_db_id
        results["dest_dir"]  = str(dest_dir)

        # 2. dvc add
        results["dvc_add"] = self.dvc_add(dest_dir)

        # 3. git commit del pointer .dvc
        msg = commit_message or (
            f"add run {run_db_id} [{project_name}/{testtype_name}/{condition}]"
        )
        self.git_add_all()
        results["git_commit"] = self.git_commit(msg)

        return results

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _run_cmd(cmd: list[str], cwd: Path) -> dict:
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=120,
            )
            return {
                "ok":     proc.returncode == 0,
                "output": proc.stdout.strip(),
                "error":  proc.stderr.strip(),
            }
        except FileNotFoundError:
            tool = cmd[0]
            return {
                "ok":     False,
                "output": "",
                "error":  f"'{tool}' non trovato. Installalo e assicurati che sia nel PATH.",
            }
        except subprocess.TimeoutExpired:
            return {
                "ok":     False,
                "output": "",
                "error":  f"Timeout eseguendo: {' '.join(cmd)}",
            }
