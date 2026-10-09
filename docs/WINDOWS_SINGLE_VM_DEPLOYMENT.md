# Deployment Ulang Satu VM Windows

## 1. Target Struktur VM

```text
C:\FrexorPlatform\
├── source\                         Git repository
├── runtime\
│   ├── server\                     Hasil build Frexor Server
│   └── worker\                     Hasil build Frexor Worker
└── data\
    ├── database\                   SQLite automation
    ├── results\                    PDF pada server API
    ├── worker-output\              DISC/VAK/IQ dan merged PDF lokal
    ├── logs\
    └── backups\
```

MySQL dan backend website boleh berada pada VM yang sama, tetapi datanya tetap terpisah dari SQLite automation.

## 2. Prasyarat

- Windows 10/11 atau Windows Server dengan desktop interaktif.
- Akun Windows khusus automation.
- Python 3.11 atau 3.12 hanya untuk build.
- Git.
- Microsoft Visual C++ Redistributable sesuai kebutuhan PyInstaller/Python.
- Frexor terpasang dan dapat digunakan manual.
- Microsoft Edge sebagai PDF viewer.
- Minimal ruang kosong 20 GB; lebih besar disarankan.
- VM tidak dikunci/logout ketika worker memproses job.
- Hak tulis akun automation ke seluruh `C:\FrexorPlatform\data`.
- Token webhook dan worker yang berbeda.

Periksa:

```powershell
py --version
git --version
Get-PSDrive C
```

Versi Python harus memiliki arsitektur yang sama dengan Windows, umumnya 64-bit. Build executable wajib dilakukan di Windows; executable Windows tidak dapat dibangun dari Linux.

## 3. Clone atau Update Source

Instalasi baru:

```powershell
New-Item -ItemType Directory -Force C:\FrexorPlatform | Out-Null
Set-Location C:\FrexorPlatform
git clone https://github.com/krsendev/frexor-automation.git source
Set-Location source
```

Update source:

```powershell
Set-Location C:\FrexorPlatform\source
git status --short
git pull origin main
```

Jangan menjalankan `git pull` jika ada perubahan lokal yang belum disimpan.

## 4. Buat Folder Data

```powershell
$Folders = @(
  "C:\FrexorPlatform\data\database",
  "C:\FrexorPlatform\data\results",
  "C:\FrexorPlatform\data\worker-output",
  "C:\FrexorPlatform\data\logs",
  "C:\FrexorPlatform\data\backups",
  "C:\FrexorPlatform\runtime\server",
  "C:\FrexorPlatform\runtime\worker"
)
$Folders | ForEach-Object { New-Item -ItemType Directory -Force $_ | Out-Null }
```

## 5. Stop Sebelum Update/Build

Hentikan worker terlebih dahulu, lalu server:

```powershell
Set-Location C:\FrexorPlatform\source

powershell -ExecutionPolicy Bypass `
  -File apps\windows-worker\scripts\stop_worker.ps1

powershell -ExecutionPolicy Bypass `
  -File apps\server-api\scripts\stop_server.ps1
```

Pastikan:

```powershell
Get-Process "Frexor Worker","Frexor Server" -ErrorAction SilentlyContinue
```

Command tersebut seharusnya tidak mengembalikan proses.

## 6. Build Server API

```powershell
Set-Location C:\FrexorPlatform\source\apps\server-api
powershell -ExecutionPolicy Bypass -File scripts\build_server_windows.ps1
```

Deploy hasil build tanpa menyalin `.env` lama:

```powershell
$ServerBuild = "C:\FrexorPlatform\source\apps\server-api\dist\Frexor Server"
$ServerRuntime = "C:\FrexorPlatform\runtime\server"

Copy-Item "$ServerBuild\*" $ServerRuntime -Recurse -Force
```

Buat `C:\FrexorPlatform\runtime\server\.env`:

```env
FREXOR_WEBHOOK_TOKEN=<token-webhook>
FREXOR_WORKER_TOKEN=<token-worker-yang-berbeda>
FREXOR_DATABASE_PATH=C:\FrexorPlatform\data\database\frexor-assessment.db
FREXOR_RESULT_STORAGE_PATH=C:\FrexorPlatform\data\results
FREXOR_MAX_RESULT_BYTES=52428800
FREXOR_API_HOST=127.0.0.1
FREXOR_API_PORT=8000
```

Token harus panjang, random, berbeda, dan tidak dimasukkan ke Git.

Buat token dari PowerShell jika OpenSSL tidak tersedia:

```powershell
$Bytes = New-Object byte[] 32
[Security.Cryptography.RandomNumberGenerator]::Fill($Bytes)
[Convert]::ToHexString($Bytes).ToLower()
```

## 7. Build Windows Worker

```powershell
Set-Location C:\FrexorPlatform\source\apps\windows-worker
powershell -ExecutionPolicy Bypass -File scripts\build_worker_windows.ps1
```

Deploy hasil build:

```powershell
$WorkerBuild = "C:\FrexorPlatform\source\apps\windows-worker\dist\Frexor Worker"
$WorkerRuntime = "C:\FrexorPlatform\runtime\worker"

Copy-Item "$WorkerBuild\*" $WorkerRuntime -Recurse -Force
```

Buat `C:\FrexorPlatform\runtime\worker\config.toml` berdasarkan `config.example.toml`.

Bagian minimum:

```toml
[data_source]
type = "api"

[frexor]
adapter = "windows"
executable_path = "C:\\Program Files\\Frexor\\Frexor.exe"
window_title_re = "^Frexor Psychology Assessment System$"
window_class_name = "GlassWndClass-GlassWindowClass-2"
startup_timeout_seconds = 30
action_timeout_seconds = 10
ui_map_path = "frexor_ui_map.toml"
close_after_success = true
close_edge_after_success = true

[api]
base_url = "http://127.0.0.1:8000"
token = "<token-worker-yang-sama-dengan-server>"
timeout_seconds = 30
worker_id = "frexor-vm-01"
poll_interval_seconds = 5
heartbeat_interval_seconds = 60

[pdf]
base_directory = "C:\\Users\\User\\Documents\\Frexor PAS"
output_directory = "C:\\FrexorPlatform\\data\\worker-output"
timeout_seconds = 60
poll_interval_seconds = 0.5
stable_seconds = 1.0
minimum_size_bytes = 100

[pdf.module_directories]
DISC = "DISC"
VAK = "VAK"
IQ = "IQ"

[logging]
level = "INFO"
directory = "C:\\FrexorPlatform\\data\\logs\\worker"
```

Salin UI map yang sudah terbukti bekerja:

```powershell
Copy-Item `
  "C:\FrexorPlatform\source\apps\windows-worker\frexor_ui_map.example.toml" `
  "C:\FrexorPlatform\runtime\worker\frexor_ui_map.toml" `
  -Force
```

Jika VM lama memiliki `frexor_ui_map.toml` yang sudah disesuaikan, gunakan file lama tersebut.

## 8. Start Manual Pertama

Server:

```powershell
Set-Location C:\FrexorPlatform\source
powershell -ExecutionPolicy Bypass `
  -File apps\server-api\scripts\start_server.ps1 `
  -ServerDirectory "C:\FrexorPlatform\runtime\server"
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Worker:

```powershell
powershell -ExecutionPolicy Bypass `
  -File apps\windows-worker\scripts\start_worker.ps1 `
  -WorkerDirectory "C:\FrexorPlatform\runtime\worker"
```

Periksa proses:

```powershell
Get-Process "Frexor Server","Frexor Worker" -ErrorAction SilentlyContinue
```

## 9. Pasang Auto Start

Server:

```powershell
powershell -ExecutionPolicy Bypass `
  -File C:\FrexorPlatform\source\apps\server-api\scripts\install_server_startup.ps1 `
  -ServerDirectory "C:\FrexorPlatform\runtime\server"
```

Worker:

```powershell
powershell -ExecutionPolicy Bypass `
  -File C:\FrexorPlatform\source\apps\windows-worker\scripts\install_worker_task.ps1 `
  -WorkerDirectory "C:\FrexorPlatform\runtime\worker"
```

Worker mencoba Task Scheduler lalu otomatis memakai Startup shortcut jika VM mengembalikan `HRESULT 0x80041316`.

## 10. Command Operasional Harian

### Stop Semua

```powershell
Stop-Process -Name "Frexor Worker" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "Frexor Server" -Force -ErrorAction SilentlyContinue
```

### Start Server

```powershell
powershell -ExecutionPolicy Bypass `
  -File C:\FrexorPlatform\source\apps\server-api\scripts\start_server.ps1 `
  -ServerDirectory "C:\FrexorPlatform\runtime\server"
```

### Start Worker

```powershell
powershell -ExecutionPolicy Bypass `
  -File C:\FrexorPlatform\source\apps\windows-worker\scripts\start_worker.ps1 `
  -WorkerDirectory "C:\FrexorPlatform\runtime\worker"
```

### Restart Semua

```powershell
Stop-Process -Name "Frexor Worker" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "Frexor Server" -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

powershell -ExecutionPolicy Bypass `
  -File C:\FrexorPlatform\source\apps\server-api\scripts\start_server.ps1 `
  -ServerDirectory "C:\FrexorPlatform\runtime\server"

Start-Sleep -Seconds 3

powershell -ExecutionPolicy Bypass `
  -File C:\FrexorPlatform\source\apps\windows-worker\scripts\start_worker.ps1 `
  -WorkerDirectory "C:\FrexorPlatform\runtime\worker"
```

### Build Ulang Setelah Git Pull

```powershell
Set-Location C:\FrexorPlatform\source
git pull origin main

Stop-Process -Name "Frexor Worker" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "Frexor Server" -Force -ErrorAction SilentlyContinue

Set-Location apps\server-api
powershell -ExecutionPolicy Bypass -File scripts\build_server_windows.ps1
Copy-Item ".\dist\Frexor Server\*" "C:\FrexorPlatform\runtime\server" -Recurse -Force

Set-Location ..\windows-worker
powershell -ExecutionPolicy Bypass -File scripts\build_worker_windows.ps1
Copy-Item ".\dist\Frexor Worker\*" "C:\FrexorPlatform\runtime\worker" -Recurse -Force
```

Setelah copy, pastikan file `.env`, `config.toml`, dan `frexor_ui_map.toml` masih ada dan benar. File tersebut tidak boleh diganti dengan file example.

Jalankan health check dan satu dummy setelah setiap build ulang. Jangan langsung membuka antrean produksi sebelum verifikasi selesai.

## 11. Log dan Diagnosis

Server:

```powershell
Get-Content "C:\FrexorPlatform\runtime\server\logs\server.log" -Tail 100 -Wait
```

Worker:

```powershell
Get-Content "C:\FrexorPlatform\data\logs\worker\automation.log" -Tail 100 -Wait
```

Bootstrap worker:

```powershell
Get-Content "$env:APPDATA\FrexorAssessmentAutomation\worker-bootstrap.log" -Tail 100
```

Port API:

```powershell
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue
```

## 12. Uji Setelah Deploy

1. `GET /health` menghasilkan `{"status":"ok"}`.
2. Worker hanya satu proses.
3. Kirim satu dummy dengan `external_id` baru.
4. DISC, VAK, dan IQ selesai.
5. Merged PDF dibuat.
6. Result tersimpan di `C:\FrexorPlatform\data\results\<job_id>\`.
7. Status job `DONE` dan `result.available=true`.
8. Endpoint download menghasilkan PDF valid.
9. Frexor dan Edge tertutup setelah sukses.
10. Job kedua dengan nama/tanggal sama tidak membuka Save As.

## 13. Backup

Jangan backup SQLite dengan copy biasa ketika aktif. Gunakan script:

```powershell
Set-Location C:\FrexorPlatform\source\apps\server-api
.venv\Scripts\python.exe scripts\backup_sqlite.py `
  "C:\FrexorPlatform\data\database\frexor-assessment.db" `
  "C:\FrexorPlatform\data\backups"
```

Backup juga folder `results` ke storage lain. Backup pada disk VM yang sama tidak melindungi dari kerusakan VM.

## 14. Rollback Sederhana

Sebelum mengganti runtime:

```powershell
Copy-Item "C:\FrexorPlatform\runtime\server" "C:\FrexorPlatform\runtime\server-backup" -Recurse -Force
Copy-Item "C:\FrexorPlatform\runtime\worker" "C:\FrexorPlatform\runtime\worker-backup" -Recurse -Force
```

Jika build baru gagal, stop proses, kembalikan folder backup, lalu start server dan worker. Jangan rollback database tanpa prosedur restore yang teruji.

## 15. Hapus Auto Start

Server:

```powershell
powershell -ExecutionPolicy Bypass `
  -File C:\FrexorPlatform\source\apps\server-api\scripts\uninstall_server_startup.ps1
```

Worker:

```powershell
powershell -ExecutionPolicy Bypass `
  -File C:\FrexorPlatform\source\apps\windows-worker\scripts\uninstall_worker_task.ps1
```

Perintah tersebut menghentikan proses terkait dan menghapus konfigurasi auto start. Database, PDF, konfigurasi, dan source code tidak dihapus.

## 16. Urutan Deployment Ringkas

1. Backup SQLite dan folder result.
2. Pastikan antrean kosong, lalu stop worker dan server.
3. Jalankan `git status --short`; simpan perubahan lokal sebelum `git pull`.
4. Pull source terbaru.
5. Build server dan worker dari direktori aplikasi masing-masing.
6. Salin hasil build ke folder runtime tanpa mengganti konfigurasi aktif.
7. Start server, jalankan health check, lalu start worker.
8. Kirim satu peserta dummy dan verifikasi PDF dapat diunduh.
9. Buka kembali integrasi website setelah seluruh pemeriksaan lulus.
