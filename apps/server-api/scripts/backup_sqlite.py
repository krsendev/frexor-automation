from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup database SQLite Frexor")
    parser.add_argument("source", type=Path)
    parser.add_argument("destination_directory", type=Path)
    args = parser.parse_args()

    source = args.source.expanduser().resolve()
    destination_directory = args.destination_directory.expanduser().resolve()
    if not source.is_file():
        parser.error(f"Database tidak ditemukan: {source}")

    destination_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = destination_directory / f"frexor-{timestamp}.db"

    with sqlite3.connect(source) as source_connection:
        with sqlite3.connect(destination) as destination_connection:
            source_connection.backup(destination_connection)
            result = destination_connection.execute("PRAGMA integrity_check").fetchone()

    if result is None or result[0] != "ok":
        destination.unlink(missing_ok=True)
        raise RuntimeError("Backup gagal melewati PRAGMA integrity_check")

    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
