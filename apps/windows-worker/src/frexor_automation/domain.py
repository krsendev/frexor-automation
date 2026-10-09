from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum
from typing import TypeAlias


class Module(StrEnum):
    DISC = "DISC"
    VAK = "VAK"
    IQ = "IQ"


class Status(StrEnum):
    READY = "READY"
    PROCESSING = "PROCESSING"
    PARTIAL = "PARTIAL"
    DONE = "DONE"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


@dataclass(frozen=True)
class DiscAnswer:
    question_no: int
    mirip: str
    tidak_mirip: str


@dataclass(frozen=True)
class ChoiceAnswer:
    question_no: int
    answer: str


Answers: TypeAlias = list[DiscAnswer] | list[ChoiceAnswer]
FREXOR_IDENTITY_MAX_LENGTH = 20


def frexor_identity(value: str) -> str:
    return value.strip()[:FREXOR_IDENTITY_MAX_LENGTH].rstrip()


@dataclass
class Participant:
    participant_id: str
    name: str
    position: str
    overall_status: Status = Status.READY
    module_statuses: dict[Module, Status] = field(
        default_factory=lambda: {module: Status.READY for module in Module}
    )
    last_error: str = ""
    error_code: str = ""
    attempt_count: int = 0
    pdf_status: str = "PENDING"
    pdf_path: str = ""
    test_date: date | None = None

    def pending_modules(self, retry_errors: bool = False) -> list[Module]:
        allowed = {Status.READY}
        if retry_errors:
            allowed.add(Status.ERROR)
        return [m for m in Module if self.module_statuses[m] in allowed]


def calculate_overall_status(statuses: dict[Module, Status]) -> Status:
    values = set(statuses.values())
    if values == {Status.DONE} or values <= {Status.DONE, Status.SKIPPED}:
        return Status.DONE
    if values == {Status.READY}:
        return Status.READY
    if Status.PROCESSING in values:
        return Status.PROCESSING
    if Status.DONE in values or Status.SKIPPED in values:
        return Status.PARTIAL
    if Status.ERROR in values and values <= {Status.ERROR}:
        return Status.ERROR
    if Status.ERROR in values:
        return Status.PARTIAL
    return Status.READY
