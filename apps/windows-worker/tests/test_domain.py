import unittest

from frexor_automation.domain import Module, Status, calculate_overall_status, frexor_identity


class DomainTests(unittest.TestCase):
    def test_partial_when_one_module_done(self):
        statuses = {Module.DISC: Status.DONE, Module.VAK: Status.ERROR, Module.IQ: Status.READY}
        self.assertEqual(calculate_overall_status(statuses), Status.PARTIAL)

    def test_done_accepts_skipped_modules(self):
        statuses = {Module.DISC: Status.DONE, Module.VAK: Status.SKIPPED, Module.IQ: Status.DONE}
        self.assertEqual(calculate_overall_status(statuses), Status.DONE)

    def test_frexor_identity_is_trimmed_to_twenty_characters(self):
        self.assertEqual(frexor_identity(" 12345678901234567890EXTRA "), "12345678901234567890")


if __name__ == "__main__":
    unittest.main()
