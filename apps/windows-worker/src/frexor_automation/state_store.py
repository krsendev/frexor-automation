from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile


@dataclass
class RunState:
    lifecycle: str = "IDLE"
    current_participant_id: str = ""
    current_module: str = ""
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    last_error_code: str = ""
    updated_at: str = ""


class RunStateStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> RunState:
        if not self.path.exists():
            return RunState()
        try:
            return RunState(**json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            return RunState(lifecycle="RECOVERY_REQUIRED")

    def save(self, state: RunState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        state.updated_at = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(asdict(state), indent=2, ensure_ascii=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.path.parent, delete=False, suffix=".tmp"
        ) as handle:
            handle.write(payload)
            temporary = Path(handle.name)
        temporary.replace(self.path)
