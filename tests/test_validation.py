import unittest

from frexor_automation.domain import ChoiceAnswer, DiscAnswer, Module
from frexor_automation.validation import validate_choices, validate_disc


class ValidationTests(unittest.TestCase):
    def test_complete_disc_is_valid(self):
        answers = [DiscAnswer(number, "A", "B") for number in range(1, 25)]
        self.assertEqual(validate_disc(answers), [])

    def test_disc_rejects_same_and_missing_answers(self):
        answers = [DiscAnswer(number, "A", "B") for number in range(1, 24)]
        answers[0] = DiscAnswer(1, "A", "A")
        errors = validate_disc(answers)
        self.assertTrue(any("missing questions: [24]" in error for error in errors))
        self.assertTrue(any("must differ" in error for error in errors))

    def test_iq_uses_question_specific_options(self):
        answers = [ChoiceAnswer(number, "A") for number in range(1, 61)]
        answers[11] = ChoiceAnswer(12, "D")
        errors = validate_choices(Module.IQ, answers)
        self.assertEqual(errors, ["IQ Q12 invalid answer: 'D'"])

    def test_vak_requires_thirty_unique_answers(self):
        answers = [ChoiceAnswer(number, "A") for number in range(1, 30)]
        errors = validate_choices(Module.VAK, answers)
        self.assertEqual(errors, ["VAK missing questions: [30]"])


if __name__ == "__main__":
    unittest.main()

