"""
testlab.core.interfaces
-----------------------
Classi astratte che ogni script in scripts/ deve implementare.
Un file in scripts/ è valido se definisce una classe TestType
che eredita da BaseTestType e implementa tutti i metodi astratti.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


# ---------------------------------------------------------------------------
# Strutture dati condivise
# ---------------------------------------------------------------------------

@dataclass
class RunMeta:
    """Metadati associati a un singolo TestRun."""
    run_id: str                          # es. "003"
    project: str                         # es. "motore_v2"
    testtype: str                        # es. "rendimento"
    condition: str                       # es. "carico50"
    date: str = ""                       # ISO 8601 — valorizzato dal FileManager
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)   # campi liberi per il progetto

    @property
    def label(self) -> str:
        """Etichetta compatta per i grafici: id + condizione."""
        return f"{self.run_id} — {self.condition}"

    def to_dict(self) -> dict:
        return {
            "run_id":   self.run_id,
            "project":  self.project,
            "testtype": self.testtype,
            "condition": self.condition,
            "date":     self.date,
            "notes":    self.notes,
            "tags":     self.tags,
            "extra":    self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RunMeta":
        return cls(
            run_id    = d["run_id"],
            project   = d["project"],
            testtype  = d["testtype"],
            condition = d["condition"],
            date      = d.get("date", ""),
            notes     = d.get("notes", ""),
            tags      = d.get("tags", []),
            extra     = d.get("extra", {}),
        )


@dataclass
class ProjectConfig:
    """Configurazione di un progetto letta da project.json."""
    name: str
    description: str = ""
    # mappa testtype_name -> nome script condiviso (senza .py)
    # es. {"rendimento": "rendimento_std", "termico": "termico_std"}
    testtypes: dict[str, str] = field(default_factory=dict)
    created: str = ""
    dvc_remote: str = ""      # nome del remote DVC configurato per questo progetto

    def to_dict(self) -> dict:
        return {
            "name":        self.name,
            "description": self.description,
            "testtypes":   self.testtypes,
            "created":     self.created,
            "dvc_remote":  self.dvc_remote,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProjectConfig":
        return cls(
            name        = d["name"],
            description = d.get("description", ""),
            testtypes   = d.get("testtypes", {}),
            created     = d.get("created", ""),
            dvc_remote  = d.get("dvc_remote", ""),
        )


# ---------------------------------------------------------------------------
# Interfaccia plugin
# ---------------------------------------------------------------------------

class BaseTestType(ABC):
    """
    Interfaccia che ogni script condiviso in scripts/ deve implementare.

    Esempio minimo di scripts/rendimento_std.py:

        import pandas as pd
        import plotly.graph_objects as go
        from testlab.core.interfaces import BaseTestType, RunMeta

        class TestType(BaseTestType):
            def read(self, filepath):
                df = pd.read_csv(filepath, sep=";")
                df.columns = ["time_s", "rpm", "rendimento_pct"]
                return df

            def plot_single(self, df, meta):
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df["time_s"], y=df["rendimento_pct"]))
                fig.update_layout(title=meta.label)
                return fig

            def plot_compare(self, runs):
                fig = go.Figure()
                for df, meta in runs:
                    fig.add_trace(go.Scatter(
                        x=df["time_s"], y=df["rendimento_pct"], name=meta.label
                    ))
                return fig
    """

    # --- lettura ----------------------------------------------------------------

    @abstractmethod
    def read(self, filepath: str | Path) -> pd.DataFrame:
        """
        Legge il file dati e restituisce un DataFrame normalizzato.
        Deve sollevare ValueError se il file non è nel formato atteso.
        """
        ...

    def validate(self, df: pd.DataFrame) -> tuple[bool, str]:
        """
        Validazione opzionale dopo la lettura.
        Restituisce (True, "") se ok, oppure (False, "messaggio errore").
        Override consigliato per aggiungere controlli specifici del testtype.
        """
        if df.empty:
            return False, "DataFrame vuoto dopo la lettura."
        return True, ""

    # --- visualizzazione --------------------------------------------------------

    @abstractmethod
    def plot_single(self, df: pd.DataFrame, meta: RunMeta):
        """
        Grafico per un singolo TestRun.
        Deve restituire un oggetto plotly.graph_objects.Figure.
        """
        ...

    @abstractmethod
    def plot_compare(self, runs: list[tuple[pd.DataFrame, RunMeta]]):
        """
        Grafico sovrapposto per confrontare più TestRun.
        Deve restituire un oggetto plotly.graph_objects.Figure.
        Il parametro runs è una lista di tuple (DataFrame, RunMeta).
        """
        ...

    # --- summary opzionale ------------------------------------------------------

    def summary(self, df: pd.DataFrame, meta: RunMeta) -> dict[str, Any]:
        """
        Restituisce un dizionario di metriche sintetiche (es. max, mean, …).
        Override opzionale — di default restituisce le statistiche base di pandas.
        Usato dalla dashboard per la tabella di confronto KPI.
        """
        return df.describe().to_dict()
