"""
testlab.notebooks.widgets
--------------------------
Componenti ipywidgets riutilizzabili per il dashboard TestLab.
Ogni sezione del notebook importa da qui i propri blocchi UI.
"""

from __future__ import annotations

import ipywidgets as w
from IPython.display import display, clear_output, HTML
from pathlib import Path
from typing import Callable, Any

# Palette colori coerente con il progetto
COLORS = {
    "primary":   "#534AB7",
    "teal":      "#1D9E75",
    "coral":     "#D85A30",
    "amber":     "#BA7517",
    "gray":      "#888780",
    "bg":        "#F1EFE8",
    "border":    "#D3D1C7",
}

_BTN_STYLE = dict(button_color=COLORS["primary"], font_weight="bold")
_BTN_DANGER = dict(button_color=COLORS["coral"], font_weight="bold")
_BTN_OK = dict(button_color=COLORS["teal"], font_weight="bold")


# ---------------------------------------------------------------------------
# Titolo sezione
# ---------------------------------------------------------------------------

def section_title(text: str, color: str = "primary") -> w.HTML:
    c = COLORS.get(color, color)
    return w.HTML(
        f'<h3 style="margin:16px 0 8px;color:{c};'
        f'border-bottom:2px solid {c};padding-bottom:4px">{text}</h3>'
    )


def info_box(text: str, kind: str = "info") -> w.HTML:
    colors = {
        "info":    ("#E6F1FB", "#185FA5"),
        "success": ("#EAF3DE", "#3B6D11"),
        "warning": ("#FAEEDA", "#854F0B"),
        "error":   ("#FCEBEB", "#A32D2D"),
    }
    bg, fg = colors.get(kind, colors["info"])
    return w.HTML(
        f'<div style="background:{bg};color:{fg};padding:10px 14px;'
        f'border-radius:8px;font-size:13px;margin:6px 0">{text}</div>'
    )


# ---------------------------------------------------------------------------
# Output con log scrollabile
# ---------------------------------------------------------------------------

class LogOutput:
    """Box di output con log scrollabile e metodi append/clear."""

    def __init__(self, height: str = "180px", label: str = "Output"):
        self._lines: list[str] = []
        self._out = w.Output(
            layout=w.Layout(
                border=f"1px solid {COLORS['border']}",
                border_radius="8px",
                padding="8px",
                max_height=height,
                overflow_y="auto",
                background_color="#FAFAFA",
            )
        )
        self.widget = w.VBox([
            w.HTML(f'<span style="font-size:12px;color:{COLORS["gray"]}">'
                   f'{label}</span>'),
            self._out,
        ])

    def append(self, msg: str, kind: str = "info"):
        icons = {"info": "ℹ", "success": "✓", "warning": "⚠", "error": "✗"}
        fgs   = {"info": "#185FA5", "success": "#3B6D11",
                  "warning": "#854F0B", "error": "#A32D2D"}
        icon = icons.get(kind, "·")
        fg   = fgs.get(kind, "#333")
        self._lines.append(
            f'<div style="font-family:monospace;font-size:12px;color:{fg}'
            f';margin:1px 0">{icon} {msg}</div>'
        )
        with self._out:
            clear_output(wait=True)
            display(HTML("".join(self._lines)))

    def clear(self):
        self._lines = []
        with self._out:
            clear_output()


# ---------------------------------------------------------------------------
# Selettori progetto / testtype / run
# ---------------------------------------------------------------------------

def make_project_selector(db, label: str = "Progetto") -> w.Dropdown:
    projects = [p["name"] for p in db.list_projects()]
    return w.Dropdown(
        options=["— seleziona —"] + projects,
        description=label + ":",
        style={"description_width": "80px"},
        layout=w.Layout(width="320px"),
    )


def make_testtype_selector(db, project_name: str) -> w.Dropdown:
    if not project_name or project_name.startswith("—"):
        return w.Dropdown(options=[], description="TestType:",
                          style={"description_width": "80px"},
                          layout=w.Layout(width="280px"))
    tts = [t["name"] for t in db.list_testtypes(project_name)]
    return w.Dropdown(
        options=["— seleziona —"] + tts,
        description="TestType:",
        style={"description_width": "80px"},
        layout=w.Layout(width="280px"),
    )


def make_run_selector(db, project_name: str, testtype_name: str,
                      multi: bool = False) -> w.SelectMultiple | w.Dropdown:
    runs = []
    if project_name and not project_name.startswith("—") \
            and testtype_name and not testtype_name.startswith("—"):
        raw = db.list_runs(project_name, testtype_name)
        runs = [(f"{r['run_id']} — {r['condition']}  [{r['date'][:10]}]", r["id"])
                for r in raw]

    if multi:
        return w.SelectMultiple(
            options=runs,
            description="Run:",
            style={"description_width": "40px"},
            layout=w.Layout(width="420px", height="140px"),
        )
    return w.Dropdown(
        options=[("— seleziona —", None)] + runs,
        description="Run:",
        style={"description_width": "40px"},
        layout=w.Layout(width="420px"),
    )


# ---------------------------------------------------------------------------
# Form aggiunta progetto
# ---------------------------------------------------------------------------

def project_form(db, fm, log: LogOutput) -> w.VBox:
    name  = w.Text(description="Nome:", placeholder="es. motore_v2",
                   style={"description_width": "100px"},
                   layout=w.Layout(width="340px"))
    desc  = w.Text(description="Descrizione:", placeholder="breve descrizione",
                   style={"description_width": "100px"},
                   layout=w.Layout(width="420px"))
    dvc   = w.Text(description="DVC remote:", placeholder="myremote (opzionale)",
                   style={"description_width": "100px"},
                   layout=w.Layout(width="340px"))
    btn   = w.Button(description="Crea progetto", icon="plus",
                     style=_BTN_STYLE, layout=w.Layout(width="180px"))

    def on_create(_):
        n = name.value.strip()
        if not n:
            log.append("Inserisci un nome per il progetto.", "warning")
            return
        try:
            db.add_project(n, desc.value.strip(), dvc.value.strip())
            fm.write_project_config(
                __import__(
                    "testlab.core.interfaces", fromlist=["ProjectConfig"]
                ).ProjectConfig(
                    name=n, description=desc.value.strip(),
                    dvc_remote=dvc.value.strip(),
                )
            )
            log.append(f"Progetto '{n}' creato.", "success")
            name.value = desc.value = dvc.value = ""
        except Exception as e:
            log.append(f"Errore: {e}", "error")

    btn.on_click(on_create)
    return w.VBox([name, desc, dvc, btn])


# ---------------------------------------------------------------------------
# Form aggiunta testtype
# ---------------------------------------------------------------------------

def testtype_form(db, log: LogOutput) -> w.VBox:
    proj_dd = w.Dropdown(
        options=["— seleziona —"] + [p["name"] for p in db.list_projects()],
        description="Progetto:", style={"description_width": "100px"},
        layout=w.Layout(width="320px"),
    )
    tt_name = w.Text(description="TestType:", placeholder="es. rendimento",
                     style={"description_width": "100px"},
                     layout=w.Layout(width="280px"))
    scripts_dir = Path(__file__).parent.parent / "scripts"
    avail = [p.stem for p in scripts_dir.glob("*.py")
             if not p.name.startswith("_")]
    script_dd = w.Dropdown(
        options=avail,
        description="Script:", style={"description_width": "100px"},
        layout=w.Layout(width="300px"),
    )
    btn = w.Button(description="Aggiungi testtype", icon="plus",
                   style=_BTN_STYLE, layout=w.Layout(width="200px"))

    def on_add(_):
        proj = proj_dd.value
        tt   = tt_name.value.strip()
        sc   = script_dd.value
        if proj.startswith("—") or not tt:
            log.append("Seleziona progetto e inserisci nome testtype.", "warning")
            return
        try:
            db.add_testtype(proj, tt, sc)
            log.append(f"TestType '{tt}' → '{sc}' aggiunto a '{proj}'.", "success")
            tt_name.value = ""
        except Exception as e:
            log.append(f"Errore: {e}", "error")

    btn.on_click(on_add)
    return w.VBox([proj_dd, w.HBox([tt_name, script_dd]), btn])


# ---------------------------------------------------------------------------
# Form importazione run
# ---------------------------------------------------------------------------

def import_run_form(db, fm, log: LogOutput) -> w.VBox:
    proj_dd = w.Dropdown(
        options=["— seleziona —"] + [p["name"] for p in db.list_projects()],
        description="Progetto:", style={"description_width": "100px"},
        layout=w.Layout(width="320px"),
    )
    tt_dd = w.Dropdown(options=[], description="TestType:",
                       style={"description_width": "100px"},
                       layout=w.Layout(width="280px"))
    cond  = w.Text(description="Condizione:", placeholder="es. carico50",
                   style={"description_width": "100px"},
                   layout=w.Layout(width="280px"))
    fpath = w.Text(description="File path:", placeholder="/path/to/data.csv",
                   style={"description_width": "100px"},
                   layout=w.Layout(width="480px"))
    notes = w.Textarea(description="Note:", placeholder="note opzionali",
                       style={"description_width": "100px"},
                       layout=w.Layout(width="480px", height="64px"))
    tags  = w.Text(description="Tag:", placeholder="tag1, tag2",
                   style={"description_width": "100px"},
                   layout=w.Layout(width="360px"))
    dvc_chk = w.Checkbox(value=True, description="Traccia con DVC + git commit",
                          indent=False)
    btn = w.Button(description="Importa run", icon="upload",
                   style=_BTN_OK, layout=w.Layout(width="180px"))

    def on_proj_change(change):
        p = change["new"]
        if p.startswith("—"):
            tt_dd.options = []
            return
        tts = [t["name"] for t in db.list_testtypes(p)]
        tt_dd.options = ["— seleziona —"] + tts

    proj_dd.observe(on_proj_change, names="value")

    def on_import(_):
        proj = proj_dd.value
        tt   = tt_dd.value
        if proj.startswith("—") or (not tt or tt.startswith("—")):
            log.append("Seleziona progetto e testtype.", "warning")
            return
        fp = Path(fpath.value.strip())
        if not fp.exists():
            log.append(f"File non trovato: {fp}", "error")
            return
        tag_list = [t.strip() for t in tags.value.split(",") if t.strip()]
        try:
            if dvc_chk.value:
                res = fm.save_and_track(
                    fp, proj, tt, cond.value.strip(),
                    notes=notes.value.strip(), tags=tag_list,
                )
                log.append(
                    f"Run {res['run_db_id']} importato e tracciato con DVC.",
                    "success"
                )
                if not res["git_commit"]["ok"]:
                    log.append(
                        "Git commit: " + res["git_commit"]["error"], "warning"
                    )
            else:
                rid, dest = fm.save_run(
                    fp, proj, tt, cond.value.strip(),
                    notes=notes.value.strip(), tags=tag_list,
                )
                log.append(f"Run {rid} importato in {dest}.", "success")
            fpath.value = notes.value = tags.value = cond.value = ""
        except Exception as e:
            log.append(f"Errore: {e}", "error")

    btn.on_click(on_import)

    return w.VBox([
        w.HBox([proj_dd, tt_dd]),
        w.HBox([cond, fpath]),
        notes, tags, dvc_chk, btn,
    ])


# ---------------------------------------------------------------------------
# Pannello Git / DVC
# ---------------------------------------------------------------------------

def git_dvc_panel(fm, log: LogOutput) -> w.VBox:
    commit_msg = w.Text(
        description="Messaggio:", placeholder="feat: aggiungo run 003",
        style={"description_width": "100px"},
        layout=w.Layout(width="460px"),
    )

    def make_btn(label, icon, style=_BTN_STYLE):
        return w.Button(description=label, icon=icon, style=style,
                        layout=w.Layout(width="160px"))

    b_status  = make_btn("git status",  "info-circle")
    b_add     = make_btn("git add -A",  "plus")
    b_commit  = make_btn("git commit",  "check",   _BTN_OK)
    b_push    = make_btn("git push",    "upload",  _BTN_OK)
    b_pull    = make_btn("git pull",    "download")
    b_log     = make_btn("git log",     "list")
    b_dstatus = make_btn("dvc status",  "info-circle")
    b_dpush   = make_btn("dvc push",    "upload",  _BTN_OK)
    b_dpull   = make_btn("dvc pull",    "download")

    def run(fn, label):
        r = fn()
        kind = "success" if r["ok"] else "error"
        out  = r["output"] or r["error"] or "(nessun output)"
        log.append(f"[{label}] {out}", kind)

    b_status.on_click(lambda _: run(fm.git_status,  "git status"))
    b_add.on_click(   lambda _: run(fm.git_add_all, "git add"))
    b_log.on_click(   lambda _: run(fm.git_log,     "git log"))
    b_pull.on_click(  lambda _: run(fm.git_pull,    "git pull"))
    b_dstatus.on_click(lambda _: run(fm.dvc_status, "dvc status"))
    b_dpull.on_click(  lambda _: run(fm.dvc_pull,   "dvc pull"))

    def on_commit(_):
        msg = commit_msg.value.strip()
        if not msg:
            log.append("Inserisci un messaggio di commit.", "warning")
            return
        run(lambda: fm.git_commit(msg), "git commit")

    def on_push(_):
        run(fm.git_push, "git push")
        run(fm.dvc_push, "dvc push")

    b_commit.on_click(on_commit)
    b_push.on_click(on_push)
    b_dpush.on_click(lambda _: run(fm.dvc_push, "dvc push"))

    return w.VBox([
        w.HTML('<b style="font-size:13px">Git</b>'),
        w.HBox([b_status, b_add, b_log, b_pull]),
        w.HBox([commit_msg, b_commit, b_push]),
        w.HTML('<b style="font-size:13px;margin-top:8px">DVC</b>'),
        w.HBox([b_dstatus, b_dpull, b_dpush]),
    ])
