from __future__ import annotations

import os
from pathlib import Path
import sys

from frexor_automation.cli import main


def default_config_path() -> Path:
    if configured := os.environ.get("FREXOR_CONFIG_PATH", "").strip():
        return Path(configured).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "config.toml"
    return Path(__file__).resolve().parent / "config.toml"


def enable_bootstrap_log() -> None:
    if sys.stdout is not None and sys.stderr is not None:
        return
    app_data = Path(os.environ.get("APPDATA", Path(sys.executable).resolve().parent))
    log_directory = app_data / "FrexorAssessmentAutomation"
    log_directory.mkdir(parents=True, exist_ok=True)
    stream = (log_directory / "worker-bootstrap.log").open(
        "a", encoding="utf-8", buffering=1
    )
    sys.stdout = stream
    sys.stderr = stream


if __name__ == "__main__":
    enable_bootstrap_log()
    arguments = sys.argv[1:]
    if not arguments:
        arguments = ["--config", str(default_config_path()), "worker"]
    raise SystemExit(main(arguments))
