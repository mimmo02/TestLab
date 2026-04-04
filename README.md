# TestLab Project

Benvenuto in **TestLab**, una piattaforma modulare per la gestione di test e analisi dati.

## 📂 Struttura della Repository

```text
testlab-code/                       ← root repo codice (git init qui)
│
├── testlab/                        ← pacchetto Python principale
│   ├── __init__.py                 ← file vuoto
│   ├── core/
│   │   ├── __init__.py             ← inizializzatore core
│   │   ├── interfaces.py
│   │   ├── db.py
│   │   ├── plugin_loader.py
│   │   └── file_manager.py
│   └── notebooks/
│       ├── widgets.py
│       └── dashboard.ipynb         ← il notebook va QUI
│
├── scripts/                        ← script condivisi testtype
│   └── rendimento_std.py
│
├── projects/                       ← project.json di ogni progetto
│   └── (vuota per ora)
│
├── db/
│   ├── schema.sql
│   └── (testlab.sqlite creato automaticamente)
│
└── requirements.txt

testlab-data/                       ← repo dati separato (dvc init qui)
└── projects/
    └── (i CSV reali finiscono qui)