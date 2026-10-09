# Production Deployment

## Arsitektur

```text
Frontend server -> FastAPI Linux -> SQLite -> Windows worker -> Frexor -> PDF
```

Frontend tidak boleh menyimpan `FREXOR_WORKER_TOKEN`. Frontend atau backend form hanya memakai webhook token dari sisi server. Jangan menaruh bearer token di JavaScript browser.

## Linux API

1. Buat dua token berbeda:

   ```bash
   openssl rand -hex 32
   openssl rand -hex 32
   ```

2. Salin repository ke `/opt/frexor-automation`, buat `.venv`, lalu install:

   ```bash
   cd /opt/frexor-automation/apps/server-api
   python3 -m venv .venv
   .venv/bin/python -m pip install -e .
   ```

3. Buat `/etc/frexor-automation.env` berdasarkan `apps/server-api/.env.example`. Batasi permission:

   ```bash
   sudo chmod 600 /etc/frexor-automation.env
   ```

4. Buat direktori database dan beri akses kepada user service:

   ```bash
   sudo install -d -o frexor -g frexor -m 750 /var/lib/frexor-automation
   ```

5. Salin `apps/server-api/deploy/frexor-api.service` ke `/etc/systemd/system/`, lalu jalankan:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now frexor-api
   sudo systemctl status frexor-api
   ```

6. Uji dari LAN:

   ```bash
   curl http://IP-SERVER:8000/health
   ```

## Windows Worker

1. Masuk ke `apps\windows-worker`, lalu install dengan `py -m pip install -e .`.
2. Salin `apps\windows-worker\config.example.toml` menjadi `config.toml`.
3. Atur `data_source.type = "api"`, adapter `windows`, URL API, worker token, worker ID, dan folder PDF.
4. Jalankan manual terlebih dahulu:

   ```powershell
   powershell -ExecutionPolicy Bypass -File apps\windows-worker\scripts\run_worker.ps1
   ```

5. Setelah dummy nyata lulus, build dan pasang executable background sesuai `docs/WINDOWS_BACKGROUND_WORKER.md`. Task Scheduler berjalan **saat operator login**, bukan saat boot. UI Automation membutuhkan desktop interaktif dan sesi Windows yang tidak terkunci.

## Kontrak Frontend

Kirim assessment dari backend frontend ke:

```http
POST /api/v1/webhooks/assessments
Authorization: Bearer <webhook-token>
Content-Type: application/json
```

Gunakan `external_id` unik dari database/form frontend. Request duplikat dengan `external_id` sama bersifat idempotent dan tidak membuat job kedua.

Periksa status melalui backend frontend:

```http
GET /api/v1/jobs/{job_id}
Authorization: Bearer <webhook-token>
```

## Gate Sebelum Data Nyata

- Mock end-to-end harus `DONE`.
- Satu peserta dummy harus menghasilkan tiga PDF yang benar.
- Simulasi crash sebelum dan sesudah submit harus diperiksa.
- Backup dan restore SQLite harus diuji.
- Token, database, log, PDF, dan data peserta tidak boleh masuk Git.
- API publik wajib berada di belakang HTTPS reverse proxy dan firewall.

## Backup SQLite

Gunakan SQLite backup API agar backup konsisten walaupun database memakai WAL:

```bash
/opt/frexor-automation/apps/server-api/.venv/bin/python \
  /opt/frexor-automation/apps/server-api/scripts/backup_sqlite.py \
  /var/lib/frexor-automation/frexor-assessment.db \
  /var/backups/frexor-automation
```

Jadwalkan dengan systemd timer atau cron, simpan terenkripsi, dan uji restore secara berkala. Jangan hanya menyalin file `.db` aktif sambil mengabaikan file WAL.
