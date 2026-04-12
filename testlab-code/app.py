"""
TestLab — GUI standalone v2
Lancia con: python app.py   (dalla cartella testlab-code/)
"""
from __future__ import annotations
import json, os, subprocess, sys, threading, shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from datetime import datetime

# ── path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from testlab.core import TestLabDB, FileManager, PluginLoader, ProjectConfig

CODE_ROOT    = ROOT
DATA_ROOT    = ROOT.parent / "testlab-data"
DB_PATH      = ROOT / "db" / "testlab.sqlite"
SCRIPTS_DIR  = ROOT / "scripts"
SETTINGS_PATH = ROOT / "db" / "settings.json"
DATA_ROOT.mkdir(parents=True, exist_ok=True)

db     = TestLabDB(DB_PATH)
loader = PluginLoader(SCRIPTS_DIR)
fm     = FileManager(CODE_ROOT, DATA_ROOT, db)

# ── settings ──────────────────────────────────────────────────────────────────
_DEF = {"matlab_exe": "", "export_folder": str(CODE_ROOT/"exports"),
        "export_format": "PNG", "export_dpi": "150"}

def load_settings():
    if SETTINGS_PATH.exists():
        try: return {**_DEF, **json.loads(SETTINGS_PATH.read_text())}
        except Exception: pass
    return dict(_DEF)

def save_settings(s):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(s, indent=2))

SETTINGS = load_settings()

# ── constants ─────────────────────────────────────────────────────────────────
COND_FIELDS = [f"Cond {i}" for i in range(1, 11)]

C = dict(primary="#534AB7", teal="#1D9E75", coral="#D85A30", amber="#BA7517",
         gray="#888780", bg="#F7F6F2", bg2="#EEECEA", border="#D3D1C7",
         white="#FFFFFF", text="#1A1A18", muted="#6B6A65")

def _btn(parent, text, cmd, color=None, width=None):
    kw = dict(bg=color or C["primary"], fg="white", relief="flat",
              font=("Helvetica", 10, "bold"), padx=8, pady=4,
              cursor="hand2", activeforeground="white",
              activebackground=color or C["primary"])
    if width: kw["width"] = width
    return tk.Button(parent, text=text, command=cmd, **kw)


# ══════════════════════════════════════════════════════════════════════════════
# LogBox
# ══════════════════════════════════════════════════════════════════════════════
class LogBox:
    _TAGS = {"info": ("#185FA5","ℹ"), "success": ("#3B6D11","✓"),
             "warning": ("#854F0B","⚠"), "error": ("#A32D2D","✗")}

    def __init__(self, parent, height=6):
        self.frame = tk.Frame(parent, bg=C["bg"])
        self.txt = scrolledtext.ScrolledText(
            self.frame, height=height, state="disabled",
            bg="#FAFAF8", fg=C["text"], font=("Courier", 10),
            relief="flat", bd=1, wrap="word")
        self.txt.pack(fill="both", expand=True)
        for t, (fg, _) in self._TAGS.items():
            self.txt.tag_config(t, foreground=fg)

    def append(self, msg, kind="info"):
        _, icon = self._TAGS.get(kind, ("#333","·"))
        self.txt.config(state="normal")
        self.txt.insert("end", f"{icon} {msg}\n", kind)
        self.txt.see("end")
        self.txt.config(state="disabled")

    def clear(self):
        self.txt.config(state="normal")
        self.txt.delete("1.0","end")
        self.txt.config(state="disabled")


# ══════════════════════════════════════════════════════════════════════════════
# Dialogs
# ══════════════════════════════════════════════════════════════════════════════
class DlgNewProject(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Nuovo progetto"); self.resizable(False,False)
        self.configure(bg=C["bg"]); self.result = None
        f = tk.Frame(self, bg=C["bg"], padx=20, pady=16); f.pack()
        self.vn = tk.StringVar(); self.vd = tk.StringVar(); self.vr = tk.StringVar()
        for i,(lbl,var) in enumerate([("Nome:",self.vn),("Descrizione:",self.vd),("DVC remote:",self.vr)]):
            tk.Label(f,text=lbl,bg=C["bg"],font=("Helvetica",10)).grid(row=i,column=0,sticky="w",pady=3)
            ttk.Entry(f,textvariable=var,width=30).grid(row=i,column=1,pady=3,padx=(8,0))
        bf = tk.Frame(f,bg=C["bg"]); bf.grid(row=3,column=0,columnspan=2,pady=(10,0))
        _btn(bf,"Crea",self._ok,color=C["primary"]).pack(side="left",padx=(0,8))
        _btn(bf,"Annulla",self.destroy,color=C["gray"]).pack(side="left")
        self.grab_set(); self.wait_window()

    def _ok(self):
        n = self.vn.get().strip()
        if not n: messagebox.showwarning("TestLab","Inserisci un nome.",parent=self); return
        self.result = (n, self.vd.get().strip(), self.vr.get().strip()); self.destroy()


class DlgNewTesttype(tk.Toplevel):
    def __init__(self, parent, projects):
        super().__init__(parent)
        self.title("Nuovo testtype"); self.resizable(False,False)
        self.configure(bg=C["bg"]); self.result = None
        f = tk.Frame(self, bg=C["bg"], padx=20, pady=16); f.pack()
        f.columnconfigure(1,weight=1)
        self.vp = tk.StringVar(); self.vn = tk.StringVar()
        self.va = tk.StringVar(); self.vc = tk.StringVar()
        rows = [("Progetto:",self.vp,None),("Nome testtype:",self.vn,None),
                ("Script analisi:",self.va,"py"),("Script confronto:",self.vc,"py")]
        self._proj_cb = None
        for i,(lbl,var,kind) in enumerate(rows):
            tk.Label(f,text=lbl,bg=C["bg"],font=("Helvetica",10)).grid(row=i,column=0,sticky="w",pady=3)
            if kind is None and i == 0:
                cb = ttk.Combobox(f,textvariable=var,values=projects,state="readonly",width=26)
                cb.grid(row=i,column=1,pady=3,padx=(8,0),sticky="w")
                self._proj_cb = cb
            elif kind is None:
                ttk.Entry(f,textvariable=var,width=28).grid(row=i,column=1,pady=3,padx=(8,0),sticky="w")
            else:
                r = tk.Frame(f,bg=C["bg"]); r.grid(row=i,column=1,pady=3,padx=(8,0),sticky="w")
                ttk.Entry(r,textvariable=var,width=24).pack(side="left",padx=(0,4))
                _btn(r,"...",lambda v=var:self._browse(v),color=C["gray"],width=3).pack(side="left")
        bf = tk.Frame(f,bg=C["bg"]); bf.grid(row=len(rows),column=0,columnspan=2,pady=(10,0))
        _btn(bf,"Salva",self._ok,color=C["primary"]).pack(side="left",padx=(0,8))
        _btn(bf,"Annulla",self.destroy,color=C["gray"]).pack(side="left")
        self.grab_set(); self.wait_window()

    def _browse(self, var):
        p = filedialog.askopenfilename(filetypes=[("Script","*.py *.m"),("Tutti","*.*")])
        if p: var.set(p)

    def _ok(self):
        if not self.vp.get() or not self.vn.get().strip():
            messagebox.showwarning("TestLab","Seleziona progetto e inserisci nome.",parent=self); return
        self.result = (self.vp.get(), self.vn.get().strip(),
                       self.va.get().strip(), self.vc.get().strip()); self.destroy()


class DlgImportRun(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Importa run"); self.resizable(False,False)
        self.configure(bg=C["bg"])
        f = tk.Frame(self,bg=C["bg"],padx=20,pady=16); f.pack()
        f.columnconfigure(1,weight=1)
        self.vp=tk.StringVar(); self.vt=tk.StringVar()
        self.vc=tk.StringVar(); self.vf=tk.StringVar()
        self.vdvc=tk.BooleanVar(value=False)
        tk.Label(f,text="Progetto:",bg=C["bg"],font=("Helvetica",10)).grid(row=0,column=0,sticky="w",pady=3)
        pcb=ttk.Combobox(f,textvariable=self.vp,values=[p["name"] for p in db.list_projects()],state="readonly",width=26)
        pcb.grid(row=0,column=1,pady=3,padx=(8,0),sticky="w"); pcb.bind("<<ComboboxSelected>>",self._on_proj)
        tk.Label(f,text="TestType:",bg=C["bg"],font=("Helvetica",10)).grid(row=1,column=0,sticky="w",pady=3)
        self.tt_cb=ttk.Combobox(f,textvariable=self.vt,state="readonly",width=26)
        self.tt_cb.grid(row=1,column=1,pady=3,padx=(8,0),sticky="w")
        tk.Label(f,text="Condizione:",bg=C["bg"],font=("Helvetica",10)).grid(row=2,column=0,sticky="w",pady=3)
        ttk.Entry(f,textvariable=self.vc,width=28).grid(row=2,column=1,pady=3,padx=(8,0),sticky="w")
        tk.Label(f,text="File dati:",bg=C["bg"],font=("Helvetica",10)).grid(row=3,column=0,sticky="w",pady=3)
        fr=tk.Frame(f,bg=C["bg"]); fr.grid(row=3,column=1,pady=3,padx=(8,0),sticky="w")
        ttk.Entry(fr,textvariable=self.vf,width=24).pack(side="left",padx=(0,4))
        _btn(fr,"...",self._browse,color=C["gray"],width=3).pack(side="left")
        tk.Label(f,text="Note:",bg=C["bg"],font=("Helvetica",10)).grid(row=4,column=0,sticky="nw",pady=3)
        self.txtn=tk.Text(f,height=3,width=28,font=("Helvetica",10),relief="flat",bd=1)
        self.txtn.grid(row=4,column=1,pady=3,padx=(8,0),sticky="ew")
        tk.Checkbutton(f,text="Traccia con DVC + git commit",variable=self.vdvc,
                       bg=C["bg"],font=("Helvetica",10)).grid(row=5,column=1,sticky="w",pady=4)
        bf=tk.Frame(f,bg=C["bg"]); bf.grid(row=6,column=0,columnspan=2,pady=(8,0))
        _btn(bf,"Importa",self._ok,color=C["teal"]).pack(side="left",padx=(0,8))
        _btn(bf,"Chiudi",self.destroy,color=C["gray"]).pack(side="left")
        self.log=LogBox(f,height=4); self.log.frame.grid(row=7,column=0,columnspan=2,sticky="ew",pady=(8,0))

    def _on_proj(self,_=None):
        self.tt_cb["values"]=[t["name"] for t in db.list_testtypes(self.vp.get())]
        self.vt.set("")

    def _browse(self):
        p=filedialog.askopenfilename(filetypes=[("CSV/TXT","*.csv *.txt"),("Tutti","*.*")])
        if p: self.vf.set(p)

    def _ok(self):
        proj=self.vp.get(); tt=self.vt.get(); fp=Path(self.vf.get().strip())
        if not proj or not tt: self.log.append("Seleziona progetto e testtype.","warning"); return
        if not fp.exists(): self.log.append(f"File non trovato: {fp}","error"); return
        notes=self.txtn.get("1.0","end").strip()
        def task():
            try:
                if self.vdvc.get():
                    res=fm.save_and_track(fp,proj,tt,self.vc.get().strip(),notes=notes)
                    self.log.append(f"Run {res['run_db_id']} importato e tracciato.","success")
                else:
                    rid,_=fm.save_run(fp,proj,tt,self.vc.get().strip(),notes=notes)
                    self.log.append(f"Run {rid} importato.","success")
            except Exception as e: self.log.append(str(e),"error")
        threading.Thread(target=task,daemon=True).start()


class DlgSettings(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Impostazioni"); self.resizable(False,False)
        self.configure(bg=C["bg"])
        f=tk.Frame(self,bg=C["bg"],padx=20,pady=16); f.pack(); f.columnconfigure(1,weight=1)
        self.vars={}
        fields=[("matlab.exe:","matlab_exe","file"),("Cartella export:","export_folder","dir"),
                ("Formato default:","export_format","combo"),("DPI default:","export_dpi","entry")]
        for i,(lbl,key,kind) in enumerate(fields):
            tk.Label(f,text=lbl,bg=C["bg"],font=("Helvetica",10)).grid(row=i,column=0,sticky="w",pady=4)
            v=tk.StringVar(value=SETTINGS.get(key,""))
            self.vars[key]=v
            if kind=="combo":
                ttk.Combobox(f,textvariable=v,values=["PNG","PDF","SVG"],state="readonly",width=10).grid(
                    row=i,column=1,pady=4,padx=(8,0),sticky="w")
            elif kind=="entry":
                ttk.Entry(f,textvariable=v,width=10).grid(row=i,column=1,pady=4,padx=(8,0),sticky="w")
            else:
                r=tk.Frame(f,bg=C["bg"]); r.grid(row=i,column=1,pady=4,padx=(8,0),sticky="w")
                ttk.Entry(r,textvariable=v,width=32).pack(side="left",padx=(0,4))
                _btn(r,"...",lambda k=key:self._browse(k),color=C["gray"],width=3).pack(side="left")
        bf=tk.Frame(f,bg=C["bg"]); bf.grid(row=len(fields),column=0,columnspan=2,pady=(12,0))
        _btn(bf,"Salva",self._save,color=C["primary"]).pack(side="left",padx=(0,8))
        _btn(bf,"Annulla",self.destroy,color=C["gray"]).pack(side="left")
        self.grab_set(); self.wait_window()

    def _browse(self,key):
        p=(filedialog.askopenfilename(filetypes=[("Eseguibile","*.exe"),("Tutti","*.*")])
           if key=="matlab_exe" else filedialog.askdirectory())
        if p: self.vars[key].set(p)

    def _save(self):
        for k,v in self.vars.items(): SETTINGS[k]=v.get().strip()
        save_settings(SETTINGS)
        messagebox.showinfo("TestLab","Impostazioni salvate.",parent=self)
        self.destroy()


class DlgGitDVC(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Git / DVC"); self.geometry("640x500"); self.configure(bg=C["bg"])
        f=tk.Frame(self,bg=C["bg"],padx=16,pady=12); f.pack(fill="both",expand=True)
        tk.Label(f,text="Git",bg=C["bg"],font=("Helvetica",11,"bold"),fg=C["primary"]).pack(anchor="w")
        r1=tk.Frame(f,bg=C["bg"]); r1.pack(anchor="w",pady=(4,0))
        for lbl,fn in [("status",lambda:self._run(fm.git_status,"git status")),
                       ("add -A",lambda:self._run(fm.git_add_all,"git add")),
                       ("log",lambda:self._run(fm.git_log,"git log")),
                       ("pull",lambda:self._run(fm.git_pull,"git pull"))]:
            _btn(r1,f"git {lbl}",fn,color=C["primary"],width=12).pack(side="left",padx=(0,6))
        r2=tk.Frame(f,bg=C["bg"]); r2.pack(anchor="w",pady=6)
        tk.Label(r2,text="Msg:",bg=C["bg"],font=("Helvetica",10)).pack(side="left",padx=(0,4))
        self.vm=tk.StringVar()
        ttk.Entry(r2,textvariable=self.vm,width=30).pack(side="left",padx=(0,6))
        _btn(r2,"commit",self._commit,color=C["teal"],width=10).pack(side="left",padx=(0,6))
        _btn(r2,"git+dvc push",self._push,color=C["teal"],width=14).pack(side="left")
        ttk.Separator(f,orient="horizontal").pack(fill="x",pady=8)
        tk.Label(f,text="DVC",bg=C["bg"],font=("Helvetica",11,"bold"),fg=C["amber"]).pack(anchor="w")
        r3=tk.Frame(f,bg=C["bg"]); r3.pack(anchor="w",pady=(4,0))
        for lbl,fn in [("status",lambda:self._run(fm.dvc_status,"dvc status")),
                       ("pull",lambda:self._run(fm.dvc_pull,"dvc pull")),
                       ("push",lambda:self._run(fm.dvc_push,"dvc push"))]:
            _btn(r3,f"dvc {lbl}",fn,color=C["amber"],width=12).pack(side="left",padx=(0,6))
        ttk.Separator(f,orient="horizontal").pack(fill="x",pady=8)
        self.log=LogBox(f,height=12); self.log.frame.pack(fill="both",expand=True)

    def _run(self,fn,label):
        def t():
            r=fn(); k="success" if r["ok"] else "error"
            self.log.append(f"[{label}] {r['output'] or r['error']}",k)
        threading.Thread(target=t,daemon=True).start()

    def _commit(self):
        msg=self.vm.get().strip()
        if not msg: self.log.append("Inserisci un messaggio.","warning"); return
        self._run(lambda:fm.git_commit(msg),"git commit")

    def _push(self):
        self._run(fm.git_push,"git push"); self._run(fm.dvc_push,"dvc push")


class DlgExploreRuns(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Esplora run"); self.geometry("900x520"); self.configure(bg=C["bg"])
        f=tk.Frame(self,bg=C["bg"],padx=12,pady=10); f.pack(fill="both",expand=True)
        # filtri
        ff=tk.Frame(f,bg=C["bg"]); ff.pack(fill="x",pady=(0,6))
        tk.Label(ff,text="Progetto:",bg=C["bg"],font=("Helvetica",10)).pack(side="left",padx=(0,4))
        self.vp=tk.StringVar()
        ttk.Combobox(ff,textvariable=self.vp,values=[p["name"] for p in db.list_projects()],
                     state="readonly",width=18).pack(side="left",padx=(0,12))
        tk.Label(ff,text="Condizione:",bg=C["bg"],font=("Helvetica",10)).pack(side="left",padx=(0,4))
        self.vc=tk.StringVar()
        ttk.Entry(ff,textvariable=self.vc,width=14).pack(side="left",padx=(0,12))
        tk.Label(ff,text="Campo:",bg=C["bg"],font=("Helvetica",10)).pack(side="left",padx=(0,4))
        self.vf=tk.StringVar()
        ttk.Combobox(ff,textvariable=self.vf,values=COND_FIELDS,width=10).pack(side="left",padx=(0,4))
        tk.Label(ff,text="=",bg=C["bg"],font=("Helvetica",10)).pack(side="left")
        self.vfv=tk.StringVar()
        ttk.Entry(ff,textvariable=self.vfv,width=10).pack(side="left",padx=(0,10))
        _btn(ff,"Cerca",self._search,color=C["primary"],width=8).pack(side="left")
        # treeview
        cols=("id","progetto","testtype","run_id","condizione","data","note")
        self.tree=ttk.Treeview(f,columns=cols,show="headings",height=18)
        ws={"id":35,"progetto":100,"testtype":100,"run_id":55,"condizione":120,"data":85,"note":280}
        for c in cols:
            self.tree.heading(c,text=c.capitalize()); self.tree.column(c,width=ws.get(c,90))
        self.tree.pack(side="left",fill="both",expand=True)
        ttk.Scrollbar(f,orient="vertical",command=self.tree.yview).pack(side="left",fill="y")
        self.lbl=tk.Label(f,text="",bg=C["bg"],fg=C["muted"],font=("Helvetica",10))
        self.lbl.pack(anchor="w")

    def _search(self):
        proj=self.vp.get()
        if not proj: messagebox.showwarning("TestLab","Seleziona un progetto.",parent=self); return
        runs=db.list_runs(proj,condition=self.vc.get().strip() or None)
        field=self.vf.get().strip(); fval=self.vfv.get().strip()
        if field and fval:
            runs=[r for r in runs if r.get("extra",{}).get(field,"").lower()==fval.lower()]
        self.tree.delete(*self.tree.get_children())
        for r in runs:
            note=r["notes"][:55]+"…" if len(r["notes"])>55 else r["notes"]
            self.tree.insert("","end",values=(r["id"],r["project"],r["testtype"],
                                              r["run_id"],r["condition"],r["date"][:10],note))
        self.lbl.config(text=f"{len(runs)} run trovati")


# ══════════════════════════════════════════════════════════════════════════════
# NavPanel — pannello sinistro
# ══════════════════════════════════════════════════════════════════════════════
class NavPanel(tk.Frame):
    def __init__(self, parent, on_change):
        super().__init__(parent, bg=C["bg2"], width=290)
        self.pack_propagate(False)
        self.on_change = on_change
        self._run_map = {}
        self._cur_id  = None
        self._build()

    def _build(self):
        tk.Label(self,text="Navigazione",bg=C["bg2"],fg=C["primary"],
                 font=("Helvetica",11,"bold")).pack(anchor="w",padx=10,pady=(10,4))

        # progetto
        pf=tk.Frame(self,bg=C["bg2"]); pf.pack(fill="x",padx=10,pady=2)
        tk.Label(pf,text="Progetto:",bg=C["bg2"],font=("Helvetica",10)).pack(side="left")
        self.vp=tk.StringVar()
        self.pcb=ttk.Combobox(pf,textvariable=self.vp,state="readonly",width=17)
        self.pcb.pack(side="left",padx=(6,0))
        self.pcb.bind("<<ComboboxSelected>>",self._on_proj)

        # testtype
        tf=tk.Frame(self,bg=C["bg2"]); tf.pack(fill="x",padx=10,pady=2)
        tk.Label(tf,text="TestType:",bg=C["bg2"],font=("Helvetica",10)).pack(side="left")
        self.vt=tk.StringVar()
        self.tcb=ttk.Combobox(tf,textvariable=self.vt,state="readonly",width=17)
        self.tcb.pack(side="left",padx=(6,0))
        self.tcb.bind("<<ComboboxSelected>>",self._on_tt)

        ttk.Separator(self,orient="horizontal").pack(fill="x",padx=10,pady=6)

        # run list
        tk.Label(self,text="Run  (Ctrl+click per multipli)",bg=C["bg2"],
                 fg=C["muted"],font=("Helvetica",9)).pack(anchor="w",padx=10)
        lbf=tk.Frame(self,bg=C["bg2"]); lbf.pack(fill="x",padx=10,pady=4)
        self.lb=tk.Listbox(lbf,selectmode="multiple",height=8,font=("Courier",9),
                            bg=C["white"],relief="flat",bd=1,exportselection=False)
        self.lb.pack(side="left",fill="both",expand=True)
        sb=ttk.Scrollbar(lbf,orient="vertical",command=self.lb.yview)
        sb.pack(side="right",fill="y"); self.lb.config(yscrollcommand=sb.set)
        self.lb.bind("<<ListboxSelect>>",self._on_sel)

        ttk.Separator(self,orient="horizontal").pack(fill="x",padx=10,pady=6)

        # campi condizione
        tk.Label(self,text="Campi condizione run",bg=C["bg2"],fg=C["primary"],
                 font=("Helvetica",10,"bold")).pack(anchor="w",padx=10)
        cf=tk.Frame(self,bg=C["bg2"]); cf.pack(fill="x",padx=10,pady=4)
        cf.columnconfigure(1,weight=1)
        self.cvars={}
        for i,field in enumerate(COND_FIELDS):
            tk.Label(cf,text=f"{field}:",bg=C["bg2"],font=("Helvetica",9),
                     width=8,anchor="w").grid(row=i,column=0,sticky="w",pady=1)
            v=tk.StringVar(); self.cvars[field]=v
            ttk.Entry(cf,textvariable=v,width=16,font=("Helvetica",9)).grid(
                row=i,column=1,sticky="ew",pady=1,padx=(4,0))

        # nota
        tk.Label(self,text="Nota:",bg=C["bg2"],font=("Helvetica",9,"bold")).pack(
            anchor="w",padx=10,pady=(6,0))
        self.txtn=tk.Text(self,height=3,font=("Helvetica",9),
                           relief="flat",bd=1,bg=C["white"])
        self.txtn.pack(fill="x",padx=10,pady=(2,4))

        _btn(self,"Salva campi run",self._save,color=C["teal"],width=18).pack(
            padx=10,pady=(0,10))

        self.refresh()

    def refresh(self):
        names=[p["name"] for p in db.list_projects()]
        self.pcb["values"]=names
        if names and not self.vp.get():
            self.vp.set(names[0]); self._on_proj()

    def _on_proj(self,_=None):
        tts=[t["name"] for t in db.list_testtypes(self.vp.get())]
        self.tcb["values"]=tts; self.vt.set(tts[0] if tts else ""); self._on_tt()

    def _on_tt(self,_=None):
        runs=db.list_runs(self.vp.get(),self.vt.get()) if self.vp.get() and self.vt.get() else []
        self._run_map={}; self.lb.delete(0,"end")
        for r in runs:
            lbl=f"{r['run_id']}  {r['condition']}"; self._run_map[lbl]=r["id"]
            self.lb.insert("end",lbl)
        self._clear_fields(); self.on_change([],self.vp.get(),self.vt.get())

    def _on_sel(self,_=None):
        ids=[self._run_map[self.lb.get(i)] for i in self.lb.curselection()]
        if len(ids)==1: self._load_fields(ids[0])
        else: self._clear_fields()
        self.on_change(ids,self.vp.get(),self.vt.get())

    def _load_fields(self,rid):
        run=db.get_run(rid)
        if not run: return
        self._cur_id=rid; extra=run.get("extra",{})
        for f,v in self.cvars.items(): v.set(extra.get(f,""))
        self.txtn.delete("1.0","end"); self.txtn.insert("1.0",run.get("notes",""))

    def _clear_fields(self):
        self._cur_id=None
        for v in self.cvars.values(): v.set("")
        self.txtn.delete("1.0","end")

    def _save(self):
        if self._cur_id is None:
            messagebox.showwarning("TestLab","Seleziona un singolo run."); return
        extra={f:v.get().strip() for f,v in self.cvars.items() if v.get().strip()}
        notes=self.txtn.get("1.0","end").strip()
        try:
            with db._conn() as con:
                con.execute("UPDATE runs SET notes=? WHERE id=?",(notes,self._cur_id))
                con.execute("DELETE FROM run_extra WHERE run_id=?",(self._cur_id,))
                for k,v in extra.items():
                    con.execute("INSERT INTO run_extra (run_id,key,value) VALUES (?,?,?)",
                                (self._cur_id,k,v))
            messagebox.showinfo("TestLab","Campi salvati.")
        except Exception as e: messagebox.showerror("TestLab",str(e))

    def selected_ids(self):
        return [self._run_map[self.lb.get(i)] for i in self.lb.curselection()]

    def selected_files(self):
        files=[]
        for rid in self.selected_ids():
            r=db.get_run(rid)
            if r: files.append(DATA_ROOT/r["data_path"])
        return files

    def cur_project(self): return self.vp.get()
    def cur_testtype(self): return self.vt.get()


# ══════════════════════════════════════════════════════════════════════════════
# LauncherPanel — pannello destro
# ══════════════════════════════════════════════════════════════════════════════
class LauncherPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=C["bg"])
        self.nav = None
        self._last_fig: Path|None = None
        self._build()

    def _build(self):
        self.columnconfigure(0,weight=1); self.columnconfigure(1,weight=1)

        # ── Analisi ───────────────────────────────────────────────────────────
        af=tk.LabelFrame(self,text="  Analisi  ",bg=C["bg"],fg=C["teal"],
                          font=("Helvetica",10,"bold"),relief="groove",bd=1)
        af.grid(row=0,column=0,sticky="nsew",padx=(0,6),pady=(0,8))
        af.columnconfigure(0,weight=1)

        tk.Label(af,text="Script (.py / .m):",bg=C["bg"],
                 font=("Helvetica",10)).grid(row=0,column=0,sticky="w",padx=8,pady=(8,2))
        sf=tk.Frame(af,bg=C["bg"]); sf.grid(row=1,column=0,sticky="ew",padx=8,pady=2)
        sf.columnconfigure(0,weight=1)
        self.va=tk.StringVar()
        ttk.Entry(sf,textvariable=self.va).grid(row=0,column=0,sticky="ew",padx=(0,4))
        _btn(sf,"...",lambda:self._browse(self.va),color=C["gray"],width=3).grid(row=0,column=1)
        self.la_type=tk.Label(af,text="",bg=C["bg"],font=("Helvetica",9,"italic"),fg=C["muted"])
        self.la_type.grid(row=2,column=0,sticky="w",padx=8)
        self.va.trace_add("write",lambda *_:self._update_type(self.va,self.la_type))

        tk.Label(af,text="Usa run selezionati dal pannello sinistro",
                 bg=C["bg"],fg=C["muted"],font=("Helvetica",9)).grid(
            row=3,column=0,sticky="w",padx=8,pady=(6,2))
        _btn(af,"▶  Lancia analisi",self._launch_analysis,
             color=C["teal"],width=20).grid(row=4,column=0,sticky="w",padx=8,pady=8)

        # ── Confronto ─────────────────────────────────────────────────────────
        cf=tk.LabelFrame(self,text="  Confronto  ",bg=C["bg"],fg=C["primary"],
                          font=("Helvetica",10,"bold"),relief="groove",bd=1)
        cf.grid(row=0,column=1,sticky="nsew",padx=(6,0),pady=(0,8))
        cf.columnconfigure(0,weight=1)

        tk.Label(cf,text="Script (.py / .m):",bg=C["bg"],
                 font=("Helvetica",10)).grid(row=0,column=0,sticky="w",padx=8,pady=(8,2))
        sf2=tk.Frame(cf,bg=C["bg"]); sf2.grid(row=1,column=0,sticky="ew",padx=8,pady=2)
        sf2.columnconfigure(0,weight=1)
        self.vc=tk.StringVar()
        ttk.Entry(sf2,textvariable=self.vc).grid(row=0,column=0,sticky="ew",padx=(0,4))
        _btn(sf2,"...",lambda:self._browse(self.vc),color=C["gray"],width=3).grid(row=0,column=1)
        self.lc_type=tk.Label(cf,text="",bg=C["bg"],font=("Helvetica",9,"italic"),fg=C["muted"])
        self.lc_type.grid(row=2,column=0,sticky="w",padx=8)
        self.vc.trace_add("write",lambda *_:self._update_type(self.vc,self.lc_type))

        tk.Label(cf,text="Seleziona ≥2 run con Ctrl+click",
                 bg=C["bg"],fg=C["muted"],font=("Helvetica",9)).grid(
            row=3,column=0,sticky="w",padx=8,pady=(6,2))
        _btn(cf,"▶  Lancia confronto",self._launch_compare,
             color=C["primary"],width=20).grid(row=4,column=0,sticky="w",padx=8,pady=(8,4))

        # export figura
        ef=tk.Frame(cf,bg=C["bg2"]); ef.grid(row=5,column=0,sticky="ew",padx=8,pady=(0,8))
        ef.columnconfigure(3,weight=1)
        tk.Label(ef,text="Export figura:",bg=C["bg2"],
                 font=("Helvetica",9,"bold")).grid(row=0,column=0,columnspan=4,sticky="w",pady=(4,2))
        tk.Label(ef,text="Fmt:",bg=C["bg2"],font=("Helvetica",9)).grid(row=1,column=0,sticky="w")
        self.vfmt=tk.StringVar(value=SETTINGS.get("export_format","PNG"))
        ttk.Combobox(ef,textvariable=self.vfmt,values=["PNG","PDF","SVG"],
                     state="readonly",width=6).grid(row=1,column=1,sticky="w",padx=4)
        tk.Label(ef,text="DPI:",bg=C["bg2"],font=("Helvetica",9)).grid(row=1,column=2,sticky="w",padx=(8,0))
        self.vdpi=tk.StringVar(value=SETTINGS.get("export_dpi","150"))
        ttk.Entry(ef,textvariable=self.vdpi,width=5).grid(row=1,column=3,sticky="w",padx=4)
        self.btn_save=_btn(ef,"Salva figura",self._save_fig,color=C["coral"],width=14)
        self.btn_save.grid(row=2,column=0,columnspan=4,sticky="w",pady=(6,0))
        self.btn_save.config(state="disabled")
        self.lbl_exp=tk.Label(ef,text="",bg=C["bg2"],fg=C["muted"],font=("Helvetica",9))
        self.lbl_exp.grid(row=3,column=0,columnspan=4,sticky="w",pady=(2,0))

        # ── Log ───────────────────────────────────────────────────────────────
        tk.Label(self,text="Output processo",bg=C["bg"],fg=C["muted"],
                 font=("Helvetica",9,"bold")).grid(row=1,column=0,columnspan=2,sticky="w",pady=(0,2))
        self.log=LogBox(self,height=12)
        self.log.frame.grid(row=2,column=0,columnspan=2,sticky="nsew")
        self.rowconfigure(2,weight=1)

    # helpers
    def _browse(self, var):
        p=filedialog.askopenfilename(filetypes=[("Script","*.py *.m"),("Tutti","*.*")])
        if p: var.set(p)

    def _update_type(self, var, lbl):
        ext=Path(var.get()).suffix.lower()
        lbl.config(**{".py":dict(text="Python",fg=C["teal"]),
                      ".m": dict(text="MATLAB",fg=C["amber"])}.get(ext,dict(text="",fg=C["muted"])))

    def _files(self):
        if not self.nav: return None
        fs=self.nav.selected_files()
        miss=[f for f in fs if not f.exists()]
        for m in miss: self.log.append(f"File non trovato (dvc pull?): {m}","error")
        return None if miss else fs

    def _build_cmd(self, script, files):
        ext=Path(script).suffix.lower()
        if ext==".py":
            return [sys.executable,script]+[str(f) for f in files]
        if ext==".m":
            matlab=SETTINGS.get("matlab_exe","").strip()
            if not matlab:
                self.log.append("Path matlab.exe non impostato (Impostazioni).","error"); return None
            sd=str(Path(script).parent).replace("\\","/")
            sp=str(Path(script)).replace("\\","/")
            fc="{"+"".join(f"'{str(f).replace(chr(92),'/')}'" for f in files)+"}"
            return [matlab,"-batch",
                    f"addpath('{sd}'); assignin('base','data_files',{fc}); run('{sp}');"]
        self.log.append(f"Estensione non supportata: {ext}","error"); return None

    def _exec(self, script, files, export_path=""):
        cmd=self._build_cmd(script,files)
        if not cmd: return
        env=os.environ.copy()
        if export_path: env["TESTLAB_EXPORT_PATH"]=export_path
        self.log.append("Lancio: "+" ".join(str(c) for c in cmd),"info")
        def task():
            try:
                proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                      text=True,cwd=str(Path(script).parent),env=env)
                for line in proc.stdout:
                    line=line.rstrip()
                    if line: self.log.append(line,"info")
                proc.wait()
                if proc.returncode==0:
                    self.log.append("Script terminato correttamente.","success")
                    if export_path and Path(export_path).exists():
                        self._last_fig=Path(export_path)
                        self.btn_save.config(state="normal")
                        self.lbl_exp.config(text=f"Pronta: {Path(export_path).name}",fg=C["teal"])
                else:
                    self.log.append(f"Exit {proc.returncode}.","error")
            except Exception as e: self.log.append(str(e),"error")
        threading.Thread(target=task,daemon=True).start()

    def _launch_analysis(self):
        sc=self.va.get().strip()
        if not sc: self.log.append("Seleziona uno script di analisi.","warning"); return
        fs=self._files()
        if fs is None: return
        if not fs: self.log.append("Seleziona almeno un run.","warning"); return
        self._exec(sc,fs)

    def _launch_compare(self):
        sc=self.vc.get().strip()
        if not sc: self.log.append("Seleziona uno script di confronto.","warning"); return
        fs=self._files()
        if fs is None: return
        if len(fs)<2: self.log.append("Seleziona almeno 2 run per il confronto.","warning"); return
        proj=self.nav.cur_project() if self.nav else "unknown"
        ts=datetime.now().strftime("%Y%m%d_%H%M%S")
        fmt=self.vfmt.get().lower()
        ed=CODE_ROOT/"projects"/proj/"exports"; ed.mkdir(parents=True,exist_ok=True)
        ep=str(ed/f"confronto_{ts}.{fmt}")
        self.btn_save.config(state="disabled")
        self.lbl_exp.config(text="In attesa...",fg=C["muted"])
        self._exec(sc,fs,export_path=ep)

    def _save_fig(self):
        if not self._last_fig or not self._last_fig.exists():
            messagebox.showwarning("TestLab","Nessuna figura disponibile."); return
        fmt=self.vfmt.get().lower(); dpi=self.vdpi.get().strip() or "150"
        proj=self.nav.cur_project() if self.nav else ""
        init=str(CODE_ROOT/"projects"/proj/"exports") if proj else str(CODE_ROOT/"exports")
        dest_dir=filedialog.askdirectory(title="Cartella di destinazione",initialdir=init)
        if not dest_dir: return
        ts=datetime.now().strftime("%Y%m%d_%H%M%S")
        dest=Path(dest_dir)/f"confronto_{ts}.{fmt}"
        dest.parent.mkdir(parents=True,exist_ok=True)
        try:
            if self._last_fig.suffix.lower()==f".{fmt}":
                shutil.copy2(self._last_fig,dest)
            else:
                try:
                    from PIL import Image
                    Image.open(self._last_fig).save(str(dest),dpi=(int(dpi),int(dpi)))
                except ImportError:
                    shutil.copy2(self._last_fig,dest)
            self.lbl_exp.config(text=f"Salvata: {dest.name}",fg=C["teal"])
            messagebox.showinfo("TestLab",f"Figura salvata in:\n{dest}")
        except Exception as e: messagebox.showerror("TestLab",str(e))


# ══════════════════════════════════════════════════════════════════════════════
# MainWindow
# ══════════════════════════════════════════════════════════════════════════════
class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TestLab"); self.geometry("1120x740"); self.minsize(900,600)
        self.configure(bg=C["bg"])
        self._style(); self._menu(); self._body()

    def _style(self):
        s=ttk.Style(self); s.theme_use("clam")
        s.configure("TFrame",background=C["bg"])
        s.configure("TEntry",fieldbackground=C["white"])
        s.configure("TCombobox",fieldbackground=C["white"])
        s.configure("TSeparator",background=C["border"])
        s.configure("Treeview",background=C["white"],fieldbackground=C["white"],
                    rowheight=24,font=("Helvetica",10))
        s.configure("Treeview.Heading",background=C["bg2"],foreground=C["text"],
                    font=("Helvetica",10,"bold"))

    def _menu(self):
        mb=tk.Menu(self,bg=C["bg2"],fg=C["text"],relief="flat",font=("Helvetica",10))
        # File
        mf=tk.Menu(mb,tearoff=0,bg=C["white"],fg=C["text"],font=("Helvetica",10))
        mf.add_command(label="Nuovo progetto…",command=self._new_proj)
        mf.add_command(label="Nuovo testtype…",command=self._new_tt)
        mf.add_separator()
        mf.add_command(label="Impostazioni…",command=lambda:DlgSettings(self))
        mf.add_separator()
        mf.add_command(label="Esci",command=self.quit)
        mb.add_cascade(label="File",menu=mf)
        # Dati
        md=tk.Menu(mb,tearoff=0,bg=C["white"],fg=C["text"],font=("Helvetica",10))
        md.add_command(label="Importa run…",command=lambda:DlgImportRun(self))
        md.add_command(label="Esplora run…",command=lambda:DlgExploreRuns(self))
        mb.add_cascade(label="Dati",menu=md)
        # Git/DVC
        mg=tk.Menu(mb,tearoff=0,bg=C["white"],fg=C["text"],font=("Helvetica",10))
        mg.add_command(label="Apri pannello Git / DVC…",command=lambda:DlgGitDVC(self))
        mb.add_cascade(label="Git / DVC",menu=mg)
        self.config(menu=mb)

    def _body(self):
        # header
        hdr=tk.Frame(self,bg=C["primary"],height=44)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        tk.Label(hdr,text="  TestLab",bg=C["primary"],fg="white",
                 font=("Helvetica",15,"bold")).pack(side="left",padx=12)
        tk.Label(hdr,text=str(CODE_ROOT),bg=C["primary"],fg="#C4C0F0",
                 font=("Helvetica",9)).pack(side="left")
        # body
        body=tk.Frame(self,bg=C["bg"]); body.pack(fill="both",expand=True,padx=10,pady=10)
        body.rowconfigure(0,weight=1); body.columnconfigure(2,weight=1)

        self.nav=NavPanel(body,on_change=self._on_sel)
        self.nav.grid(row=0,column=0,sticky="ns",padx=(0,0))

        tk.Frame(body,bg=C["border"],width=1).grid(row=0,column=1,sticky="ns",padx=8)

        self.launcher=LauncherPanel(body)
        self.launcher.nav=self.nav
        self.launcher.grid(row=0,column=2,sticky="nsew")

    def _on_sel(self, ids, proj, tt):
        pass   # placeholder — si può usare per aggiornare una status bar

    def _new_proj(self):
        dlg=DlgNewProject(self)
        if not dlg.result: return
        name,desc,dvc=dlg.result
        try:
            db.add_project(name,desc,dvc)
            fm.write_project_config(ProjectConfig(name=name,description=desc,dvc_remote=dvc))
            self.nav.refresh()
            messagebox.showinfo("TestLab",f"Progetto '{name}' creato.")
        except Exception as e: messagebox.showerror("TestLab",str(e))

    def _new_tt(self):
        projs=[p["name"] for p in db.list_projects()]
        dlg=DlgNewTesttype(self,projs)
        if not dlg.result: return
        proj,name,analysis,compare=dlg.result
        try:
            db.add_testtype(proj,name,analysis or name)
            cfg=fm.read_project_config(proj)
            cfg.testtypes[name]=analysis or name
            d=cfg.to_dict(); d.setdefault("compare_scripts",{})[name]=compare
            (CODE_ROOT/"projects"/proj/"project.json").write_text(
                json.dumps(d,indent=2,ensure_ascii=False))
            self.nav._on_proj()
            messagebox.showinfo("TestLab",f"TestType '{name}' aggiunto.")
        except Exception as e: messagebox.showerror("TestLab",str(e))


if __name__ == "__main__":
    MainWindow().mainloop()
