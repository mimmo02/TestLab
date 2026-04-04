"""
testlab.core.plugin_loader
--------------------------
Carica dinamicamente gli script da scripts/ in base al nome dichiarato
in project.json sotto la chiave "testtypes".

Flusso di risoluzione:
  project.json["testtypes"]["rendimento"] == "rendimento_std"
      → cerca scripts/rendimento_std.py
      → importa la classe TestType
      → verifica che sia sottoclasse di BaseTestType
      → restituisce un'istanza

In caso di errore cade sul DefaultTestType (lettura CSV generica).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from .interfaces import BaseTestType, RunMeta
import pandas as pd


# ---------------------------------------------------------------------------
# Default fallback
# ---------------------------------------------------------------------------

class DefaultTestType(BaseTestType):
    """
    Fallback generico usato quando lo script condiviso non esiste o
    non è valido. Legge CSV con separatore automatico e produce
    grafici lineari su tutte le colonne numeriche.
    """

    def read(self, filepath: str | Path) -> pd.DataFrame:
        fp = Path(filepath)
        if fp.suffix.lower() == ".csv":
            # prova prima virgola, poi punto e virgola
            for sep in (",", ";", "\t"):
                try:
                    df = pd.read_csv(fp, sep=sep)
                    if len(df.columns) > 1:
                        return df
                except Exception:
                    continue
        # fallback: legge come testo e prova a parsarlo
        return pd.read_csv(filepath, sep=None, engine="python")

    def plot_single(self, df: pd.DataFrame, meta: RunMeta):
        try:
            import plotly.graph_objects as go
        except ImportError:
            raise ImportError("plotly è richiesto: pip install plotly")

        fig = go.Figure()
        num_cols = df.select_dtypes("number").columns
        x = df.index if len(num_cols) < 2 else df[num_cols[0]]
        for col in (num_cols[1:] if len(num_cols) > 1 else num_cols):
            fig.add_trace(go.Scatter(x=x, y=df[col], name=col))
        fig.update_layout(title=f"{meta.label} (default reader)")
        return fig

    def plot_compare(self, runs: list[tuple[pd.DataFrame, RunMeta]]):
        try:
            import plotly.graph_objects as go
        except ImportError:
            raise ImportError("plotly è richiesto: pip install plotly")

        fig = go.Figure()
        for df, meta in runs:
            num_cols = df.select_dtypes("number").columns
            if len(num_cols) == 0:
                continue
            x = df.index if len(num_cols) < 2 else df[num_cols[0]]
            y_col = num_cols[1] if len(num_cols) > 1 else num_cols[0]
            fig.add_trace(go.Scatter(x=x, y=df[y_col], name=meta.label))
        fig.update_layout(title="Confronto (default reader)")
        return fig


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class PluginLoader:
    """
    Gestisce il caricamento degli script condivisi da scripts/.

    Utilizzo:
        loader = PluginLoader(scripts_dir=Path("testlab/scripts"))
        plugin = loader.get("rendimento_std")
        df = plugin.read("data.csv")
    """

    def __init__(self, scripts_dir: Path):
        self.scripts_dir = Path(scripts_dir)
        self._cache: dict[str, BaseTestType] = {}

    # ------------------------------------------------------------------
    # API pubblica
    # ------------------------------------------------------------------

    def get(self, script_name: str) -> BaseTestType:
        """
        Restituisce un'istanza del TestType definito in scripts/<script_name>.py.
        Usa la cache in-process per evitare reload multipli.
        Cade sul DefaultTestType se il file non esiste o è invalido.
        """
        if script_name in self._cache:
            return self._cache[script_name]

        instance = self._load(script_name)
        self._cache[script_name] = instance
        return instance

    def get_for_project(
        self,
        project_config,          # ProjectConfig
        testtype_name: str,
    ) -> BaseTestType:
        """
        Risolve il nome dello script partendo dal ProjectConfig e dal nome
        del testtype richiesto.
        """
        script_name = project_config.testtypes.get(testtype_name)
        if not script_name:
            print(
                f"[PluginLoader] testtype '{testtype_name}' non dichiarato "
                f"in project.json di '{project_config.name}'. "
                f"Uso DefaultTestType."
            )
            return DefaultTestType()
        return self.get(script_name)

    def available_scripts(self) -> list[str]:
        """Restituisce i nomi degli script presenti in scripts/ (senza .py)."""
        return sorted(p.stem for p in self.scripts_dir.glob("*.py")
                      if not p.name.startswith("_"))

    def reload(self, script_name: str) -> BaseTestType:
        """Forza il reload di uno script (utile in sviluppo dal notebook)."""
        self._cache.pop(script_name, None)
        # rimuove il modulo dal sys.modules per permettere il reimport
        mod_key = f"testlab_script_{script_name}"
        sys.modules.pop(mod_key, None)
        return self.get(script_name)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _load(self, script_name: str) -> BaseTestType:
        script_path = self.scripts_dir / f"{script_name}.py"

        if not script_path.exists():
            print(
                f"[PluginLoader] Script '{script_name}.py' non trovato in "
                f"{self.scripts_dir}. Uso DefaultTestType."
            )
            return DefaultTestType()

        try:
            mod_key = f"testlab_script_{script_name}"
            spec = importlib.util.spec_from_file_location(mod_key, script_path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_key] = mod
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f"[PluginLoader] Errore caricando '{script_name}.py': {e}. "
                  f"Uso DefaultTestType.")
            return DefaultTestType()

        cls = getattr(mod, "TestType", None)
        if cls is None:
            print(
                f"[PluginLoader] '{script_name}.py' non definisce la classe "
                f"'TestType'. Uso DefaultTestType."
            )
            return DefaultTestType()

        if not (isinstance(cls, type) and issubclass(cls, BaseTestType)):
            print(
                f"[PluginLoader] 'TestType' in '{script_name}.py' non eredita "
                f"da BaseTestType. Uso DefaultTestType."
            )
            return DefaultTestType()

        try:
            return cls()
        except Exception as e:
            print(f"[PluginLoader] Errore istanziando TestType in "
                  f"'{script_name}.py': {e}. Uso DefaultTestType.")
            return DefaultTestType()
