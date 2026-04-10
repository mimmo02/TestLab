# TestLab Project

Benvenuto in **TestLab**, una piattaforma modulare per la gestione di test e analisi dati.

## 🚀 Installazione e Setup

Segui questi passaggi per configurare l'ambiente di sviluppo e risolvere i problemi di dipendenze (come il mancato rilevamento di `pandas`).

### 1. Preparazione dell'ambiente
Posizionati nella cartella principale `testlab-code/` e crea un ambiente virtuale. Questo isola le librerie del progetto da quelle di sistema.

```bash
# Crea l'ambiente virtuale (eseguire una sola volta)
python -m venv venv

# ATTIVAZIONE (Windows PowerShell)
# Se ricevi l'errore "Esecuzione script disabilitata", esegui prima:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

.\venv\Scripts\activate

# ATTIVAZIONE (macOS/Linux)
source venv/bin/activate

# Installa tutti i pacchetti necessari
pip install -r requirements.txt

# Inizializza DVC nella cartella dati
cd ../testlab-data
dvc init

# Torna alla cartella del codice
cd ../testlab-code
python app.py
```

## Avvio Rapido (Windows)
Per evitare di digitare i comandi ogni volta, crea un file run_app.bat nella cartella testlab-code/ con questo contenuto:
```bash
@echo off
powershell -ExecutionPolicy Bypass -Command ".\venv\Scripts\activate; python app.py"
```
## Configurazione Git (.gitignore)
È fondamentale non caricare l'ambiente virtuale su Git. Assicurati che nella root del progetto sia presente un file chiamato .gitignore con il seguente contenuto:
```
# Ambiente Virtuale (cartella locale)
venv/
.venv/
env/

# Cache di Python
__pycache__/
*.py[cod]
*$py.class

# Database locale e file temporanei
db/*.sqlite
*.log

# Cartelle IDE (VS Code, PyCharm)
.vscode/
.idea/
```


## 📁 Struttura del progetto

### testlab-code/ (root repo codice)

```
testlab-code/
├── app.py                          # GUI Standalone (Tkinter)
├── testlab/                        # pacchetto Python principale
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── interfaces.py
│   │   ├── db.py                   # Gestione TestLabDB
│   │   ├── plugin_loader.py        # Caricamento dinamico script
│   │   └── file_manager.py         # Integrazione DVC/Git
│   └── notebooks/
│       ├── widgets.py
│       └── dashboard.ipynb         # Dashboard interattiva
├── scripts/                        # script condivisi
├── projects/                       # configurazioni project.json
├── db/
│   ├── schema.sql
│   └── testlab.sqlite              # Database locale
└── requirements.txt                # Dipendenze Python
```

### testlab-data/ (repo dati separato)

```
testlab-data/
└── projects/                       # storage fisico CSV/dati
```