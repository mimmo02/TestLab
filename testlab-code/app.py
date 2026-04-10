"""
TestLab — GUI standalone
Lancia con: python app.py
Posizione: testlab-code/app.py
"""

from __future__ import annotations

import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent          # testlab-code/
sys.path.insert(0, str(ROOT))

from testlab.core import TestLabDB, FileManager, PluginLoader
from testlab.core import ProjectConfig

# ── Costanti ──────────────────────────────────────────────────────────────────
CODE_ROOT   = ROOT
DATA_ROOT   = ROOT.parent / "testlab-data"
DB_PATH     = ROOT / "db" / "testlab.sqlite"
SCRIPTS_DIR = ROOT / "scripts"

DATA_ROOT.mkdir(parents=True, exist_ok=True)

db     = TestLabDB(DB_PATH)
loader = PluginLoader(SCRIPTS_DIR)
fm     = FileManager(CODE_ROOT, DATA_ROOT, db)

# ── Palette ───────────────────────────────────────────────────────────────────
C = {
    "primary": "#534AB7",
    "teal":    "#1D9E75",
    "coral":   "#D85A30",
    "amber":   "#BA7517",
    "gray":    "#888780",
    "bg":      "#F7F6F2",
    "bg2":     "#EEECEA",
    "border":  "#D3D1C7",
    "white":   "#FFFFFF",
    "text":    "#1A1A18",
    "muted":   "#6B6A65",
    "success": "#EAF3DE",
    "success_fg": "#3B6D11",
    "error":   "#FCEBEB",
    "error_fg":"#A32D2D",
    "warn":    "#FAEEDA",
    "warn_fg": "#854F0B",
}

# ── Helpers UI ────────────────────────────────────────────────────────────────

def styled_btn(parent, text, command, color=None, width=18):
    color = color or C["primary"]
    b = tk.Button(
        parent, text=text, command=command,
        bg=color, fg="white", relief="flat",
        font=("Helvetica", 10, "bold"),
        padx=10, pady=5, cursor="hand2",
        activebackground=color, activeforeground="white",
        width=width,
    )
    return b


def labeled_entry(parent, label, row, col=0, width=30, colspan=1):
    tk.Label(parent, text=label, bg=C["bg"], fg=C["text"],
             font=("Helvetica", 10)).grid(
        row=row, column=col, sticky="w", padx=(0, 6), pady=4)
    var = tk.StringVar()
    e = ttk.Entry(parent, textvariable=var, width=width)
    e.grid(row=row, column=col + 1, sticky="ew", pady=4,
           columnspan=colspan, padx=(0, 12))
    return var


def section_label(parent, text, color=None):
    color = color or C["primary"]
    f = tk.Frame(parent, bg=C["bg"])
    tk.Label(f, text=text, bg=C["bg"], fg=color,
             font=("Helvetica", 13, "bold")).pack(side="left")
    tk.Frame(f, bg=color, height=2).pack(side="bottom", fill="x")
    return f


class LogBox:
    """Casella di log scrollabile con colori per tipo messaggio."""

    COLORS = {
        "info":    ("#185FA5", "ℹ"),
        "success": ("#3B6D11", "✓"),
        "warning": ("#854F0B", "⚠"),
        "error":   ("#A32D2D", "✗"),
    }

    def __init__(self, parent, height=8):
        self.txt = scrolledtext.ScrolledText(
            parent, height=height, state="disabled",
            bg="#FAFAF8", fg=C["text"],
            font=("Courier", 10), relief="flat",
            bd=1, wrap="word",
        )
        self.txt.pack(fill="x", padx=0, pady=(4, 0))
        for kind, (fg, _) in self.COLORS.items():
            self.txt.tag_config(kind, foreground=fg)

    def append(self, msg: str, kind: str = "info"):
        _, icon = self.COLORS.get(kind, ("#333", "·"))
        self.txt.config(state="normal")
        self.txt.insert("end", f"{icon} {msg}\n", kind)
        self.txt.see("end")
        self.txt.config(state="disabled")

    def clear(self):
        self.txt.config(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.config(state="disabled")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Gestione progetti e testtype
# ══════════════════════════════════════════════════════════════════════════════

class TabProjects(ttk.Frame):
    def __init__(self, notebook):
        super().__init__(notebook, padding=16)
        self.columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        # ── Crea progetto ────────────────────────────────────────────────────
        section_label(self, "Nuovo progetto").grid(
            row=0, column=0, sticky="ew", pady=(0, 8))

        frm = tk.Frame(self, bg=C["bg"])
        frm.grid(row=1, column=0, sticky="ew")
        frm.columnconfigure(1, weight=1)

        self.v_name  = labeled_entry(frm, "Nome:",        0, width=28)
        self.v_desc  = labeled_entry(frm, "Descrizione:", 1, width=42)
        self.v_dvc   = labeled_entry(frm, "DVC remote:",  2, width=28)

        styled_btn(frm, "Crea progetto", self._create_project,
                   color=C["primary"]).grid(
            row=3, column=1, sticky="w", pady=8)

        ttk.Separator(self, orient="horizontal").grid(
            row=2, column=0, sticky="ew", pady=12)

        # ── Aggiungi testtype ────────────────────────────────────────────────
        section_label(self, "Nuovo testtype", color=C["teal"]).grid(
            row=3, column=0, sticky="ew", pady=(0, 8))

        frm2 = tk.Frame(self, bg=C["bg"])
        frm2.grid(row=4, column=0, sticky="ew")
        frm2.columnconfigure(1, weight=1)

        tk.Label(frm2, text="Progetto:", bg=C["bg"],
                 font=("Helvetica", 10)).grid(row=0, column=0, sticky="w",
                                               padx=(0, 6), pady=4)
        self.proj_var = tk.StringVar()
        self.proj_cb  = ttk.Combobox(frm2, textvariable=self.proj_var,
                                      width=26, state="readonly")
        self.proj_cb.grid(row=0, column=1, sticky="w", pady=4, padx=(0, 12))

        self.v_ttname = labeled_entry(frm2, "TestType:", 1, width=22)

        tk.Label(frm2, text="Script:", bg=C["bg"],
                 font=("Helvetica", 10)).grid(row=2, column=0, sticky="w",
                                               padx=(0, 6), pady=4)
        self.script_var = tk.StringVar()
        self.script_cb  = ttk.Combobox(frm2, textvariable=self.script_var,
                                        width=30, state="readonly")
        self.script_cb.grid(row=2, column=1, sticky="w", pady=4, padx=(0, 12))
        self._refresh_scripts()

        styled_btn(frm2, "Aggiungi testtype", self._add_testtype,
                   color=C["teal"]).grid(row=3, column=1, sticky="w", pady=8)

        ttk.Separator(self, orient="horizontal").grid(
            row=5, column=0, sticky="ew", pady=12)

        # ── Lista progetti ───────────────────────────────────────────────────
        section_label(self, "Progetti esistenti", color=C["gray"]).grid(
            row=6, column=0, sticky="ew", pady=(0, 6))

        tree_frame = tk.Frame(self, bg=C["bg"])
        tree_frame.grid(row=7, column=0, sticky="ew")

        cols = ("Nome", "Descrizione", "DVC remote", "TestType")
        self.tree = ttk.Treeview(tree_frame, columns=cols,
                                  show="headings", height=7)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=160 if c == "Descrizione" else 120)
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=sb.set)

        styled_btn(self, "↺  Aggiorna lista", self._refresh_tree,
                   color=C["gray"], width=18).grid(
            row=8, column=0, sticky="w", pady=6)

        # ── Log ──────────────────────────────────────────────────────────────
        self.log = LogBox(self, height=5)

        self._refresh_tree()
        self._refresh_projects_cb()

    # ── Actions ──────────────────────────────────────────────────────────────

    def _create_project(self):
        name = self.v_name.get().strip()
        if not name:
            self.log.append("Inserisci un nome per il progetto.", "warning")
            return
        try:
            db.add_project(name, self.v_desc.get().strip(),
                           self.v_dvc.get().strip())
            fm.write_project_config(ProjectConfig(
                name=name,
                description=self.v_desc.get().strip(),
                dvc_remote=self.v_dvc.get().strip(),
            ))
            self.log.append(f"Progetto '{name}' creato.", "success")
            self.v_name.set(""); self.v_desc.set(""); self.v_dvc.set("")
            self._refresh_tree()
            self._refresh_projects_cb()
        except Exception as e:
            self.log.append(str(e), "error")

    def _add_testtype(self):
        proj = self.proj_var.get()
        tt   = self.v_ttname.get().strip()
        sc   = self.script_var.get()
        if not proj or not tt or not sc:
            self.log.append("Compila tutti i campi.", "warning")
            return
        try:
            db.add_testtype(proj, tt, sc)
            # aggiorna anche project.json
            cfg = fm.read_project_config(proj)
            cfg.testtypes[tt] = sc
            fm.write_project_config(cfg)
            self.log.append(f"TestType '{tt}' → '{sc}' aggiunto a '{proj}'.",
                            "success")
            self.v_ttname.set("")
            self._refresh_tree()
        except Exception as e:
            self.log.append(str(e), "error")

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for p in db.list_projects():
            tts = [t["name"] for t in db.list_testtypes(p["name"])]
            self.tree.insert("", "end", values=(
                p["name"], p["description"],
                p["dvc_remote"], ", ".join(tts),
            ))

    def _refresh_projects_cb(self):
        names = [p["name"] for p in db.list_projects()]
        self.proj_cb["values"] = names

    def _refresh_scripts(self):
        avail = [p.stem for p in SCRIPTS_DIR.glob("*.py")
                 if not p.name.startswith("_")]
        self.script_cb["values"] = avail
        if avail:
            self.script_var.set(avail[0])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Importazione run
# ══════════════════════════════════════════════════════════════════════════════

class TabImport(ttk.Frame):
    def __init__(self, notebook):
        super().__init__(notebook, padding=16)
        self.columnconfigure(1, weight=1)
        self._build()

    def _build(self):
        section_label(self, "Importa run", color=C["teal"]).grid(
            row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        # Progetto
        tk.Label(self, text="Progetto:", bg=C["bg"],
                 font=("Helvetica", 10)).grid(row=1, column=0, sticky="w",
                                               padx=(0, 6), pady=4)
        self.proj_var = tk.StringVar()
        self.proj_cb  = ttk.Combobox(self, textvariable=self.proj_var,
                                      width=26, state="readonly")
        self.proj_cb.grid(row=1, column=1, sticky="w", pady=4, padx=(0, 12))
        self.proj_cb.bind("<<ComboboxSelected>>", self._on_proj)

        # TestType
        tk.Label(self, text="TestType:", bg=C["bg"],
                 font=("Helvetica", 10)).grid(row=2, column=0, sticky="w",
                                               padx=(0, 6), pady=4)
        self.tt_var = tk.StringVar()
        self.tt_cb  = ttk.Combobox(self, textvariable=self.tt_var,
                                    width=26, state="readonly")
        self.tt_cb.grid(row=2, column=1, sticky="w", pady=4, padx=(0, 12))

        # Condizione
        self.v_cond = labeled_entry(self, "Condizione:", 3, width=28)

        # File path con bottone sfoglia
        tk.Label(self, text="File dati:", bg=C["bg"],
                 font=("Helvetica", 10)).grid(row=4, column=0, sticky="w",
                                               padx=(0, 6), pady=4)
        self.v_fpath = tk.StringVar()
        ttk.Entry(self, textvariable=self.v_fpath, width=44).grid(
            row=4, column=1, sticky="ew", pady=4, padx=(0, 6))
        styled_btn(self, "Sfoglia…", self._browse, color=C["gray"],
                   width=10).grid(row=4, column=2, sticky="w")

        # Note
        tk.Label(self, text="Note:", bg=C["bg"],
                 font=("Helvetica", 10)).grid(row=5, column=0, sticky="nw",
                                               padx=(0, 6), pady=4)
        self.txt_notes = tk.Text(self, height=3, width=48,
                                  font=("Helvetica", 10),
                                  relief="flat", bd=1, bg=C["white"])
        self.txt_notes.grid(row=5, column=1, columnspan=2,
                             sticky="ew", pady=4)

        # Tag
        self.v_tags = labeled_entry(self, "Tag:", 6, width=40, colspan=2)

        # DVC checkbox
        self.dvc_var = tk.BooleanVar(value=True)
        tk.Checkbutton(self, text="Traccia con DVC + git commit",
                        variable=self.dvc_var,
                        bg=C["bg"], font=("Helvetica", 10)).grid(
            row=7, column=1, sticky="w", pady=4)

        styled_btn(self, "Importa run", self._import,
                   color=C["teal"], width=16).grid(
            row=8, column=1, sticky="w", pady=10)

        self.log = LogBox(self, height=7)

        self._refresh()

    def _refresh(self):
        self.proj_cb["values"] = [p["name"] for p in db.list_projects()]

    def _on_proj(self, _=None):
        p = self.proj_var.get()
        tts = [t["name"] for t in db.list_testtypes(p)]
        self.tt_cb["values"] = tts
        self.tt_var.set("")

    def _browse(self):
        path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt"),
                       ("All files", "*.*")])
        if path:
            self.v_fpath.set(path)

    def _import(self):
        proj = self.proj_var.get()
        tt   = self.tt_var.get()
        fp   = Path(self.v_fpath.get().strip())
        cond = self.v_cond.get().strip()

        if not proj or not tt:
            self.log.append("Seleziona progetto e testtype.", "warning")
            return
        if not fp.exists():
            self.log.append(f"File non trovato: {fp}", "error")
            return

        tags = [t.strip() for t in self.v_tags.get().split(",") if t.strip()]
        notes = self.txt_notes.get("1.0", "end").strip()

        def task():
            try:
                if self.dvc_var.get():
                    res = fm.save_and_track(fp, proj, tt, cond,
                                            notes=notes, tags=tags)
                    self.log.append(
                        f"Run {res['run_db_id']} importato e tracciato.",
                        "success")
                    if not res["git_commit"]["ok"]:
                        self.log.append(
                            "Git commit: " + res["git_commit"]["error"],
                            "warning")
                else:
                    rid, dest = fm.save_run(fp, proj, tt, cond,
                                            notes=notes, tags=tags)
                    self.log.append(f"Run {rid} importato in {dest}.",
                                    "success")
                self.v_fpath.set("")
                self.v_cond.set("")
                self.v_tags.set("")
                self.txt_notes.delete("1.0", "end")
            except Exception as e:
                self.log.append(str(e), "error")

        threading.Thread(target=task, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Visualizzazione singolo run
# ══════════════════════════════════════════════════════════════════════════════

class TabView(ttk.Frame):
    def __init__(self, notebook):
        super().__init__(notebook, padding=16)
        self.columnconfigure(1, weight=1)
        self._build()

    def _build(self):
        section_label(self, "Visualizzazione singolo run",
                       color=C["teal"]).grid(
            row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        # Selettori a cascata
        tk.Label(self, text="Progetto:", bg=C["bg"],
                 font=("Helvetica", 10)).grid(row=1, column=0, sticky="w",
                                               padx=(0, 6), pady=4)
        self.proj_var = tk.StringVar()
        self.proj_cb  = ttk.Combobox(self, textvariable=self.proj_var,
                                      width=24, state="readonly")
        self.proj_cb.grid(row=1, column=1, sticky="w", pady=4, padx=(0,12))
        self.proj_cb.bind("<<ComboboxSelected>>", self._on_proj)

        tk.Label(self, text="TestType:", bg=C["bg"],
                 font=("Helvetica", 10)).grid(row=2, column=0, sticky="w",
                                               padx=(0, 6), pady=4)
        self.tt_var = tk.StringVar()
        self.tt_cb  = ttk.Combobox(self, textvariable=self.tt_var,
                                    width=24, state="readonly")
        self.tt_cb.grid(row=2, column=1, sticky="w", pady=4, padx=(0,12))
        self.tt_cb.bind("<<ComboboxSelected>>", self._on_tt)

        tk.Label(self, text="Run:", bg=C["bg"],
                 font=("Helvetica", 10)).grid(row=3, column=0, sticky="w",
                                               padx=(0, 6), pady=4)
        self.run_var = tk.StringVar()
        self.run_cb  = ttk.Combobox(self, textvariable=self.run_var,
                                     width=40, state="readonly")
        self.run_cb.grid(row=3, column=1, sticky="w", pady=4, padx=(0,12))

        styled_btn(self, "Visualizza", self._plot,
                   color=C["primary"], width=14).grid(
            row=4, column=1, sticky="w", pady=8)

        # KPI box
        tk.Label(self, text="KPI:", bg=C["bg"],
                 font=("Helvetica", 10, "bold")).grid(
            row=5, column=0, sticky="nw", padx=(0, 6), pady=4)
        self.kpi_txt = scrolledtext.ScrolledText(
            self, height=10, width=36, state="disabled",
            bg=C["bg2"], font=("Courier", 10), relief="flat", bd=1)
        self.kpi_txt.grid(row=5, column=1, sticky="ew", pady=4)

        self.log = LogBox(self, height=4)
        self._refresh()

    def _refresh(self):
        self.proj_cb["values"] = [p["name"] for p in db.list_projects()]

    def _on_proj(self, _=None):
        p = self.proj_var.get()
        self.tt_cb["values"] = [t["name"] for t in db.list_testtypes(p)]
        self.tt_var.set("")
        self.run_cb["values"] = []

    def _on_tt(self, _=None):
        p  = self.proj_var.get()
        tt = self.tt_var.get()
        runs = db.list_runs(p, tt)
        self._run_map = {
            f"{r['run_id']} — {r['condition']}  [{r['date'][:10]}]": r["id"]
            for r in runs
        }
        self.run_cb["values"] = list(self._run_map.keys())

    def _plot(self):
        label = self.run_var.get()
        if not label:
            self.log.append("Seleziona un run.", "warning")
            return
        run_id = self._run_map.get(label)

        def task():
            try:
                data_file, meta = fm.load_run(run_id)
                proj_cfg = fm.read_project_config(meta.project)
                plugin   = loader.get_for_project(proj_cfg, meta.testtype)
                df       = plugin.read(data_file)
                ok, msg  = plugin.validate(df)
                if not ok:
                    self.log.append(f"Validazione: {msg}", "warning")
                summary = plugin.summary(df, meta)

                # KPI
                self.kpi_txt.config(state="normal")
                self.kpi_txt.delete("1.0", "end")
                for k, v in summary.items():
                    self.kpi_txt.insert("end", f"{k:<22} {v}\n")
                self.kpi_txt.config(state="disabled")

                # Grafico in finestra separata (plotly apre browser)
                fig = plugin.plot_single(df, meta)
                fig.show()
                self.log.append(
                    f"Run {meta.run_id} caricato ({len(df)} righe).",
                    "success")
            except Exception as e:
                self.log.append(str(e), "error")

        threading.Thread(target=task, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Comparazione run
# ══════════════════════════════════════════════════════════════════════════════

class TabCompare(ttk.Frame):
    def __init__(self, notebook):
        super().__init__(notebook, padding=16)
        self.columnconfigure(1, weight=1)
        self._run_map = {}
        self._build()

    def _build(self):
        section_label(self, "Comparazione run",
                       color=C["primary"]).grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        tk.Label(self, text="Progetto:", bg=C["bg"],
                 font=("Helvetica", 10)).grid(row=1, column=0, sticky="w",
                                               padx=(0, 6), pady=4)
        self.proj_var = tk.StringVar()
        self.proj_cb  = ttk.Combobox(self, textvariable=self.proj_var,
                                      width=24, state="readonly")
        self.proj_cb.grid(row=1, column=1, sticky="w", pady=4, padx=(0,12))
        self.proj_cb.bind("<<ComboboxSelected>>", self._on_proj)

        tk.Label(self, text="TestType:", bg=C["bg"],
                 font=("Helvetica", 10)).grid(row=2, column=0, sticky="w",
                                               padx=(0, 6), pady=4)
        self.tt_var = tk.StringVar()
        self.tt_cb  = ttk.Combobox(self, textvariable=self.tt_var,
                                    width=24, state="readonly")
        self.tt_cb.grid(row=2, column=1, sticky="w", pady=4, padx=(0,12))
        self.tt_cb.bind("<<ComboboxSelected>>", self._on_tt)

        tk.Label(self, text="Run\n(Ctrl+click\nper multipli):",
                 bg=C["bg"], font=("Helvetica", 10),
                 justify="left").grid(row=3, column=0, sticky="nw",
                                       padx=(0, 6), pady=4)
        self.run_lb = tk.Listbox(self, selectmode="multiple",
                                  width=50, height=8,
                                  font=("Courier", 10),
                                  bg=C["white"], relief="flat", bd=1)
        self.run_lb.grid(row=3, column=1, sticky="ew", pady=4)

        styled_btn(self, "Confronta", self._compare,
                   color=C["primary"], width=14).grid(
            row=4, column=1, sticky="w", pady=8)

        # KPI tabella
        tk.Label(self, text="KPI:", bg=C["bg"],
                 font=("Helvetica", 10, "bold")).grid(
            row=5, column=0, sticky="nw", padx=(0, 6), pady=4)
        self.kpi_txt = scrolledtext.ScrolledText(
            self, height=10, state="disabled",
            bg=C["bg2"], font=("Courier", 10), relief="flat", bd=1)
        self.kpi_txt.grid(row=5, column=1, sticky="ew", pady=4)

        self.log = LogBox(self, height=4)
        self._refresh()

    def _refresh(self):
        self.proj_cb["values"] = [p["name"] for p in db.list_projects()]

    def _on_proj(self, _=None):
        p = self.proj_var.get()
        self.tt_cb["values"] = [t["name"] for t in db.list_testtypes(p)]
        self.tt_var.set("")
        self.run_lb.delete(0, "end")

    def _on_tt(self, _=None):
        p  = self.proj_var.get()
        tt = self.tt_var.get()
        runs = db.list_runs(p, tt)
        self._run_map = {}
        self.run_lb.delete(0, "end")
        for r in runs:
            label = f"{r['run_id']} — {r['condition']}  [{r['date'][:10]}]"
            self._run_map[label] = r["id"]
            self.run_lb.insert("end", label)

    def _compare(self):
        indices = self.run_lb.curselection()
        if len(indices) < 2:
            self.log.append("Seleziona almeno 2 run.", "warning")
            return
        labels = [self.run_lb.get(i) for i in indices]
        ids    = [self._run_map[l] for l in labels]

        def task():
            try:
                import pandas as pd
                runs_data = []
                summaries = []
                for rid in ids:
                    data_file, meta = fm.load_run(rid)
                    proj_cfg = fm.read_project_config(meta.project)
                    plugin   = loader.get_for_project(proj_cfg, meta.testtype)
                    df       = plugin.read(data_file)
                    runs_data.append((df, meta))
                    summaries.append(plugin.summary(df, meta))
                    self.log.append(f"Caricato: {meta.label}", "info")

                # grafico
                proj_cfg = fm.read_project_config(runs_data[0][1].project)
                plugin   = loader.get_for_project(
                    proj_cfg, runs_data[0][1].testtype)
                fig = plugin.plot_compare(runs_data)
                fig.show()

                # KPI tabella testo
                df_kpi = pd.DataFrame(summaries)
                self.kpi_txt.config(state="normal")
                self.kpi_txt.delete("1.0", "end")
                # intestazione
                cols = list(df_kpi.columns)
                header = "  ".join(f"{c:<22}" for c in cols)
                self.kpi_txt.insert("end", header + "\n")
                self.kpi_txt.insert("end", "─" * len(header) + "\n")
                for _, row in df_kpi.iterrows():
                    line = "  ".join(f"{str(v):<22}" for v in row)
                    self.kpi_txt.insert("end", line + "\n")
                self.kpi_txt.config(state="disabled")
                self.log.append(
                    f"Confronto completato su {len(ids)} run.", "success")
            except Exception as e:
                self.log.append(str(e), "error")

        threading.Thread(target=task, daemon=True).start()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Esplora run
# ══════════════════════════════════════════════════════════════════════════════

class TabExplore(ttk.Frame):
    def __init__(self, notebook):
        super().__init__(notebook, padding=16)
        self.columnconfigure(1, weight=1)
        self._build()

    def _build(self):
        section_label(self, "Esplora run", color=C["gray"]).grid(
            row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10))

        tk.Label(self, text="Progetto:", bg=C["bg"],
                 font=("Helvetica", 10)).grid(row=1, column=0, sticky="w",
                                               padx=(0, 6), pady=4)
        self.proj_var = tk.StringVar()
        self.proj_cb  = ttk.Combobox(self, textvariable=self.proj_var,
                                      width=22, state="readonly")
        self.proj_cb.grid(row=1, column=1, sticky="w", pady=4, padx=(0,12))

        self.v_cond = labeled_entry(self, "Condizione:", 1, col=2, width=18)

        self.v_tags = labeled_entry(self, "Tag:", 2, col=0, width=18)

        styled_btn(self, "Cerca", self._search,
                   color=C["gray"], width=10).grid(
            row=2, column=2, sticky="w", pady=4)

        # Treeview risultati
        cols = ("id", "testtype", "run_id", "condizione",
                "data", "note", "tag")
        self.tree = ttk.Treeview(self, columns=cols,
                                  show="headings", height=14)
        widths = {"id": 40, "testtype": 110, "run_id": 60,
                  "condizione": 110, "data": 90, "note": 200, "tag": 120}
        for c in cols:
            self.tree.heading(c, text=c.capitalize())
            self.tree.column(c, width=widths.get(c, 100))
        self.tree.grid(row=3, column=0, columnspan=4,
                        sticky="nsew", pady=8)
        self.rowconfigure(3, weight=1)

        sb = ttk.Scrollbar(self, orient="vertical",
                            command=self.tree.yview)
        sb.grid(row=3, column=4, sticky="ns")
        self.tree.configure(yscrollcommand=sb.set)

        self.lbl_count = tk.Label(self, text="", bg=C["bg"],
                                   fg=C["muted"], font=("Helvetica", 10))
        self.lbl_count.grid(row=4, column=0, columnspan=4, sticky="w")

        self._refresh()

    def _refresh(self):
        self.proj_cb["values"] = [p["name"] for p in db.list_projects()]

    def _search(self):
        proj = self.proj_var.get()
        if not proj:
            messagebox.showwarning("TestLab", "Seleziona un progetto.")
            return
        tags = [t.strip() for t in self.v_tags.get().split(",") if t.strip()]
        cond = self.v_cond.get().strip() or None
        runs = db.list_runs(proj, condition=cond, tags=tags or None)

        self.tree.delete(*self.tree.get_children())
        for r in runs:
            note = r["notes"][:45] + "…" if len(r["notes"]) > 45 else r["notes"]
            self.tree.insert("", "end", values=(
                r["id"], r["testtype"], r["run_id"],
                r["condition"], r["date"][:10],
                note, ", ".join(r["tags"]),
            ))
        self.lbl_count.config(text=f"{len(runs)} run trovati")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — Git & DVC
# ══════════════════════════════════════════════════════════════════════════════

class TabGitDVC(ttk.Frame):
    def __init__(self, notebook):
        super().__init__(notebook, padding=16)
        self._build()

    def _build(self):
        section_label(self, "Controllo versione",
                       color=C["amber"]).grid(
            row=0, column=0, columnspan=4, sticky="ew", pady=(0, 10))

        # Git
        tk.Label(self, text="Git", bg=C["bg"],
                 font=("Helvetica", 11, "bold"),
                 fg=C["primary"]).grid(row=1, column=0, sticky="w", pady=(0,4))

        btn_row1 = tk.Frame(self, bg=C["bg"])
        btn_row1.grid(row=2, column=0, columnspan=4, sticky="w", pady=2)
        for label, cmd, color in [
            ("git status",  lambda: self._run(fm.git_status,  "git status"),  C["primary"]),
            ("git add -A",  lambda: self._run(fm.git_add_all, "git add"),     C["primary"]),
            ("git log",     lambda: self._run(fm.git_log,     "git log"),     C["primary"]),
            ("git pull",    lambda: self._run(fm.git_pull,    "git pull"),    C["teal"]),
        ]:
            styled_btn(btn_row1, label, cmd, color=color, width=14).pack(
                side="left", padx=(0, 8))

        # Commit row
        commit_row = tk.Frame(self, bg=C["bg"])
        commit_row.grid(row=3, column=0, columnspan=4, sticky="w", pady=6)
        tk.Label(commit_row, text="Messaggio:", bg=C["bg"],
                 font=("Helvetica", 10)).pack(side="left", padx=(0, 6))
        self.v_commit = tk.StringVar()
        ttk.Entry(commit_row, textvariable=self.v_commit,
                  width=40).pack(side="left", padx=(0, 8))
        styled_btn(commit_row, "git commit",
                   self._commit, color=C["teal"], width=13).pack(side="left",
                                                                   padx=(0, 8))
        styled_btn(commit_row, "git + dvc push",
                   self._push, color=C["teal"], width=16).pack(side="left")

        ttk.Separator(self, orient="horizontal").grid(
            row=4, column=0, columnspan=4, sticky="ew", pady=10)

        # DVC
        tk.Label(self, text="DVC", bg=C["bg"],
                 font=("Helvetica", 11, "bold"),
                 fg=C["amber"]).grid(row=5, column=0, sticky="w", pady=(0,4))

        btn_row2 = tk.Frame(self, bg=C["bg"])
        btn_row2.grid(row=6, column=0, columnspan=4, sticky="w", pady=2)
        for label, cmd, color in [
            ("dvc status", lambda: self._run(fm.dvc_status, "dvc status"), C["amber"]),
            ("dvc pull",   lambda: self._run(fm.dvc_pull,   "dvc pull"),   C["amber"]),
            ("dvc push",   lambda: self._run(fm.dvc_push,   "dvc push"),   C["teal"]),
        ]:
            styled_btn(btn_row2, label, cmd, color=color, width=14).pack(
                side="left", padx=(0, 8))

        ttk.Separator(self, orient="horizontal").grid(
            row=7, column=0, columnspan=4, sticky="ew", pady=10)

        tk.Label(self, text="Output comandi:", bg=C["bg"],
                 font=("Helvetica", 10, "bold")).grid(
            row=8, column=0, columnspan=4, sticky="w")
        self.log = LogBox(self, height=14)

    def _run(self, fn, label):
        def task():
            r = fn()
            kind = "success" if r["ok"] else "error"
            out  = r["output"] or r["error"] or "(nessun output)"
            self.log.append(f"[{label}]\n{out}", kind)
        threading.Thread(target=task, daemon=True).start()

    def _commit(self):
        msg = self.v_commit.get().strip()
        if not msg:
            self.log.append("Inserisci un messaggio di commit.", "warning")
            return
        self._run(lambda: fm.git_commit(msg), "git commit")

    def _push(self):
        self._run(fm.git_push, "git push")
        self._run(fm.dvc_push, "dvc push")


# ══════════════════════════════════════════════════════════════════════════════
# App principale
# ══════════════════════════════════════════════════════════════════════════════

class TestLabApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TestLab")
        self.geometry("900x720")
        self.minsize(800, 600)
        self.configure(bg=C["bg"])

        # Stile ttk
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame",       background=C["bg"])
        style.configure("TNotebook",    background=C["bg2"], borderwidth=0)
        style.configure("TNotebook.Tab",
                         background=C["bg2"], foreground=C["muted"],
                         padding=(14, 6), font=("Helvetica", 10))
        style.map("TNotebook.Tab",
                   background=[("selected", C["white"])],
                   foreground=[("selected", C["primary"])],
                   font=[("selected", ("Helvetica", 10, "bold"))])
        style.configure("Treeview",     background=C["white"],
                         fieldbackground=C["white"],
                         rowheight=24, font=("Helvetica", 10))
        style.configure("Treeview.Heading",
                         background=C["bg2"], foreground=C["text"],
                         font=("Helvetica", 10, "bold"))
        style.configure("TEntry",       fieldbackground=C["white"])
        style.configure("TCombobox",    fieldbackground=C["white"])
        style.configure("TSeparator",   background=C["border"])

        # Header
        header = tk.Frame(self, bg=C["primary"], height=48)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text="  TestLab", bg=C["primary"], fg="white",
                 font=("Helvetica", 16, "bold")).pack(side="left",
                                                        padx=12, pady=8)
        tk.Label(header,
                 text=f"  {CODE_ROOT}",
                 bg=C["primary"], fg="#C4C0F0",
                 font=("Helvetica", 9)).pack(side="left", pady=8)

        # Notebook
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=0, pady=0)

        self.tab_proj    = TabProjects(nb)
        self.tab_import  = TabImport(nb)
        self.tab_view    = TabView(nb)
        self.tab_compare = TabCompare(nb)
        self.tab_explore = TabExplore(nb)
        self.tab_git     = TabGitDVC(nb)

        nb.add(self.tab_proj,    text="  Progetti  ")
        nb.add(self.tab_import,  text="  Importa  ")
        nb.add(self.tab_view,    text="  Visualizza  ")
        nb.add(self.tab_compare, text="  Confronta  ")
        nb.add(self.tab_explore, text="  Esplora  ")
        nb.add(self.tab_git,     text="  Git & DVC  ")

        # Aggiorna i selettori quando si cambia tab
        def on_tab_change(event):
            tab = nb.index(nb.select())
            refresh_map = {
                1: self.tab_import._refresh,
                2: self.tab_view._refresh,
                3: self.tab_compare._refresh,
                4: self.tab_explore._refresh,
            }
            if tab in refresh_map:
                refresh_map[tab]()

        nb.bind("<<NotebookTabChanged>>", on_tab_change)


if __name__ == "__main__":
    app = TestLabApp()
    app.mainloop()
