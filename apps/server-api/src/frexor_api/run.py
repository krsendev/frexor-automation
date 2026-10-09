from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
import uvicorn


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    host = os.getenv("FREXOR_API_HOST", "0.0.0.0")
    port = int(os.getenv("FREXOR_API_PORT", "8000"))
    uvicorn.run("frexor_api.main:app", host=host, port=port)


if __name__ == "__main__":
    main()
