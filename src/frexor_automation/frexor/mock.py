from __future__ import annotations

from ..domain import ChoiceAnswer, DiscAnswer, Module, Participant
from .base import FrexorAdapter


class MockFrexorAdapter(FrexorAdapter):
    def __init__(self, fail_at: tuple[Module, int] | None = None, verify: bool = True):
        self.fail_at = fail_at
        self.verify = verify
        self.actions: list[str] = []

    def check_environment(self) -> None:
        self.actions.append("check_environment")

    def launch_or_connect(self) -> None:
        self.actions.append("launch_or_connect")

    def open_participant(self, participant: Participant) -> None:
        self.actions.append(f"participant:{participant.participant_id}")

    def open_module(self, module: Module) -> None:
        self.actions.append(f"open:{module}")

    def fill_disc_question(self, answer: DiscAnswer) -> None:
        if self.fail_at == (Module.DISC, answer.question_no):
            raise RuntimeError(f"Simulated DISC Q{answer.question_no} failure")
        self.actions.append(f"DISC:{answer.question_no}:{answer.mirip}:{answer.tidak_mirip}")

    def fill_choice_question(self, module: Module, answer: ChoiceAnswer) -> None:
        if self.fail_at == (module, answer.question_no):
            raise RuntimeError(f"Simulated {module} Q{answer.question_no} failure")
        self.actions.append(f"{module}:{answer.question_no}:{answer.answer}")

    def submit(self, module: Module) -> None:
        self.actions.append(f"submit:{module}")

    def verify_submission(self, module: Module) -> bool:
        self.actions.append(f"verify:{module}")
        return self.verify

    def recover_from_error(self) -> bool:
        self.actions.append("recover")
        return True

