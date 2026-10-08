'''
Program ini bertanggung jawab untuk membaca konfigurasi
dari environment variable.
'''

import os

def requiredEnvironment(name: str) -> str:
  value = os.getenv(name, "").strip()
  if not value:
    raise RuntimeError(f"Environment variable {name} wajib diisi")
  return value

WEBHOOK_TOKEN = requiredEnvironment("FREXOR_WEBHOOK_TOKEN")
WORKER_TOKEN = requiredEnvironment("FREXOR_WORKER_TOKEN")

if WEBHOOK_TOKEN == WORKER_TOKEN:
  raise RuntimeError(
    "FREXOR_WEBHOOK_TOKEN dan FREXOR_WORKER_TOKEN wajib berbeda"
  )
