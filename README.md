# Frexor Automation Platform

Repository ini berisi dua aplikasi terpisah yang berkomunikasi melalui HTTP.

```text
Website backend
      |
      v
Frexor Server API ---- SQLite + Result Storage
      |
      v
Windows Worker ---- Frexor ---- PDF
```

## Struktur Repository

```text
apps/
├── server-api/
│   ├── src/frexor_api/       FastAPI, SQLite queue, upload/download PDF
│   ├── tests/                Test khusus server
│   ├── scripts/              Build, start, stop, backup, test webhook
│   ├── deploy/               Unit service Linux
│   ├── pyproject.toml        Dependency server
│   └── .env.windows.example  Contoh konfigurasi Windows
└── windows-worker/
    ├── src/frexor_automation/ Worker dan UI Automation
    ├── tests/                 Test khusus worker
    ├── scripts/               Build, start, stop, Startup installer
    ├── templates/             Template data Sheets/Excel
    ├── test-data/             Data dummy
    ├── pyproject.toml         Dependency worker
    ├── config.example.toml
    └── frexor_ui_map.example.toml

docs/                        Design, API contract, deployment, runbook
PRD/                         Product requirements
```

Server dan worker tidak lagi memakai satu `pyproject.toml`. Install dependency dari direktori aplikasi masing-masing.

## Deployment Satu VM Windows

Panduan utama:

- `docs/WINDOWS_SINGLE_VM_DEPLOYMENT.md`
- `docs/WINDOWS_BACKGROUND_WORKER.md`
- `docs/API_CONTRACT.md`

Topologi ketika seluruh sistem wajib berada pada satu VM:

```text
Web server/backend + MySQL
Frexor Server.exe + SQLite + result storage
Frexor Worker.exe + Frexor + Edge
```

Backend web dan worker memakai `http://127.0.0.1:8000`. Port FastAPI tidak perlu dibuka ke LAN jika hanya backend web yang mengaksesnya.

## Development Server API

```powershell
cd apps\server-api
py -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[test]"
Copy-Item .env.windows.example .env
.venv\Scripts\python.exe -m frexor_api.run
```

Test:

```powershell
$env:FREXOR_WEBHOOK_TOKEN = "test-webhook-token"
$env:FREXOR_WORKER_TOKEN = "test-worker-token"
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Development Windows Worker

```powershell
cd apps\windows-worker
py -m venv .venv
.venv\Scripts\python.exe -m pip install -e .
Copy-Item config.example.toml config.toml
Copy-Item .env.example .env
Copy-Item frexor_ui_map.example.toml frexor_ui_map.toml
.venv\Scripts\python.exe -m frexor_automation.cli --config config.toml worker
```

Test:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Build Executable Windows

Server:

```powershell
cd apps\server-api
powershell -ExecutionPolicy Bypass -File scripts\build_server_windows.ps1
```

Worker:

```powershell
cd apps\windows-worker
powershell -ExecutionPolicy Bypass -File scripts\build_worker_windows.ps1
```

## Data dan Secret

Jangan commit `.env`, `config.toml`, token, credential, database production, log, atau PDF peserta. Token worker disimpan sebagai `FREXOR_WORKER_TOKEN` pada `apps/windows-worker/.env`, bukan di `config.toml`.

Gunakan folder data di luar source code:

```text
C:\FrexorPlatform\data\
├── database\
├── results\
├── worker-output\
├── logs\
└── backups\
```

## Dokumentasi

Mulai dari `docs/PROJECT_DOCUMENTATION_INDEX.md`. Requirement induk berada di `PRD/PRD_Frexor_Automation_Platform_v3.md`.
