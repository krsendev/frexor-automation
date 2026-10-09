from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
from threading import Event
from typing import Callable

from .domain import ChoiceAnswer, DiscAnswer, Module, Participant, Status, calculate_overall_status
from .frexor.base import FrexorAdapter
from .repositories import AssessmentRepository
from .pdf_results import Snapshot
from .validation import validate_module, validate_participant


ProgressCallback = Callable[[str, Module | None, int, int], None]
BatchProgressCallback = Callable[["BatchSummary", str], None]


@dataclass(frozen=True)
class ValidationResult:
    participant_id: str
    valid: bool
    errors: list[str]


@dataclass
class BatchSummary:
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    failed_participants: list[tuple[str, str, str]] = field(default_factory=list)


class Orchestrator:
    def __init__(
        self,
        repository: AssessmentRepository,
        adapter: FrexorAdapter,
        pdf_manager,
        logger: logging.Logger,
        progress: ProgressCallback | None = None,
        continue_after_participant_error: bool = False,
        batch_progress: BatchProgressCallback | None = None,
    ):
        self.repository = repository
        self.adapter = adapter
        self.pdf_manager = pdf_manager
        self.logger = logger
        self.progress = progress or (lambda *_: None)
        self.continue_after_participant_error = continue_after_participant_error
        self.batch_progress = batch_progress or (lambda *_: None)
        self.stop_requested = Event()

    def request_stop(self) -> None:
        self.stop_requested.set()

    def validate_batch(self, retry_errors: bool = False) -> list[ValidationResult]:
        results = []
        for participant in self.repository.list_participants(include_errors=retry_errors):
            errors = validate_participant(participant)
            interrupted = [m.value for m, status in participant.module_statuses.items() if status is Status.PROCESSING]
            if interrupted:
                errors.append(f"Interrupted PROCESSING state requires operator review: {interrupted}")
            for module in participant.pending_modules(retry_errors=retry_errors):
                answers = self.repository.get_answers(participant.participant_id, module)
                errors.extend(validate_module(module, answers))
            results.append(ValidationResult(participant.participant_id, not errors, errors))
        return results

    def run_batch(self, retry_errors: bool = False) -> BatchSummary:
        self.stop_requested.clear()
        loaded = self.repository.list_participants(include_errors=retry_errors, include_done=True)
        participants = [
            p for p in loaded
            if p.overall_status is not Status.DONE
            and (retry_errors or Status.ERROR not in p.module_statuses.values())
        ]
        skipped = len(loaded) - len(participants)
        summary = BatchSummary(total=len(loaded), skipped=skipped)
        if not participants:
            self.batch_progress(summary, "")
            return summary
        self.adapter.check_environment()
        self.pdf_manager.check_environment()
        self.adapter.launch_or_connect()
        for index, participant in enumerate(participants, start=1):
            if self.stop_requested.is_set():
                self.logger.info("SAFE_STOP before participant=%s", participant.participant_id)
                break
            self.batch_progress(summary, participant.participant_id)
            self._process_participant(participant, retry_errors)
            if participant.overall_status is Status.DONE and participant.pdf_status == "VERIFIED":
                summary.success += 1
            elif Status.ERROR in participant.module_statuses.values():
                summary.failed += 1
                summary.failed_participants.append(
                    (participant.participant_id, participant.error_code, participant.last_error)
                )
            self.batch_progress(summary, participant.participant_id)
            if not self.continue_after_participant_error and Status.ERROR in participant.module_statuses.values():
                self.logger.warning("Batch stopped after participant error: %s", participant.participant_id)
                break
        self.batch_progress(summary, "")
        if summary.success > 0 and summary.failed == 0 and not self.stop_requested.is_set():
            try:
                self.adapter.close_after_success()
                self.logger.info("APPLICATION_CLEANUP completed after successful batch")
            except Exception as exc:
                self.logger.warning("APPLICATION_CLEANUP failed: %s", exc)
        return summary

    def _persist(
        self, participant: Participant, module: Module, status: Status,
        error_code: str = "", error_message: str = "",
    ) -> None:
        participant.module_statuses[module] = status
        participant.overall_status = calculate_overall_status(participant.module_statuses)
        participant.last_error = error_message
        participant.error_code = error_code
        self.repository.update_module_status(participant, module, status, error_code, error_message)

    def _process_participant(self, participant: Participant, retry_errors: bool) -> None:
        interrupted = [m for m, status in participant.module_statuses.items() if status is Status.PROCESSING]
        if interrupted:
            module = interrupted[0]
            existing = self.pdf_manager.existing_result(participant, module)
            if existing is None:
                self._set_error(
                    participant,
                    module,
                    "INTERRUPTED_REVIEW_REQUIRED",
                    ["Previous run stopped during PROCESSING and no archived PDF was found"],
                )
                return
            participant.pdf_path = str(Path(existing).parent)
            next_statuses = dict(participant.module_statuses)
            next_statuses[module] = Status.DONE
            try:
                if set(next_statuses.values()) <= {Status.DONE, Status.SKIPPED}:
                    merged = self.pdf_manager.merge_results(participant)
                    participant.pdf_path = str(merged)
                    participant.pdf_status = "VERIFIED"
                else:
                    participant.pdf_status = "PARTIAL"
            except Exception as exc:
                code = getattr(exc, "code", "PDF_MERGE_FAILED")
                self._set_error(participant, module, code, [str(exc)])
                return
            self._persist(participant, module, Status.DONE)
            self.logger.info(
                "%s %s recovered from archived PDF path=%s",
                participant.participant_id, module, existing,
            )
        if retry_errors:
            if not self._recover_error_modules_with_archived_pdf(participant):
                return
        participant_errors = validate_participant(participant)
        if participant_errors:
            self._mark_first_pending_error(participant, retry_errors, "PARTICIPANT_INVALID", participant_errors)
            return
        modules = participant.pending_modules(retry_errors=retry_errors)
        if not modules:
            return
        self.logger.info("%s START participant", participant.participant_id)
        try:
            self.adapter.open_participant(participant)
        except Exception as exc:
            self._mark_first_pending_error(participant, retry_errors, "PARTICIPANT_OPEN_FAILED", [str(exc)])
            return

        for module in modules:
            if self.stop_requested.is_set():
                self.logger.info("%s SAFE_STOP before module=%s", participant.participant_id, module)
                return
            answers = self.repository.get_answers(participant.participant_id, module)
            errors = validate_module(module, answers)
            if errors:
                self._set_error(participant, module, "DATA_INVALID", errors)
                return
            try:
                self._process_module(participant, module, answers)
            except Exception as exc:
                code = getattr(exc, "code", "MODULE_FAILED")
                self._set_error(participant, module, code, [str(exc)])
                recovered = self.adapter.recover_from_error()
                self.logger.warning(
                    "%s %s recovery=%s", participant.participant_id, module, recovered
                )
                return

    def _recover_error_modules_with_archived_pdf(self, participant: Participant) -> bool:
        for module in Module:
            if participant.module_statuses[module] is not Status.ERROR:
                continue
            existing = self.pdf_manager.existing_result(participant, module)
            if existing is None:
                continue
            self._persist(participant, module, Status.PROCESSING)
            participant.pdf_path = str(Path(existing).parent)
            next_statuses = dict(participant.module_statuses)
            next_statuses[module] = Status.DONE
            try:
                if set(next_statuses.values()) <= {Status.DONE, Status.SKIPPED}:
                    merged = self.pdf_manager.merge_results(participant)
                    participant.pdf_path = str(merged)
                    participant.pdf_status = "VERIFIED"
                    self.logger.info(
                        "%s merged PDF recovered path=%s",
                        participant.participant_id,
                        merged,
                    )
                else:
                    participant.pdf_status = "PARTIAL"
            except Exception as exc:
                code = getattr(exc, "code", "PDF_MERGE_FAILED")
                self._set_error(participant, module, code, [str(exc)])
                return False
            self._persist(participant, module, Status.DONE)
            self.logger.info(
                "%s %s recovered from archived PDF path=%s",
                participant.participant_id,
                module,
                existing,
            )
        return True

    def _process_module(
        self, participant: Participant, module: Module,
        answers: list[DiscAnswer] | list[ChoiceAnswer],
    ) -> None:
        participant.attempt_count += 1
        self._persist(participant, module, Status.PROCESSING)
        self.logger.info("%s %s PROCESSING", participant.participant_id, module)
        self.adapter.open_module(module)
        total = len(answers)
        ordered_answers = sorted(answers, key=lambda a: a.question_no)
        if module is Module.DISC:
            for index, answer in enumerate(ordered_answers, start=1):
                self.adapter.fill_disc_question(answer)  # type: ignore[arg-type]
                self.progress(participant.participant_id, module, index, total)
                self.logger.info(
                    "%s %s input question=%s", participant.participant_id, module, answer.question_no
                )
        else:
            self.adapter.fill_choice_answers(module, ordered_answers)  # type: ignore[arg-type]
            for index, answer in enumerate(ordered_answers, start=1):
                self.progress(participant.participant_id, module, index, total)
                self.logger.info(
                    "%s %s input question=%s", participant.participant_id, module, answer.question_no
                )
        pdf_before: Snapshot = self.pdf_manager.snapshot(module)
        self.adapter.submit(module)
        self.logger.info("%s %s submit clicked", participant.participant_id, module)
        ui_verified = self.adapter.verify_submission(module)
        if ui_verified:
            self.logger.info("%s %s submit UI transition verified", participant.participant_id, module)
        else:
            self.logger.warning(
                "%s %s submit UI transition not observed; waiting for the generated PDF",
                participant.participant_id, module,
            )
        result = self.pdf_manager.wait_for_result(pdf_before, participant, module)
        self.logger.info("%s %s PDF verified path=%s", participant.participant_id, module, result)
        if not ui_verified:
            ui_verified = self.adapter.verify_submission(module)
            if ui_verified:
                self.logger.info(
                    "%s %s delayed submit dialog verified after PDF creation",
                    participant.participant_id,
                    module,
                )
            else:
                self.logger.warning(
                    "%s %s submit dialog was not observed after PDF verification",
                    participant.participant_id,
                    module,
                )
        next_statuses = dict(participant.module_statuses)
        next_statuses[module] = Status.DONE
        if set(next_statuses.values()) <= {Status.DONE, Status.SKIPPED}:
            merged = self.pdf_manager.merge_results(participant)
            participant.pdf_path = str(merged)
            participant.pdf_status = "VERIFIED"
            self.logger.info(
                "%s merged PDF verified path=%s",
                participant.participant_id,
                merged,
            )
        else:
            participant.pdf_path = str(Path(result).parent)
            participant.pdf_status = "PARTIAL"
        self._persist(participant, module, Status.DONE)
        self.logger.info("%s %s DONE", participant.participant_id, module)

    def _set_error(self, participant: Participant, module: Module, code: str, errors: list[str]) -> None:
        message = "; ".join(errors)
        if code.startswith("PDF_"):
            participant.pdf_status = "ERROR"
        self._persist(participant, module, Status.ERROR, code, message)
        self.logger.error("%s %s %s %s", participant.participant_id, module, code, message)

    def _mark_first_pending_error(
        self, participant: Participant, retry_errors: bool, code: str, errors: list[str]
    ) -> None:
        modules = participant.pending_modules(retry_errors=retry_errors)
        if modules:
            self._set_error(participant, modules[0], code, errors)
