# Frexor Automation System Design

## 1. Tujuan Dokumen

Dokumen ini menjelaskan desain teknis implementasi aktif dan target pengembangan PDF dashboard. Status fitur dibedakan menjadi `CURRENT` dan `PLANNED`.

## 2. Context Diagram

```text
Browser Peserta
      |
      v
Website Form + Backend
      |
      | webhook JSON
      v
Automation API Linux <------ Backend/Dashboard HR (PARTIAL)
FastAPI + SQLite
      ^
      | claim / answers / status / heartbeat
      v
Windows Worker
      |
      v
Frexor + Edge PDF
```

## 3. Deployment Topology

### Linux API Host

- FastAPI.
- SQLite database.
- systemd service.
- Result storage untuk merged PDF.
- Future reverse proxy dan HTTPS.

### Windows VM

- Active interactive user session.
- Python worker atau packaged executable.
- Frexor desktop application.
- Microsoft Edge sebagai default PDF viewer.
- Folder `Documents/Frexor PAS/{DISC,VAK,IQ}`.
- Local archive output.

### Website Host

- Form frontend.
- Backend PHP.
- MySQL website.
- Webhook token hanya pada backend.

## 4. Current Component Design

### 4.1 Automation API

Package: `src/frexor_api`.

Responsibilities:

- Validasi Pydantic.
- Authentication webhook/worker.
- Persistence SQLite.
- Idempotency.
- Atomic claim.
- Answer delivery.
- Module status transition.
- Heartbeat.
- Expired lease recovery.
- Read status.
- Menerima upload merged PDF, menyimpan metadata/checksum, dan menyediakan download by job ID.

### 4.2 Worker Runtime

Package: `src/frexor_automation`.

Responsibilities:

- Poll claim endpoint.
- Menyimpan ownership job aktif pada memory.
- Menjalankan heartbeat thread.
- Mengambil jawaban per modul.
- Validasi ulang data domain.
- Mengendalikan Frexor.
- Mendeteksi dan mengarsipkan PDF.
- Mengirim status modul.
- Menggabungkan PDF dan mengunggah hasil sebelum job menjadi `DONE`.

### 4.3 Website Integration

Responsibilities:

- Validasi session dan CSRF.
- Mapping database question ID ke nomor relatif.
- Normalisasi kapital.
- Membentuk kontrak webhook.
- Menyimpan `job_id`.
- Tidak menyamarkan downstream error sebagai HTTP 200.

## 5. Current Request Sequence

```text
Website Backend       API              SQLite          Worker       Frexor
      |                 |                 |               |            |
      | POST webhook    |                 |               |            |
      |---------------->| validate        |               |            |
      |                 | insert job      |               |            |
      |                 |---------------->|               |            |
      |<----------------| 201 + job_id    |               |            |
      |                 |                 |               |            |
      |                 | POST claim      |<--------------|            |
      |                 | atomic update   |               |            |
      |                 |---------------->|               |            |
      |                 | job metadata    |-------------->|            |
      |                 | GET answers     |<--------------|            |
      |                 | answers         |-------------->|            |
      |                 |                 |               | fill/submit|
      |                 |                 |               |----------->|
      |                 | PATCH status    |<--------------|            |
```

## 6. Queue and Concurrency

- SQLite hanya dibuka oleh API host.
- Worker tidak memiliki akses filesystem/database Linux.
- `BEGIN IMMEDIATE` mencegah dua claim menulis bersamaan.
- Update claim memakai predicate `status = 'QUEUED'`.
- Worker ID dan lease diperiksa pada endpoint worker.
- Model operasional utama tetap satu worker memproses satu job.

## 7. Failure Safety

### Before Processing

`CLAIMED` dengan lease expired aman dikembalikan ke `QUEUED` karena belum ada modul yang dimulai.

### During Processing

`PROCESSING` dengan lease expired menjadi `REVIEW_REQUIRED`. Sistem tidak dapat memastikan apakah tombol submit sudah ditekan.

### PDF Created, Status Not Saved

Worker memeriksa archive PDF untuk memulihkan modul tanpa submit ulang.

### Network Lost

Heartbeat berhenti. Lease akan expired. Job aktif tidak boleh langsung diproses worker lain jika sudah `PROCESSING`.

## 8. Current Result Pipeline

```text
DISC.pdf ----+
VAK.pdf -----+--> Merge --> Validate --> SHA-256 --> Upload
IQ.pdf ------+                                      |
                                                   v
                                      Linux Result Storage
                                                   |
                                                   v
                                           Dashboard Download
```

### Merge Rules

- Input order fixed: DISC, VAK, IQ.
- Semua input wajib valid.
- Output dibuat pada temporary path.
- Setelah valid, output dipindahkan secara atomik.
- Source PDFs tidak dihapus sampai upload confirmed.

### Upload Rules

- Endpoint worker-only.
- Multipart upload.
- Server menghitung checksum sendiri.
- Duplicate upload untuk checksum sama bersifat idempotent.
- Checksum berbeda pada job yang sama ditolak dan membutuhkan review.

## 9. Current Server Storage

```text
/var/lib/frexor-automation/
├── frexor-assessment.db
└── results/
    └── <job_id>/
        └── Hasil Psikotes <DD-MM-YYYY> <posisi> <nama>.pdf
```

Storage path tidak dikirim langsung kepada browser. Direktori dan file dibatasi dengan permission OS.

## 10. Dashboard Boundary

Dashboard menggunakan backend sendiri atau server-side routes. Browser tidak menerima worker/webhook token.

Download by job ID sudah tersedia. List, filter, login, role, dan audit dashboard masih planned.

Minimal views:

- Login.
- Job list.
- Job detail.
- Result availability.
- Download.
- Review-required queue.
- Audit history.

## 11. Security Boundaries

| Boundary | Credential |
|---|---|
| Website backend ke API | Webhook token |
| Windows worker ke API | Worker token |
| HR ke dashboard | User session dan role |
| Admin ke server | SSH/OS account |

Token tidak boleh digunakan lintas boundary.

## 12. Scaling Boundary

SQLite sesuai selama:

- satu API instance menjadi writer;
- volume internal kecil-menengah;
- query dashboard memakai pagination;
- file PDF tidak disimpan sebagai BLOB;
- worker berkomunikasi hanya melalui API.

Evaluasi PostgreSQL atau object storage ketika API perlu multi-instance, volume meningkat signifikan, atau reporting menjadi berat.

