from __future__ import annotations

from pathlib import Path
import time
import tomllib
from datetime import date

from ..config import FrexorConfig
from ..domain import ChoiceAnswer, DiscAnswer, Module, Participant, frexor_identity
from ..errors import ConfigurationError, FrexorError, LoginRequiredError, UnsafeUiStateError
from .base import FrexorAdapter


class WindowsFrexorAdapter(FrexorAdapter):
    """Frexor UIA adapter using visible labels and ordered text inputs."""

    def __init__(self, config: FrexorConfig):
        self.config = config
        self.app = None
        self.window = None
        self.ui_map = self._load_map(config.ui_map_path)
        self.participant: Participant | None = None
        self.current_module: Module | None = None
        self.answer_controls: list = []

    @staticmethod
    def _load_map(path: Path) -> dict:
        if not path.exists():
            raise ConfigurationError(f"Frexor UI map not found: {path}")
        with path.open("rb") as handle:
            return tomllib.load(handle)

    def check_environment(self) -> None:
        if not self.ui_map.get("discovery_complete", False):
            raise ConfigurationError("Frexor UI discovery is incomplete; inspect UIA controls first")
        if self.ui_map.get("strategy") != "ordered_edits":
            raise ConfigurationError("Unsupported Frexor UI strategy")
        submission = self.ui_map.get("submission", {})
        submission_required = {"dialog_title", "message_contains", "confirm_button_title"}
        if submission_required - submission.keys():
            raise ConfigurationError("Incomplete submission dialog mapping")
        for module in Module:
            section = self.ui_map.get(module.value, {})
            required = {
                "navigation_title", "entry_title", "form_title", "question_count",
                "answers_per_question", "answer_start_index", "submit_title",
            }
            missing = required - section.keys()
            if missing or any(section.get(key) == "TBD" for key in required):
                detail = sorted(missing) if missing else "TBD value"
                raise ConfigurationError(f"Incomplete {module} UI mapping: {detail}")
        if not self.config.executable_path.exists():
            raise ConfigurationError(f"Frexor executable not found: {self.config.executable_path}")
        try:
            import pywinauto  # noqa: F401
        except ImportError as exc:
            raise ConfigurationError("pywinauto is required on Windows") from exc

    def launch_or_connect(self) -> None:
        from pywinauto import Application
        criteria = {"title_re": self.config.window_title_re}
        if self.config.window_class_name:
            criteria["class_name"] = self.config.window_class_name
        try:
            self.app = Application(backend="uia").connect(**criteria)
        except Exception:
            self.app = Application(backend="uia").start(str(self.config.executable_path))
        self.window = self.app.window(**criteria)
        self.window.wait("visible enabled ready", timeout=self.config.startup_timeout_seconds)
        self._login_if_required()

    def _login_if_required(self) -> None:
        login_buttons = [
            control for control in self.window.descendants(control_type="Button")
            if control.is_visible() and control.window_text().strip() == "LOG IN"
        ]
        if not login_buttons:
            return
        if len(login_buttons) != 1:
            raise UnsafeUiStateError("Frexor LOG IN button was not uniquely identified")
        login_buttons[0].click_input()
        deadline = time.monotonic() + self.config.startup_timeout_seconds
        while time.monotonic() < deadline:
            try:
                self._find_by_title("Attitude Test [DISC]", ("Button",))
                return
            except UnsafeUiStateError:
                time.sleep(0.25)
        raise LoginRequiredError("Frexor did not reach the assessment menu after LOG IN")

    def _descendants(self, control_type: str) -> list:
        if self.window is None:
            raise FrexorError("Frexor is not connected")
        return [control for control in self.window.descendants(control_type=control_type) if control.is_visible()]

    def _find_by_title(self, title: str, control_types: tuple[str, ...]):
        if self.window is None:
            raise FrexorError("Frexor is not connected")
        for control_type in control_types:
            matches = [
                control for control in self.window.descendants(control_type=control_type)
                if control.is_visible() and control.window_text().strip() == title
            ]
            if len(matches) == 1:
                return matches[0]
            if len(matches) > 1:
                raise UnsafeUiStateError(f"Multiple {control_type} controls found with title {title!r}")
        raise UnsafeUiStateError(f"Control not found with title {title!r}")

    def _has_title(self, title: str, control_types: tuple[str, ...]) -> bool:
        if self.window is None:
            raise FrexorError("Frexor is not connected")
        return any(
            control.is_visible() and control.window_text().strip() == title
            for control_type in control_types
            for control in self.window.descendants(control_type=control_type)
        )

    def _wait_for_title(self, title: str) -> None:
        deadline = time.monotonic() + self.config.action_timeout_seconds
        while time.monotonic() < deadline:
            if self._has_title(title, ("Text", "Group", "Pane", "Document")):
                return
            time.sleep(0.2)
        raise UnsafeUiStateError(f"Form title did not appear: {title!r}")

    def _open_assessment_form(self, section: dict) -> None:
        form_title = section["form_title"]
        entry_title = section["entry_title"]
        deadline = time.monotonic() + self.config.action_timeout_seconds
        while time.monotonic() < deadline:
            if self._has_title(form_title, ("Text", "Group", "Pane", "Document")):
                return

            entry_controls = [
                control for control in self.window.descendants(control_type="Text")
                if control.is_visible() and control.window_text().strip() == entry_title
            ]
            if entry_controls:
                # The JavaFX label is not actionable; the clickable tile image is above it.
                label = entry_controls[0]
                rectangle = label.rectangle()
                label.click_input(coords=(rectangle.width() // 2, -90))
                self._wait_for_title(form_title)
                return
            time.sleep(0.2)
        raise UnsafeUiStateError(
            f"Frexor assessment submenu did not appear for {form_title!r}"
        )

    def open_participant(self, participant: Participant) -> None:
        # Participant identity is entered separately on each assessment form.
        self.participant = participant

    def open_module(self, module: Module) -> None:
        if self.participant is None:
            raise UnsafeUiStateError("Participant context is missing")
        if getattr(self, "window", None) is not None:
            self.window.set_focus()
        section = self.ui_map[module.value]
        navigation = self._find_by_title(
            section["navigation_title"], ("Hyperlink", "Button", "Text", "MenuItem")
        )
        navigation.click_input()
        self._open_assessment_form(section)

        edits = self._descendants("Edit")
        start = int(section["answer_start_index"])
        expected_answers = int(section["question_count"]) * int(section["answers_per_question"])
        expected_minimum = start + expected_answers
        if len(edits) < expected_minimum:
            raise UnsafeUiStateError(
                f"{module} expected at least {expected_minimum} visible Edit controls, found {len(edits)}"
            )

        participant_map = self.ui_map["participant"]
        self._set_indexed_text(
            int(participant_map["name_edit_index"]), frexor_identity(self.participant.name)
        )
        self._set_indexed_text(
            int(participant_map["position_edit_index"]), frexor_identity(self.participant.position)
        )
        if self.participant.test_date is None:
            raise UnsafeUiStateError("Participant test_date is missing")
        self._ensure_test_date(
            int(participant_map["date_edit_index"]), self.participant.test_date
        )
        self.answer_controls = edits[start:expected_minimum]
        self.current_module = module

    def _ensure_test_date(self, edit_index: int, test_date: date) -> None:
        days = ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu")
        months = (
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember",
        )
        expected_long = (
            f"{days[test_date.weekday()]}, {test_date.day:02d} "
            f"{months[test_date.month - 1]} {test_date.year}"
        )
        accepted = {
            expected_long.casefold(),
            test_date.isoformat().casefold(),
            test_date.strftime("%d/%m/%Y").casefold(),
        }
        def visible_values() -> set[str]:
            result = set()
            for control_type in ("Pane", "Text", "Edit"):
                for control in self._descendants(control_type):
                    text = control.window_text().strip()
                    value = self._control_value(control).strip()
                    if text:
                        result.add(text.casefold())
                    if value:
                        result.add(value.casefold())
            return result

        current_values = visible_values()
        if accepted & current_values:
            return
        self._set_indexed_text(edit_index, expected_long)
        if accepted & visible_values():
            return
        raise UnsafeUiStateError(
            f"Frexor test date does not match participant data ({expected_long}); "
            f"check Edit index {edit_index}"
        )

    def _set_indexed_text(self, index: int, value: str) -> None:
        current_edits = self._descendants("Edit")
        if index >= len(current_edits):
            raise UnsafeUiStateError(
                f"Frexor Edit index {index} is unavailable; found {len(current_edits)} fields"
            )
        current_value = self._control_value(current_edits[index]).strip().upper()
        if current_value == value.strip().upper():
            return

        last_error: Exception | None = None
        for _ in range(3):
            try:
                edits = self._descendants("Edit")
                if index >= len(edits):
                    raise UnsafeUiStateError(
                        f"Frexor Edit index {index} is unavailable; found {len(edits)} fields"
                    )
                self._write_text(edits[index], value)
                break
            except Exception as exc:
                last_error = exc
                time.sleep(0.2)
        else:
            raise UnsafeUiStateError(
                f"Frexor field at Edit index {index} could not be filled: {last_error}"
            ) from last_error

        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            refreshed = self._descendants("Edit")
            if index < len(refreshed):
                actual = self._control_value(refreshed[index]).strip().upper()
                if actual == value.strip().upper():
                    return
            time.sleep(0.1)
        raise UnsafeUiStateError(
            f"Frexor field at Edit index {index} did not retain the requested value"
        )

    @staticmethod
    def _set_text(control, value: str) -> None:
        WindowsFrexorAdapter._write_text(control, value)
        if WindowsFrexorAdapter._control_value(control).strip().upper() != value.strip().upper():
            raise UnsafeUiStateError("Frexor field value did not match the requested input")

    @staticmethod
    def _write_text(control, value: str) -> None:
        try:
            control.set_edit_text(value)
        except Exception:
            # Some JavaFX fields reject UIA ValuePattern after another field changes.
            control.click_input()
            control.type_keys("^a{BACKSPACE}", set_foreground=False)
            control.type_keys(value, with_spaces=True, set_foreground=False, pause=0.02)

    @staticmethod
    def _control_value(control) -> str:
        try:
            return str(control.get_value())
        except Exception:
            try:
                return str(control.iface_value.CurrentValue)
            except Exception:
                return ""

    def _answer_control(self, module: Module, question_no: int, offset: int = 0):
        if self.current_module is not module:
            raise UnsafeUiStateError(f"Current Frexor module is not {module}")
        per_question = int(self.ui_map[module.value]["answers_per_question"])
        index = (question_no - 1) * per_question + offset
        if getattr(self, "window", None) is not None:
            start = int(self.ui_map[module.value]["answer_start_index"])
            edits = self._descendants("Edit")
            absolute_index = start + index
            if absolute_index >= len(edits):
                raise UnsafeUiStateError(
                    f"Answer field not found for {module} question {question_no}"
                )
            return edits[absolute_index]
        try:
            return self.answer_controls[index]
        except IndexError as exc:
            raise UnsafeUiStateError(f"Answer field not found for {module} question {question_no}") from exc

    def fill_disc_question(self, answer: DiscAnswer) -> None:
        start = int(self.ui_map[Module.DISC.value].get("answer_start_index", 0))
        index = start + (answer.question_no - 1) * 2
        if getattr(self, "window", None) is not None:
            self._type_disc_pair(index, answer.mirip, answer.tidak_mirip)
            return
        self._set_text(self._answer_control(Module.DISC, answer.question_no), answer.mirip)
        self._set_text(self._answer_control(Module.DISC, answer.question_no, 1), answer.tidak_mirip)

    def _type_disc_pair(self, first_index: int, mirip: str, tidak_mirip: str) -> None:
        edits = self._descendants("Edit")
        if first_index + 1 >= len(edits):
            raise UnsafeUiStateError(f"Frexor DISC pair at Edit index {first_index} is unavailable")

        # DISC auto-advances after each letter: right first, then down one row.
        edits[first_index].click_input()
        edits[first_index].type_keys(
            mirip + tidak_mirip,
            set_foreground=False,
            pause=0.08,
        )
        time.sleep(0.1)

        refreshed = self._descendants("Edit")
        actual_mirip = self._control_value(refreshed[first_index]).strip().upper()
        actual_tidak = self._control_value(refreshed[first_index + 1]).strip().upper()
        if actual_mirip != mirip.strip().upper() or actual_tidak != tidak_mirip.strip().upper():
            self._dismiss_disc_pair_warning()
            raise UnsafeUiStateError(
                f"Frexor DISC pair at Edit index {first_index} did not match the requested answers"
            )

    def _dismiss_disc_pair_warning(self) -> None:
        deadline = time.monotonic() + 1.0
        expected = "Masukkan jawaban yang berbeda untuk Mirip dan tidak mirip"
        while time.monotonic() < deadline:
            dialog = self._find_submission_dialog("Perhatian")
            if dialog is None:
                time.sleep(0.05)
                continue
            message = " ".join(
                control.window_text().strip()
                for control in dialog.descendants(control_type="Text")
                if control.is_visible() and control.window_text().strip()
            )
            if expected.casefold() not in message.casefold():
                raise UnsafeUiStateError(f"Unexpected Frexor warning while filling DISC: {message!r}")
            buttons = [
                control for control in dialog.descendants(control_type="Button")
                if control.is_visible() and control.window_text().strip() == "OK"
            ]
            if len(buttons) != 1:
                raise UnsafeUiStateError("Frexor DISC warning OK button was not uniquely identified")
            buttons[0].click_input()
            return

    def fill_choice_question(self, module: Module, answer: ChoiceAnswer) -> None:
        if getattr(self, "window", None) is not None:
            start = int(self.ui_map[module.value]["answer_start_index"])
            self._type_choice_answer(start + answer.question_no - 1, answer.answer, module)
            return
        self._set_text(self._answer_control(module, answer.question_no), answer.answer)

    def _type_choice_answer(self, index: int, answer: str, module: Module) -> None:
        edits = self._descendants("Edit")
        if index >= len(edits):
            raise UnsafeUiStateError(f"Frexor {module} answer at Edit index {index} is unavailable")

        # VAK and IQ advance to the next question after one keyboard character.
        edits[index].click_input()
        edits[index].type_keys(answer, set_foreground=False, pause=0.08)
        time.sleep(0.05)

        refreshed = self._descendants("Edit")
        actual = self._control_value(refreshed[index]).strip().upper()
        if actual != answer.strip().upper():
            raise UnsafeUiStateError(
                f"Frexor {module} answer at Edit index {index} did not match the requested value"
            )

    def fill_choice_answers(self, module: Module, answers: list[ChoiceAnswer]) -> None:
        if getattr(self, "window", None) is None:
            return super().fill_choice_answers(module, answers)
        if self.current_module is not module:
            raise UnsafeUiStateError(f"Current Frexor module is not {module}")

        ordered = sorted(answers, key=lambda item: item.question_no)
        start = int(self.ui_map[module.value]["answer_start_index"])
        edits = self._descendants("Edit")
        if start + len(ordered) > len(edits):
            raise UnsafeUiStateError(
                f"Frexor {module} expected {len(ordered)} answer fields from Edit index {start}"
            )

        # One keyboard stream follows Frexor's native auto-advance behavior.
        edits[start].click_input()
        edits[start].type_keys(
            "".join(answer.answer for answer in ordered),
            set_foreground=False,
            pause=0.05,
        )
        time.sleep(0.2)

        refreshed = self._descendants("Edit")
        mismatches = []
        for offset, expected in enumerate(ordered):
            actual = self._control_value(refreshed[start + offset]).strip().upper()
            if actual != expected.answer.strip().upper():
                mismatches.append(expected.question_no)
        if mismatches:
            raise UnsafeUiStateError(
                f"Frexor {module} bulk input verification failed at questions {mismatches}"
            )

    def submit(self, module: Module) -> None:
        if self.current_module is not module:
            raise UnsafeUiStateError(f"Cannot submit {module}; another module is active")
        title = self.ui_map[module.value]["submit_title"]
        self._find_by_title(title, ("Button", "Hyperlink", "Text")).click_input()

    def verify_submission(self, module: Module) -> bool:
        submission = self.ui_map["submission"]
        form_title = self.ui_map[module.value]["form_title"]
        deadline = time.monotonic() + self.config.action_timeout_seconds
        while time.monotonic() < deadline:
            dialog = self._find_submission_dialog(submission["dialog_title"])
            if dialog is not None:
                try:
                    dialog.set_focus()
                except Exception:
                    try:
                        self.window.set_focus()
                    except Exception:
                        pass
                texts = " ".join(
                    control.window_text().strip()
                    for control in dialog.descendants(control_type="Text")
                    if control.is_visible() and control.window_text().strip()
                )
                if submission["message_contains"] not in texts:
                    raise UnsafeUiStateError(f"Unexpected Frexor dialog message: {texts!r}")
                buttons = [
                    control for control in dialog.descendants(control_type="Button")
                    if control.is_visible()
                    and control.window_text().strip() == submission["confirm_button_title"]
                ]
                if len(buttons) != 1:
                    raise UnsafeUiStateError("Frexor success dialog OK button was not uniquely identified")
                buttons[0].click_input()
                self.current_module = None
                self.answer_controls = []
                return True
            if not self._has_title(form_title, ("Text", "Group", "Pane", "Document")):
                self.current_module = None
                self.answer_controls = []
                return True
            time.sleep(0.2)
        return False

    def _find_submission_dialog(self, title: str):
        main_window = getattr(self, "window", None)
        if main_window is not None:
            try:
                for child in main_window.descendants(control_type="Window"):
                    if child.is_visible() and child.window_text().strip() == title:
                        return child
            except Exception:
                pass
        if self.app is None:
            return None
        for window in self.app.windows():
            try:
                if window.is_visible() and window.window_text().strip() == title:
                    return window
            except Exception:
                continue
        return None

    def recover_from_error(self) -> bool:
        self.current_module = None
        self.answer_controls = []
        try:
            self.launch_or_connect()
            return True
        except Exception:
            return False

    def close_after_success(self) -> None:
        if self.config.close_edge_after_success:
            self._close_edge_windows()
        if self.config.close_after_success:
            self._close_frexor_window()

    def _close_frexor_window(self) -> None:
        window = self.window
        if window is None:
            return
        try:
            window.close()
            window.wait_not("exists", timeout=self.config.action_timeout_seconds)
        finally:
            self.window = None
            self.app = None
            self.participant = None
            self.current_module = None
            self.answer_controls = []

    def _close_edge_windows(self) -> None:
        from pywinauto import Desktop
        import psutil

        edge_windows = []
        for window in Desktop(backend="uia").windows():
            try:
                process_id = window.element_info.process_id
                if psutil.Process(process_id).name().casefold() == "msedge.exe":
                    edge_windows.append(window)
            except (psutil.Error, OSError, AttributeError):
                continue
        for window in edge_windows:
            try:
                window.close()
            except Exception:
                continue
