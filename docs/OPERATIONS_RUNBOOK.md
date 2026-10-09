# Operations Runbook

## 1. Daily Start

### Server API

```powershell
Get-Process "Frexor Server" -ErrorAction SilentlyContinue
Invoke-RestMethod http://127.0.0.1:8000/health
```

### Windows Worker

- Login operator.
- Pastikan desktop tidak terkunci.
- Pastikan Frexor dapat dibuka.
- Pastikan folder DISC, VAK, IQ tersedia.
- Pastikan hanya satu worker berjalan.

## 2. Normal Indicators

- Claim polling mengembalikan `204` saat antrean kosong.
- Heartbeat POST muncul hanya ketika job aktif.
- Job bergerak `QUEUED -> CLAIMED -> PROCESSING -> DONE`.
- Tiga PDF lokal tersedia setelah sukses.

## 3. First Response by Status

### FAILED

- Baca `error_code` dan modul.
- Jangan langsung mengubah database.
- Periksa log worker tanpa menyalin token atau jawaban.
- Retry hanya setelah penyebab diketahui.

### REVIEW_REQUIRED

- Periksa Frexor dan folder PDF.
- Tentukan apakah submit sudah terjadi.
- Jangan requeue otomatis.
- Dokumentasikan keputusan operator.

### QUEUED Lama

- Pastikan worker hidup.
- Pastikan token dan URL benar.
- Uji `/health` dari Windows.
- Pastikan tidak ada instance lock lama.

## 4. Backup

```powershell
Set-Location C:\FrexorPlatform\source\apps\server-api
.venv\Scripts\python.exe scripts\backup_sqlite.py `
  "C:\FrexorPlatform\data\database\frexor-assessment.db" `
  "C:\FrexorPlatform\data\backups"
```

Verify:

```powershell
.venv\Scripts\python.exe -c "import sqlite3; print(sqlite3.connect(r'C:\path\backup.db').execute('PRAGMA integrity_check').fetchone()[0])"
```

Backup file menerima perlindungan yang sama dengan database utama.

## 5. Restore Drill

1. Hentikan API test atau staging.
2. Salin backup ke lokasi database staging.
3. Jalankan `PRAGMA integrity_check`.
4. Start API staging.
5. Periksa job dan status.
6. Jangan melakukan restore pertama kali pada production tanpa rehearsal.

## 6. Secret Rotation

### Webhook Token

- Buat token baru.
- Update backend website.
- Update environment API.
- Restart API.
- Test submission dummy.

### Worker Token

- Buat token baru.
- Update Windows config atau secret.
- Update environment API.
- Restart API dan worker.
- Test claim dummy.

Jangan menggunakan token yang sama untuk webhook dan worker.

## 7. Logs

Log yang boleh:

```text
job_id
external_id bila diperlukan
module
status
error_code
timestamp
worker_id
```

Log yang dilarang:

```text
token
password
CSRF token
seluruh jawaban
payload lengkap
cookie/session
```

## 8. Incident Checklist

- Catat waktu kejadian.
- Catat job ID dan worker ID.
- Simpan status API.
- Hindari menjalankan job ulang sebelum status submit diketahui.
- Rotasi token jika muncul pada log, chat, atau source.
- Restore hanya dari backup terverifikasi.
