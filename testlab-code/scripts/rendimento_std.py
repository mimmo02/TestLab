"""
scripts/rendimento_std.py
--------------------------
Script condiviso per test di rendimento con formato CSV standard:
    time_s ; rpm ; coppia_nm ; potenza_kw ; rendimento_pct

Usato da tutti i progetti che producono questo tipo di dati.
Dichiaralo in project.json:
    "testtypes": { "rendimento": "rendimento_std" }
"""

from __future__ import annotations
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

from testlab.core.interfaces import BaseTestType, RunMeta


class TestType(BaseTestType):

    REQUIRED_COLS = {"time_s", "rpm", "coppia_nm", "potenza_kw", "rendimento_pct"}

    # ------------------------------------------------------------------
    # Lettura
    # ------------------------------------------------------------------

    def read(self, filepath: str | Path) -> pd.DataFrame:
        df = pd.read_csv(
            filepath,
            sep=";",
            decimal=",",        # formato europeo
            skiprows=0,
            encoding="utf-8",
        )
        # normalizza nomi colonne (strip, lower)
        df.columns = [c.strip().lower() for c in df.columns]

        if not self.REQUIRED_COLS.issubset(df.columns):
            missing = self.REQUIRED_COLS - set(df.columns)
            raise ValueError(f"Colonne mancanti nel file: {missing}")

        # ordina per tempo
        df = df.sort_values("time_s").reset_index(drop=True)
        return df

    def validate(self, df: pd.DataFrame) -> tuple[bool, str]:
        if df["rendimento_pct"].max() > 100:
            return False, "rendimento_pct supera 100%."
        if df["time_s"].is_monotonic_increasing is False:
            return False, "time_s non è monotonicamente crescente."
        return True, ""

    # ------------------------------------------------------------------
    # Visualizzazione
    # ------------------------------------------------------------------

    def plot_single(self, df: pd.DataFrame, meta: RunMeta) -> go.Figure:
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df["time_s"], y=df["rendimento_pct"],
            name="Rendimento %", line=dict(color="#1D9E75", width=2),
        ))
        fig.add_trace(go.Scatter(
            x=df["time_s"], y=df["rpm"] / df["rpm"].max() * 100,
            name="RPM (norm.)", line=dict(color="#7F77DD", width=1.5, dash="dot"),
            yaxis="y",
        ))

        fig.update_layout(
            title=f"Rendimento — {meta.label}",
            xaxis_title="Tempo [s]",
            yaxis_title="Rendimento [%]",
            legend=dict(orientation="h", y=-0.2),
            template="plotly_white",
        )
        return fig

    def plot_compare(self, runs: list[tuple[pd.DataFrame, RunMeta]]) -> go.Figure:
        fig = go.Figure()
        for df, meta in runs:
            fig.add_trace(go.Scatter(
                x=df["time_s"],
                y=df["rendimento_pct"],
                name=meta.label,
                mode="lines",
            ))

        fig.update_layout(
            title="Confronto rendimento",
            xaxis_title="Tempo [s]",
            yaxis_title="Rendimento [%]",
            legend=dict(orientation="h", y=-0.2),
            template="plotly_white",
        )
        return fig

    def summary(self, df: pd.DataFrame, meta: RunMeta) -> dict:
        return {
            "run":              meta.label,
            "rendimento_max":   round(df["rendimento_pct"].max(), 2),
            "rendimento_medio": round(df["rendimento_pct"].mean(), 2),
            "rpm_max":          round(df["rpm"].max(), 0),
            "potenza_max_kw":   round(df["potenza_kw"].max(), 2),
            "durata_s":         round(df["time_s"].iloc[-1], 1),
        }
