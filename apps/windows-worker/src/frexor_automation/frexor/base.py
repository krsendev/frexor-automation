from __future__ import annotations

from abc import ABC, abstractmethod

from ..domain import ChoiceAnswer, DiscAnswer, Module, Participant


class FrexorAdapter(ABC):
    @abstractmethod
    def check_environment(self) -> None: ...

    @abstractmethod
    def launch_or_connect(self) -> None: ...

    @abstractmethod
    def open_participant(self, participant: Participant) -> None: ...

    @abstractmethod
    def open_module(self, module: Module) -> None: ...

    @abstractmethod
    def fill_disc_question(self, answer: DiscAnswer) -> None: ...

    def fill_disc_answers(self, answers: list[DiscAnswer]) -> None:
        for answer in answers:
            self.fill_disc_question(answer)

    @abstractmethod
    def fill_choice_question(self, module: Module, answer: ChoiceAnswer) -> None: ...

    def fill_choice_answers(self, module: Module, answers: list[ChoiceAnswer]) -> None:
        for answer in answers:
            self.fill_choice_question(module, answer)

    @abstractmethod
    def submit(self, module: Module) -> None: ...

    @abstractmethod
    def verify_submission(self, module: Module) -> bool: ...

    @abstractmethod
    def recover_from_error(self) -> bool: ...

    def close_after_success(self) -> None:
        """Close UI applications after a fully successful job when configured."""
