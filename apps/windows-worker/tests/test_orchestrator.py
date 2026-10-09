import logging
from datetime import date
from pathlib import Path
import unittest

from frexor_automation.domain import ChoiceAnswer, DiscAnswer, Module, Participant, Status
from frexor_automation.frexor.mock import MockFrexorAdapter
from frexor_automation.errors import PdfMergeError
from frexor_automation.orchestrator import Orchestrator
from frexor_automation.repositories import InMemoryRepository
from frexor_automation.pdf_results import MockPdfResultManager


def all_answers(participant_id: str):
    return {
        (participant_id, Module.DISC): [DiscAnswer(n, "A", "B") for n in range(1, 25)],
        (participant_id, Module.VAK): [ChoiceAnswer(n, "A") for n in range(1, 31)],
        (participant_id, Module.IQ): [ChoiceAnswer(n, "A") for n in range(1, 61)],
    }


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("test")
        self.logger.addHandler(logging.NullHandler())

    def test_resume_does_not_repeat_done_module(self):
        participant = Participant(
            "P001", "Andi", "Operator", Status.PARTIAL,
            {Module.DISC: Status.DONE, Module.VAK: Status.ERROR, Module.IQ: Status.READY},
            test_date=date.today(),
        )
        repository = InMemoryRepository([participant], all_answers("P001"))
        adapter = MockFrexorAdapter()
        Orchestrator(repository, adapter, MockPdfResultManager(), self.logger).run_batch(retry_errors=True)

        stored = repository.participants["P001"]
        self.assertEqual(stored.overall_status, Status.DONE)
        self.assertEqual(stored.pdf_status, "VERIFIED")
        self.assertNotIn("open:DISC", adapter.actions)
        self.assertIn("open:VAK", adapter.actions)
        self.assertIn("open:IQ", adapter.actions)

    def test_pdf_verification_can_confirm_submit_when_pdf_viewer_hides_frexor(self):
        participant = Participant("P001", "Andi", "Operator", test_date=date.today())
        repository = InMemoryRepository([participant], all_answers("P001"))
        adapter = MockFrexorAdapter(verify=False)
        Orchestrator(repository, adapter, MockPdfResultManager(), self.logger).run_batch()

        stored = repository.participants["P001"]
        self.assertEqual(stored.overall_status, Status.DONE)
        self.assertEqual(stored.pdf_status, "VERIFIED")
        self.assertEqual(adapter.actions.count("verify:DISC"), 2)

    def test_full_run_merges_once_and_stores_merged_path(self):
        participant = Participant("P001", "Andi", "Operator", test_date=date.today())
        repository = InMemoryRepository([participant], all_answers("P001"))
        adapter = MockFrexorAdapter()
        pdf_manager = MockPdfResultManager()

        Orchestrator(repository, adapter, pdf_manager, self.logger).run_batch()

        stored = repository.participants["P001"]
        self.assertEqual(pdf_manager.actions.count("merge:P001"), 1)
        self.assertEqual(
            len([action for action in pdf_manager.actions if action.startswith("prepare:P001:")]),
            3,
        )
        self.assertEqual(adapter.actions.count("close_after_success"), 1)
        self.assertEqual(
            stored.pdf_path,
            f"/mock/P001/Hasil Psikotes {date.today().strftime('%d-%m-%Y')} Operator Andi.pdf",
        )

    def test_merge_failure_marks_final_module_error(self):
        class FailingMergeManager(MockPdfResultManager):
            def merge_results(self, participant):
                self.actions.append(f"merge:{participant.participant_id}")
                raise PdfMergeError("merge failed")

        participant = Participant("P001", "Andi", "Operator", test_date=date.today())
        repository = InMemoryRepository([participant], all_answers("P001"))
        adapter = MockFrexorAdapter()

        Orchestrator(repository, adapter, FailingMergeManager(), self.logger).run_batch()

        stored = repository.participants["P001"]
        self.assertEqual(stored.module_statuses[Module.IQ], Status.ERROR)
        self.assertEqual(stored.error_code, "PDF_MERGE_FAILED")
        self.assertEqual(stored.pdf_status, "ERROR")
        self.assertNotIn("close_after_success", adapter.actions)

    def test_retry_merge_uses_archived_iq_without_resubmitting(self):
        class ArchivedIqManager(MockPdfResultManager):
            def existing_result(self, participant, module):
                self.actions.append(f"existing:{participant.participant_id}:{module}")
                if module is Module.IQ:
                    return Path(f"/archive/{participant.participant_id}/IQ.pdf")
                return None

        participant = Participant(
            "P001", "Andi", "Operator", Status.PARTIAL,
            {Module.DISC: Status.DONE, Module.VAK: Status.DONE, Module.IQ: Status.ERROR},
            error_code="PDF_MERGE_FAILED", pdf_status="ERROR", test_date=date.today(),
        )
        repository = InMemoryRepository([participant], all_answers("P001"))
        adapter = MockFrexorAdapter()
        pdf_manager = ArchivedIqManager()

        Orchestrator(repository, adapter, pdf_manager, self.logger).run_batch(retry_errors=True)

        stored = repository.participants["P001"]
        self.assertEqual(stored.overall_status, Status.DONE)
        self.assertEqual(
            stored.pdf_path,
            f"/mock/P001/Hasil Psikotes {date.today().strftime('%d-%m-%Y')} Operator Andi.pdf",
        )
        self.assertNotIn("open:IQ", adapter.actions)
        self.assertNotIn("submit:IQ", adapter.actions)
        self.assertEqual(pdf_manager.actions.count("merge:P001"), 1)

    def test_retry_merge_failure_does_not_resubmit_archived_iq(self):
        class FailingArchivedIqManager(MockPdfResultManager):
            def existing_result(self, participant, module):
                if module is Module.IQ:
                    return Path(f"/archive/{participant.participant_id}/IQ.pdf")
                return None

            def merge_results(self, participant):
                raise PdfMergeError("merge still failed")

        participant = Participant(
            "P001", "Andi", "Operator", Status.PARTIAL,
            {Module.DISC: Status.DONE, Module.VAK: Status.DONE, Module.IQ: Status.ERROR},
            error_code="PDF_MERGE_FAILED", pdf_status="ERROR", test_date=date.today(),
        )
        repository = InMemoryRepository([participant], all_answers("P001"))
        adapter = MockFrexorAdapter()

        Orchestrator(
            repository, adapter, FailingArchivedIqManager(), self.logger
        ).run_batch(retry_errors=True)

        stored = repository.participants["P001"]
        self.assertEqual(stored.module_statuses[Module.IQ], Status.ERROR)
        self.assertEqual(stored.error_code, "PDF_MERGE_FAILED")
        self.assertNotIn("open:IQ", adapter.actions)
        self.assertNotIn("submit:IQ", adapter.actions)

    def test_validation_does_not_open_frexor(self):
        participant = Participant("P001", "Andi", "Operator", test_date=date.today())
        repository = InMemoryRepository([participant], all_answers("P001"))
        adapter = MockFrexorAdapter()
        results = Orchestrator(repository, adapter, MockPdfResultManager(), self.logger).validate_batch()

        self.assertTrue(results[0].valid)
        self.assertEqual(adapter.actions, [])

    def test_interrupted_processing_is_not_automatically_repeated(self):
        participant = Participant(
            "P001", "Andi", "Operator", Status.PROCESSING,
            {Module.DISC: Status.PROCESSING, Module.VAK: Status.READY, Module.IQ: Status.READY},
            test_date=date.today(),
        )
        repository = InMemoryRepository([participant], all_answers("P001"))
        adapter = MockFrexorAdapter()
        Orchestrator(repository, adapter, MockPdfResultManager(), self.logger).run_batch()

        stored = repository.participants["P001"]
        self.assertEqual(stored.module_statuses[Module.DISC], Status.ERROR)
        self.assertEqual(stored.error_code, "INTERRUPTED_REVIEW_REQUIRED")
        self.assertNotIn("open:DISC", adapter.actions)

    def test_interrupted_processing_recovers_from_archived_pdf(self):
        class ExistingPdfManager(MockPdfResultManager):
            def existing_result(self, participant, module):
                return Path(f"/archive/{participant.participant_id}/{module.value}.pdf")

        participant = Participant(
            "P001", "Andi", "Operator", Status.PROCESSING,
            {Module.DISC: Status.PROCESSING, Module.VAK: Status.DONE, Module.IQ: Status.DONE},
            test_date=date.today(),
        )
        repository = InMemoryRepository([participant], all_answers("P001"))
        adapter = MockFrexorAdapter()
        summary = Orchestrator(repository, adapter, ExistingPdfManager(), self.logger).run_batch()

        stored = repository.participants["P001"]
        self.assertEqual(stored.overall_status, Status.DONE)
        self.assertEqual(stored.pdf_status, "VERIFIED")
        self.assertEqual(summary.success, 1)
        self.assertNotIn("open:DISC", adapter.actions)

    def test_done_participant_is_counted_as_skipped_without_opening_frexor(self):
        participant = Participant(
            "P001", "Andi", "Operator", Status.DONE,
            {Module.DISC: Status.DONE, Module.VAK: Status.DONE, Module.IQ: Status.DONE},
            pdf_status="VERIFIED", test_date=date.today(),
        )
        repository = InMemoryRepository([participant], all_answers("P001"))
        adapter = MockFrexorAdapter()
        pdf_manager = MockPdfResultManager()
        summary = Orchestrator(repository, adapter, pdf_manager, self.logger).run_batch()

        self.assertEqual(summary.total, 1)
        self.assertEqual(summary.skipped, 1)
        self.assertEqual(adapter.actions, [])
        self.assertEqual(pdf_manager.actions, [])

    def test_error_module_requires_explicit_retry(self):
        participant = Participant(
            "P001", "Andi", "Operator", Status.PARTIAL,
            {Module.DISC: Status.DONE, Module.VAK: Status.ERROR, Module.IQ: Status.READY},
            test_date=date.today(),
        )
        repository = InMemoryRepository([participant], all_answers("P001"))
        adapter = MockFrexorAdapter()
        summary = Orchestrator(repository, adapter, MockPdfResultManager(), self.logger).run_batch()

        self.assertEqual(summary.skipped, 1)
        self.assertEqual(adapter.actions, [])


if __name__ == "__main__":
    unittest.main()
