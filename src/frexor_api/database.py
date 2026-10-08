"""
Program ini berfungsi untuk membuka koneksi ke database
dan mengatur transaksi ke database secara otomatis
"""

import sqlite3
from contextlib import contextmanager
import os
from pathlib import Path
from typing import Iterator

# Membuat direktori /data dan file .db pada lokasi file database.py berada
DATABASE_PATH = Path(
  os.getenv(
    "FREXOR_DATABASE_PATH",
    str(
      Path(__file__).resolve().parent
      / "data"
      / "frexor-assessment.db"
    ),
  )
).expanduser().resolve()

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  external_id TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  position TEXT NOT NULL,
  test_date TEXT NOT NULL,

  status TEXT NOT NULL DEFAULT 'QUEUED'
    CHECK (
      status IN (
        'QUEUED',
        'CLAIMED',
        'PROCESSING',
        'DONE',
        'RETRY_PENDING',
        'FAILED',
        'REVIEW_REQUIRED'
      )
    ),
  worker_id TEXT,
  lease_until TEXT,

  attempt_count INTEGER NOT NULL DEFAULT 0,

  last_error TEXT NOT NULL DEFAULT '',
  error_code TEXT NOT NULL DEFAULT '',
  pdf_path TEXT NOT NULL DEFAULT '',

  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS answers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL,
  module TEXT NOT NULL
    CHECK (
      module IN (
        'DISC',
        'VAK',
        'IQ'
      )
    ),

  question_no INTEGER NOT NULL,

  answer TEXT,
  mirip TEXT,
  tidak_mirip TEXT,

  FOREIGN KEY (job_id)
    REFERENCES jobs(id)
    ON DELETE CASCADE,

  UNIQUE (
    job_id,
    module,
    question_no
  )
);

CREATE TABLE IF NOT EXISTS module_runs (
  job_id TEXT NOT NULL,
  module TEXT NOT NULL
    CHECK (
      module IN (
        'DISC',
        'VAK',
        'IQ'
      )
    ),

  status TEXT NOT NULL DEFAULT 'PENDING'
    CHECK (
      status IN (
        'PENDING',
        'PROCESSING',
        'DONE',
        'ERROR'
      )
    ),

  attempt_count INTEGER NOT NULL DEFAULT 0,

  error_code TEXT NOT NULL DEFAULT '',
  error_message TEXT NOT NULL DEFAULT '',
  pdf_path TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL,

  PRIMARY KEY (
    job_id,
    module
  ),

  FOREIGN KEY (job_id)
    REFERENCES jobs(id)
    ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_jobs_queue
ON jobs (
  status,
  created_at
);

CREATE INDEX IF NOT EXISTS idx_answer_job_module
ON answers (
  job_id,
  module,
  question_no
);
"""

# Fungsi connect untuk query read sederhana
def connect() -> sqlite3.Connection:
  DATABASE_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
  )
  # deteksi file .db, jika tidak ada dibuat otomatis oleh SQLite
  connection = sqlite3.connect(
    DATABASE_PATH,
    timeout=30,
  )
  # Menggunakan row_factory agar bisa dibaca berdasarkan nama kolom
  connection.row_factory = sqlite3.Row

  # Foreign key diaktifkan, karena SQLite tidak secara default mengaktifkannya
  connection.execute(
    "PRAGMA foreign_keys = ON"
  )

  # WAL = Write-Ahead Logging, setiap perubahan akan ditulis ke WAL dan digabung ke db utama
  connection.execute(
    "PRAGMA journal_mode = WAL"
  )
  return connection

# Fungsi transaction digunakan untuk operasi write
@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
  connection = connect()

  try:
    connection.execute(
      "BEGIN IMMEDIATE"
    )

    yield connection

    connection.commit()
  except Exception:
    connection.rollback()
    raise
  finally:
    connection.close()

def initializeDatabase() -> None:
  connection = connect()

  try:
    connection.executescript(
      SCHEMA
    )
    connection.commit()
  except Exception:
    connection.rollback()
    raise
  finally:
    connection.close()
