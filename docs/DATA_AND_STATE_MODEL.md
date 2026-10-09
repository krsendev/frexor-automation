# Data and State Model

## 1. Current SQLite Ownership

Satu file SQLite menyimpan seluruh participant/job. File bukan dibuat per peserta.

```text
frexor-assessment.db
├── jobs
├── answers
└── module_runs
```

## 2. Current Relationships

```text
jobs 1 ---- 114 answers
jobs 1 ---- 3 module_runs
```

Per job normal:

- 24 DISC rows.
- 30 VAK rows.
- 60 IQ rows.
- 3 module status rows.

## 3. Job Fields

| Field | Fungsi |
|---|---|
| `id` | UUID internal queue |
| `external_id` | Idempotency key website |
| `name` | Nama yang digunakan Frexor |
| `position` | Posisi yang digunakan Frexor |
| `test_date` | Tanggal pengerjaan peserta |
| `status` | State job |
| `worker_id` | Worker pemilik lease |
| `lease_until` | Waktu ownership berakhir |
| `attempt_count` | Jumlah claim |
| `error_code` | Kode error terakhir |
| `last_error` | Pesan error terakhir |
| `pdf_path` | Path arsip lokal yang dilaporkan worker |
| timestamps | Audit waktu dasar |

## 4. Current State Transitions

```text
QUEUED -> CLAIMED -> PROCESSING -> DONE
                    |
                    +-> FAILED
                    +-> REVIEW_REQUIRED (lease expired)

CLAIMED --lease expired--> QUEUED
```

Module:

```text
PENDING -> PROCESSING -> DONE
                 |
                 +-> ERROR -> PROCESSING (explicit retry)
```

## 5. Current Data Retention Concern

SQLite menyimpan identitas dan jawaban psikologi. SQLite standar tidak mengenkripsi isi file. Keamanan bergantung pada permission OS, full-disk encryption, API authentication, encrypted backup, dan retention policy.

## 6. Planned Result Tables

### `result_files`

```sql
CREATE TABLE result_files (
  job_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  storage_path TEXT,
  original_filename TEXT,
  size_bytes INTEGER,
  page_count INTEGER,
  sha256 TEXT,
  error_code TEXT NOT NULL DEFAULT '',
  error_message TEXT NOT NULL DEFAULT '',
  uploaded_at TEXT,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);
```

Status:

```text
PENDING
MERGING
UPLOAD_PENDING
UPLOADING
AVAILABLE
ERROR
```

### `download_audit`

```sql
CREATE TABLE download_audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL,
  user_id TEXT NOT NULL,
  downloaded_at TEXT NOT NULL,
  ip_address TEXT NOT NULL,
  user_agent TEXT NOT NULL,
  FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
);
```

## 7. Finalization Rule Roadmap

```text
All modules DONE
  + merged PDF valid
  + upload confirmed
  + result status AVAILABLE
  = job selesai untuk dashboard
```

Gunakan `result_status` terpisah agar kegagalan merge/upload tidak menghilangkan fakta bahwa modul Frexor sudah selesai.

## 8. Deletion and Retention

Sebelum production, HR harus menentukan lama penyimpanan jawaban mentah, PDF, audit download, backup, prosedur penghapusan peserta, dan legal hold.
