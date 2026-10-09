import tempfile
import unittest
from datetime import date
from pathlib import Path

from frexor_automation.config import PdfConfig
from frexor_automation.domain import Module, Participant
from frexor_automation.errors import PdfAssociationError, PdfInvalidError, PdfMergeError
from frexor_automation.pdf_results import PdfResultManager
from pypdf import PdfReader, PdfWriter


VALID_PDF = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


class PdfResultTests(unittest.TestCase):
    def manager(self, root: Path) -> PdfResultManager:
        watch = root / "watch"
        watch.mkdir()
        for module in Module:
            (watch / module.value).mkdir()
        return PdfResultManager(PdfConfig(
            watch, {"DISC": "DISC", "VAK": "VAK", "IQ": "IQ"},
            root / "output", 1, 0.01, 0, 10,
        ))

    @staticmethod
    def write_pdf(path: Path, widths: list[float]) -> None:
        writer = PdfWriter()
        for width in widths:
            writer.add_blank_page(width=width, height=100)
        with path.open("wb") as handle:
            writer.write(handle)
        writer.close()

    def write_merge_sources(
        self, manager: PdfResultManager, participant: Participant
    ) -> list[Path]:
        sources = []
        for module, width in zip(Module, (100, 200, 300)):
            path = manager._destination(participant, module)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.write_pdf(path, [width])
            sources.append(path)
        return sources

    def test_archives_pdf_by_participant_and_module(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = self.manager(root)
            manager.check_environment()
            before = manager.snapshot(Module.IQ)
            filename = f"Hasil IQ {date.today().isoformat()} Ops Andi Test.pdf"
            (root / "watch" / "IQ" / filename).write_bytes(VALID_PDF)

            participant = Participant("P001", "Andi Test", "Ops", test_date=date.today())
            result = manager.wait_for_result(before, participant, Module.IQ)

            self.assertEqual(result.name, "IQ.pdf")
            self.assertEqual(result.parent.name, "P001_Andi_Test")
            self.assertEqual(result.read_bytes(), VALID_PDF)
            self.assertEqual(manager.existing_result(participant, Module.IQ), result)

    def test_rejects_invalid_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = self.manager(root)
            invalid = root / "watch" / "DISC" / "result.pdf"
            invalid.write_bytes(b"not a pdf document")
            with self.assertRaises(PdfInvalidError):
                manager._validate(invalid)

    def test_does_not_overwrite_existing_result(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = self.manager(root)
            source = root / "watch" / "DISC" / "result.pdf"
            source.write_bytes(VALID_PDF)
            participant = Participant("P001", "Andi", "Ops", test_date=date.today())
            manager._archive(source, participant, Module.DISC)
            with self.assertRaises(PdfAssociationError):
                manager._archive(source, participant, Module.DISC)

    def test_rejects_pdf_filename_for_another_participant(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = self.manager(root)
            path = root / "watch" / "VAK" / f"Hasil VAK {date.today().isoformat()} Ops Orang Lain.pdf"
            path.write_bytes(VALID_PDF)
            with self.assertRaises(PdfAssociationError):
                manager._validate_association(
                    path, Participant("P001", "Andi", "Ops", test_date=date.today()), Module.VAK
                )

    def test_pdf_filename_uses_frexor_identity_character_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = self.manager(root)
            participant = Participant(
                "P001", "Nama Peserta Sangat Panjang", "Posisi Peserta Sangat Panjang",
                test_date=date.today(),
            )
            path = root / "watch" / "DISC" / (
                f"Hasil DISC {date.today().isoformat()} "
                "Posisi Peserta Sanga Nama Peserta Sangat.pdf"
            )
            path.write_bytes(VALID_PDF)

            manager._validate_association(path, participant, Module.DISC)

    def test_moves_existing_same_name_source_before_submission(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manager = self.manager(root)
            participant = Participant("P002", "Andi", "Ops", test_date=date.today())
            source = manager._expected_source(participant, Module.DISC)
            source.write_bytes(VALID_PDF)

            archived = manager.prepare_for_submission(participant, Module.DISC)

            self.assertIsNotNone(archived)
            self.assertFalse(source.exists())
            self.assertTrue(archived.exists())
            self.assertEqual(archived.read_bytes(), VALID_PDF)
            self.assertIn("_source_collisions", archived.parts)

    def test_merges_results_in_disc_vak_iq_order_and_preserves_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = self.manager(Path(directory))
            participant = Participant("P001", "Andi", "Ops", test_date=date.today())
            sources = self.write_merge_sources(manager, participant)

            result = manager.merge_results(participant)

            self.assertEqual(
                result.name,
                f"Hasil Psikotes {date.today().strftime('%d-%m-%Y')} Ops Andi.pdf",
            )
            pages = PdfReader(result).pages
            self.assertEqual(len(pages), 3)
            self.assertEqual([float(page.mediabox.width) for page in pages], [100, 200, 300])
            self.assertTrue(all(source.exists() for source in sources))

    def test_merge_requires_all_module_results(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = self.manager(Path(directory))
            participant = Participant("P001", "Andi", "Ops", test_date=date.today())
            path = manager._destination(participant, Module.DISC)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.write_pdf(path, [100])

            with self.assertRaises(PdfMergeError):
                manager.merge_results(participant)

    def test_existing_valid_merge_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = self.manager(Path(directory))
            participant = Participant("P001", "Andi", "Ops", test_date=date.today())
            self.write_merge_sources(manager, participant)
            first = manager.merge_results(participant)
            original = first.read_bytes()

            second = manager.merge_results(participant)

            self.assertEqual(second, first)
            self.assertEqual(second.read_bytes(), original)

    def test_corrupt_source_fails_without_creating_merged_result(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = self.manager(Path(directory))
            participant = Participant("P001", "Andi", "Ops", test_date=date.today())
            self.write_merge_sources(manager, participant)
            manager._destination(participant, Module.VAK).write_bytes(b"not a pdf")

            with self.assertRaises(PdfMergeError):
                manager.merge_results(participant)

            self.assertFalse(manager._merged_destination(participant).exists())


if __name__ == "__main__":
    unittest.main()
