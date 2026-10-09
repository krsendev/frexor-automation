import unittest
from types import SimpleNamespace

from frexor_automation.domain import ChoiceAnswer, DiscAnswer, Module
from frexor_automation.errors import UnsafeUiStateError
from frexor_automation.frexor.windows import WindowsFrexorAdapter


class FakeEdit:
    def __init__(self):
        self.value = ""

    def set_edit_text(self, value):
        self.value = value

    def get_value(self):
        return self.value

    def is_visible(self):
        return True


class FakeKeyboardOnlyEdit(FakeEdit):
    def set_edit_text(self, value):
        raise OSError("UIA ValuePattern failed")

    def click_input(self):
        pass

    def type_keys(self, keys, **_kwargs):
        if keys == "^a{BACKSPACE}":
            self.value = ""
        else:
            self.value += keys


class FakeAutoAdvanceEdit(FakeEdit):
    def __init__(self, controls, index):
        super().__init__()
        self.controls = controls
        self.index = index

    def click_input(self):
        pass

    def type_keys(self, keys, **_kwargs):
        for offset, key in enumerate(keys):
            self.controls[self.index + offset].value = key


class FakeEditWindow:
    def __init__(self, count):
        self.edits = []
        self.edits.extend(FakeAutoAdvanceEdit(self.edits, index) for index in range(count))

    def descendants(self, control_type):
        return self.edits if control_type == "Edit" else []


class FakeRefreshingWindow:
    def __init__(self):
        self.value = ""
        self.calls = 0

    def descendants(self, control_type):
        if control_type != "Edit":
            return []
        self.calls += 1
        owner = self

        class RefreshingEdit(FakeEdit):
            def set_edit_text(self, value):
                owner.value = value

            def get_value(self):
                return "" if owner.calls == 1 else owner.value

        return [RefreshingEdit()]


class FakeExistingValueWindow:
    def __init__(self, value):
        self.edit = FakeEdit()
        self.edit.value = value
        self.write_attempts = 0
        original_set = self.edit.set_edit_text

        def track_write(value):
            self.write_attempts += 1
            original_set(value)

        self.edit.set_edit_text = track_write

    def descendants(self, control_type):
        return [self.edit] if control_type == "Edit" else []


class FakeWindowTextEdit(FakeEdit):
    def __init__(self, value):
        super().__init__()
        self.visible_value = value
        self.write_attempts = 0

    def set_edit_text(self, value):
        self.write_attempts += 1
        self.visible_value = value

    def get_value(self):
        return ""

    def window_text(self):
        return self.visible_value


class FakeControl:
    def __init__(self, text, value=None, callback=None):
        self.text = text
        self.value = text if value is None else value
        self.callback = callback
        self.clicked = False

    def is_visible(self):
        return True

    def window_text(self):
        return self.text

    def click_input(self, **_kwargs):
        self.clicked = True
        if self.callback:
            self.callback()

    def get_value(self):
        return self.value

    def rectangle(self):
        return SimpleNamespace(width=lambda: 300)


class FakeDialog(FakeControl):
    def __init__(self):
        super().__init__("Perhatian")
        self.message = FakeControl("Hasil Tes sudah disimpan di C:\\Users\\User\\Documents\\Frexor PAS\\DISC\\")
        self.ok = FakeControl("OK")

    def descendants(self, control_type):
        return [self.message] if control_type == "Text" else [self.ok]


class FakeDiscWarning(FakeControl):
    def __init__(self):
        super().__init__("Perhatian")
        self.message = FakeControl(
            "Masukkan jawaban yang berbeda untuk Mirip dan tidak mirip"
        )
        self.ok = FakeControl("OK")

    def descendants(self, control_type):
        return [self.message] if control_type == "Text" else [self.ok]


class FakeApplication:
    def __init__(self, dialog):
        self.dialog = dialog

    def windows(self):
        return [self.dialog]


class FakeMainWindow:
    def __init__(self, dialog):
        self.dialog = dialog

    def descendants(self, control_type):
        return [self.dialog] if control_type == "Window" else []


class FakeLoginWindow:
    def __init__(self, values):
        self.logged_in = False
        self.minimized = True
        self.focused = False
        self.login = FakeControl("LOG IN", callback=self._complete_login)
        self.navigation = FakeControl("Attitude Test [DISC]")
        self.edits = [FakeControl("", value=value) for value in values]

    def _complete_login(self):
        self.logged_in = True

    def is_minimized(self):
        return self.minimized

    def restore(self):
        self.minimized = False

    def set_focus(self):
        self.focused = True

    def descendants(self, control_type):
        if control_type == "Edit":
            return self.edits
        if control_type == "Button":
            return [self.navigation] if self.logged_in else [self.login]
        return []


class FakeAssessmentWindow:
    def __init__(self, form_already_open=False, duplicate_form_titles=False):
        self.form_open = form_already_open
        self.duplicate_form_titles = duplicate_form_titles
        self.outer_entry = FakeControl("Masukkan Hasil Penilaian", callback=self._open_form)
        self.inner_entry = FakeControl("Masukkan Hasil Penilaian")
        self.form = FakeControl("Lembar Jawaban Attitude Test [DISC]")
        self.inner_form = FakeControl("Lembar Jawaban Attitude Test [DISC]")

    def _open_form(self):
        self.form_open = True

    def descendants(self, control_type):
        if control_type != "Text":
            return []
        if self.form_open:
            return [self.form, self.inner_form] if self.duplicate_form_titles else [self.form]
        return [self.outer_entry, self.inner_entry]


class WindowsAdapterTests(unittest.TestCase):
    def adapter(self):
        adapter = WindowsFrexorAdapter.__new__(WindowsFrexorAdapter)
        adapter.ui_map = {
            "DISC": {"answers_per_question": 2},
            "VAK": {"answers_per_question": 1},
            "IQ": {"answers_per_question": 1},
        }
        adapter.current_module = Module.DISC
        adapter.answer_controls = [FakeEdit() for _ in range(48)]
        return adapter

    def test_disc_maps_each_question_to_two_ordered_inputs(self):
        adapter = self.adapter()
        adapter.fill_disc_question(DiscAnswer(7, "C", "D"))
        self.assertEqual(adapter.answer_controls[12].value, "C")
        self.assertEqual(adapter.answer_controls[13].value, "D")

    def test_keyboard_input_is_used_when_javafx_value_pattern_fails(self):
        control = FakeKeyboardOnlyEdit()
        WindowsFrexorAdapter._set_text(control, "Admin HR")
        self.assertEqual(control.value, "Admin HR")

    def test_indexed_text_is_verified_with_refreshed_javafx_control(self):
        adapter = self.adapter()
        adapter.window = FakeRefreshingWindow()

        adapter._set_indexed_text(0, "Nama Peserta")

        self.assertEqual(adapter.window.value, "Nama Peserta")
        self.assertGreaterEqual(adapter.window.calls, 2)

    def test_identity_field_is_not_rewritten_when_value_already_matches(self):
        adapter = self.adapter()
        adapter.window = FakeExistingValueWindow("NAMA PESERTA")

        adapter._set_indexed_text(0, "Nama Peserta")

        self.assertEqual(adapter.window.write_attempts, 0)

    def test_identity_uses_window_text_when_javafx_value_is_empty(self):
        adapter = self.adapter()
        edit = FakeWindowTextEdit("Nama Peserta")
        adapter.window = SimpleNamespace(
            descendants=lambda control_type: [edit] if control_type == "Edit" else []
        )

        adapter._set_indexed_text(0, "Nama Peserta")

        self.assertEqual(edit.write_attempts, 0)

    def test_disc_pair_warning_is_closed(self):
        adapter = self.adapter()
        warning = FakeDiscWarning()
        adapter.window = FakeMainWindow(warning)
        adapter.app = FakeApplication(None)
        adapter.app.windows = lambda: []

        adapter._dismiss_disc_pair_warning()

        self.assertTrue(warning.ok.clicked)

    def test_disc_pair_uses_keyboard_auto_advance(self):
        adapter = self.adapter()
        adapter.window = FakeEditWindow(51)
        adapter._type_disc_pair(3, "A", "D")

        self.assertEqual(adapter.window.edits[3].value, "A")
        self.assertEqual(adapter.window.edits[4].value, "D")

    def test_choice_answer_uses_keyboard_auto_advance(self):
        adapter = self.adapter()
        adapter.window = FakeEditWindow(63)
        adapter._type_choice_answer(3, "B", Module.VAK)

        self.assertEqual(adapter.window.edits[3].value, "B")

    def test_choice_answers_are_typed_as_one_verified_stream(self):
        adapter = self.adapter()
        adapter.window = FakeEditWindow(33)
        adapter.current_module = Module.VAK
        adapter.ui_map["VAK"]["answer_start_index"] = 3
        answers = [ChoiceAnswer(number, "ABC"[(number - 1) % 3]) for number in range(1, 31)]

        adapter.fill_choice_answers(Module.VAK, answers)

        self.assertEqual(
            "".join(control.value for control in adapter.window.edits[3:33]),
            "".join(answer.answer for answer in answers),
        )

    def test_choice_rejects_wrong_active_module(self):
        adapter = self.adapter()
        with self.assertRaises(UnsafeUiStateError):
            adapter.fill_choice_question(Module.VAK, ChoiceAnswer(1, "A"))

    def test_success_dialog_is_verified_and_closed(self):
        adapter = self.adapter()
        dialog = FakeDialog()
        adapter.app = FakeApplication(None)
        adapter.app.windows = lambda: []
        adapter.window = FakeMainWindow(dialog)
        adapter.config = SimpleNamespace(action_timeout_seconds=1)
        adapter.ui_map["submission"] = {
            "dialog_title": "Perhatian",
            "message_contains": "Hasil Tes sudah disimpan di",
            "confirm_button_title": "OK",
        }
        adapter.ui_map["DISC"]["form_title"] = "Lembar Jawaban Attitude Test [DISC]"

        self.assertTrue(adapter.verify_submission(Module.DISC))
        self.assertTrue(dialog.ok.clicked)

    def test_login_button_is_clicked_automatically(self):
        adapter = self.adapter()
        adapter.window = FakeLoginWindow(["", "", ""])
        adapter.config = SimpleNamespace(startup_timeout_seconds=1)
        adapter._login_if_required()
        self.assertTrue(adapter.window.login.clicked)
        self.assertFalse(adapter.window.minimized)
        self.assertTrue(adapter.window.focused)

    def test_assessment_submenu_opens_data_entry_form(self):
        adapter = self.adapter()
        adapter.window = FakeAssessmentWindow()
        adapter.config = SimpleNamespace(action_timeout_seconds=1)

        adapter._open_assessment_form({
            "entry_title": "Masukkan Hasil Penilaian",
            "form_title": "Lembar Jawaban Attitude Test [DISC]",
        })

        self.assertTrue(adapter.window.outer_entry.clicked)
        self.assertTrue(adapter.window.form_open)

    def test_assessment_form_is_not_reopened_when_already_visible(self):
        adapter = self.adapter()
        adapter.window = FakeAssessmentWindow(
            form_already_open=True,
            duplicate_form_titles=True,
        )
        adapter.config = SimpleNamespace(action_timeout_seconds=1)

        adapter._open_assessment_form({
            "entry_title": "Masukkan Hasil Penilaian",
            "form_title": "Lembar Jawaban Attitude Test [DISC]",
        })

        self.assertFalse(adapter.window.outer_entry.clicked)


if __name__ == "__main__":
    unittest.main()
