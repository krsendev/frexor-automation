'''
Program ini bertanggung jawab untuk membaca konfigurasi
dari environment variable.
'''

import os
from pathlib import Path

def requiredEnvironment(name: str) -> str:
  value = os.getenv(name, "").strip()
  if not value:
    raise RuntimeError(f"Environment variable {name} wajib diisi")
  return value

WEBHOOK_TOKEN = requiredEnvironment("FREXOR_WEBHOOK_TOKEN")
WORKER_TOKEN = requiredEnvironment("FREXOR_WORKER_TOKEN")
RESULT_STORAGE_PATH = Path(
  os.getenv(
    "FREXOR_RESULT_STORAGE_PATH",
    str(Path(__file__).resolve().parent / "data" / "results"),
  )
).expanduser().resolve()
MAX_RESULT_BYTES = int(os.getenv("FREXOR_MAX_RESULT_BYTES", str(50 * 1024 * 1024)))

if WEBHOOK_TOKEN == WORKER_TOKEN:
  raise RuntimeError(
    "FREXOR_WEBHOOK_TOKEN dan FREXOR_WORKER_TOKEN wajib berbeda"
  )
