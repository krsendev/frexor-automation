from __future__ import annotations

from collections import Counter

from .domain import ChoiceAnswer, DiscAnswer, Module, Participant


QUESTION_COUNTS = {Module.DISC: 24, Module.VAK: 30, Module.IQ: 60}
DISC_OPTIONS = set("ABCD")
VAK_OPTIONS = set("ABC")


def iq_options(question_no: int) -> set[str]:
    if question_no in {12, 24, 44, 56}:
        return set("ABC")
    if question_no in {15, 54}:
        return set("ABCDEFGH")
    return set("ABCDE")


def validate_participant(participant: Participant) -> list[str]:
    errors = []
    if not participant.participant_id.strip():
        errors.append("participant_id is required")
    if not participant.name.strip():
        errors.append("name is required")
    if not participant.position.strip():
        errors.append("position is required")
    if participant.test_date is None:
        errors.append("test_date is required")
    return errors


def _validate_numbers(numbers: list[int], module: Module) -> list[str]:
    expected = set(range(1, QUESTION_COUNTS[module] + 1))
    actual = set(numbers)
    errors = []
    duplicates = sorted(number for number, count in Counter(numbers).items() if count > 1)
    if duplicates:
        errors.append(f"{module} duplicate questions: {duplicates}")
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        errors.append(f"{module} missing questions: {missing}")
    if extra:
        errors.append(f"{module} unexpected questions: {extra}")
    return errors


def validate_disc(answers: list[DiscAnswer]) -> list[str]:
    errors = _validate_numbers([a.question_no for a in answers], Module.DISC)
    for answer in answers:
        if answer.mirip not in DISC_OPTIONS:
            errors.append(f"DISC Q{answer.question_no} invalid mirip: {answer.mirip!r}")
        if answer.tidak_mirip not in DISC_OPTIONS:
            errors.append(f"DISC Q{answer.question_no} invalid tidak_mirip: {answer.tidak_mirip!r}")
        if answer.mirip == answer.tidak_mirip:
            errors.append(f"DISC Q{answer.question_no} mirip and tidak_mirip must differ")
    return errors


def validate_choices(module: Module, answers: list[ChoiceAnswer]) -> list[str]:
    errors = _validate_numbers([a.question_no for a in answers], module)
    for answer in answers:
        allowed = VAK_OPTIONS if module is Module.VAK else iq_options(answer.question_no)
        if answer.answer not in allowed:
            errors.append(f"{module} Q{answer.question_no} invalid answer: {answer.answer!r}")
    return errors


def validate_module(module: Module, answers: list[DiscAnswer] | list[ChoiceAnswer]) -> list[str]:
    if module is Module.DISC:
        return validate_disc(answers)  # type: ignore[arg-type]
    return validate_choices(module, answers)  # type: ignore[arg-type]
