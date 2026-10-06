from __future__ import annotations

import os
from pathlib import Path

from frexor_automation.ui import run_ui


def main() -> None:
    app_data = os.environ.get("APPDATA")
    base = Path(app_data) / "FrexorAssessmentAutomation" if app_data else Path.cwd()
    base.mkdir(parents=True, exist_ok=True)
    run_ui(base / "config.toml")


if __name__ == "__main__":
    main()
