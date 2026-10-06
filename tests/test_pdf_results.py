import tempfile
import unittest
from datetime import date
from pathlib import Path

from frexor_automation.config import PdfConfig
from frexor_automation.domain import Module, Participant
from frexor_automation.errors import PdfAssociationError, PdfInvalidError
from frexor_automation.pdf_results import PdfResultManager


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


if __name__ == "__main__":
    unittest.main()
