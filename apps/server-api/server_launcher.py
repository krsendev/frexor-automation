from __future__ import annotations

import os
from pathlib import Path
import sys
import time

from dotenv import load_dotenv


def application_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def enable_file_output(base: Path) -> None:
    if sys.stdout is not None and sys.stderr is not None:
        return
    log_directory = base / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    stream = (log_directory / "server.log").open("a", encoding="utf-8", buffering=1)
    sys.stdout = stream
    sys.stderr = stream


def acquire_single_instance(base: Path):
    import msvcrt

    lock_path = base / "frexor-server.lock"
    handle = lock_path.open("a+b")
    if lock_path.stat().st_size == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        print("Frexor Server instance lain sudah berjalan.")
        raise SystemExit(1)
    return handle


if __name__ == "__main__":
    base = application_directory()
    enable_file_output(base)
    load_dotenv(base / ".env")
    os.chdir(base)
    instance_lock = acquire_single_instance(base)
    from frexor_api.run import main

    while True:
        try:
            main()
        except Exception as exc:
            print(f"Frexor Server berhenti karena error: {exc}; restart dalam 15 detik.")
        time.sleep(15)
