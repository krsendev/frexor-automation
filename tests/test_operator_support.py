import tempfile
import unittest
from pathlib import Path

from frexor_automation.config import load_config
from frexor_automation.config_writer import write_config
from frexor_automation.errors import ConfigurationError
from frexor_automation.operator_messages import friendly_error
from frexor_automation.repositories import GoogleSheetsRepository, PARTICIPANT_HEADERS
from frexor_automation.state_store import RunState, RunStateStore


class OperatorSupportTests(unittest.TestCase):
    def test_first_run_configuration_is_loadable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / "config.toml"
            write_config(
                config_path, "C:/Frexor/Frexor.exe", "sheet-id", "C:/secret.json",
                "C:/Frexor/Results", "C:/Assessment Results",
            )
            config = load_config(config_path)
            self.assertEqual(config.sheets.spreadsheet_id, "sheet-id")
            self.assertTrue((root / "frexor_ui_map.toml").exists())

    def test_run_state_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            store = RunStateStore(Path(directory) / "state.json")
            store.save(RunState(lifecycle="RUNNING", current_participant_id="P023", success=22))
            restored = store.load()
            self.assertEqual(restored.lifecycle, "RUNNING")
            self.assertEqual(restored.current_participant_id, "P023")
            self.assertEqual(restored.success, 22)

    def test_operator_error_hides_raw_exception_as_primary_message(self):
        message = friendly_error("PDF_TIMEOUT", "TimeoutError: selector failed")
        self.assertEqual(message.title, "Hasil PDF belum ditemukan")
        self.assertNotIn("TimeoutError", message.description)

    def test_google_sheet_write_layout_requires_exact_participant_headers(self):
        GoogleSheetsRepository._require_headers(
            [PARTICIPANT_HEADERS], PARTICIPANT_HEADERS, "Participants"
        )
        with self.assertRaises(ConfigurationError):
            GoogleSheetsRepository._require_headers(
                [["participant_id", "question_no", "mirip", "tidak_mirip"]],
                PARTICIPANT_HEADERS,
                "Participants",
            )


if __name__ == "__main__":
    unittest.main()
