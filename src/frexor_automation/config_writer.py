from __future__ import annotations

from pathlib import Path


def _quoted(value: str | Path) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def write_config(
    path: Path,
    executable_path: str,
    spreadsheet_id: str,
    credentials_path: str,
    pdf_watch_directory: str,
    output_directory: str,
    source_type: str = "google_sheets",
    excel_path: str = "assessment-data.xlsx",
    api_base_url: str = "",
    api_token: str = "",
) -> None:
    ui_map = path.parent / "frexor_ui_map.toml"
    if not ui_map.exists():
        example = path.parent / "frexor_ui_map.example.toml"
        if example.exists():
            ui_map.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            ui_map.write_text('''discovery_complete = true
strategy = "ordered_edits"

[submission]
dialog_title = "Perhatian"
message_contains = "Hasil Tes sudah disimpan di"
confirm_button_title = "OK"

[participant]
name_edit_index = 0
position_edit_index = 1
date_edit_index = 2

[DISC]
navigation_title = "Attitude Test [DISC]"
entry_title = "Masukkan Hasil Penilaian"
form_title = "Lembar Jawaban Attitude Test [DISC]"
question_count = 24
answers_per_question = 2
answer_start_index = 3
submit_title = "Kirim"

[VAK]
navigation_title = "Working Style Test [VAK]"
entry_title = "Masukkan Hasil Penilaian"
form_title = "Lembar Jawaban Working Style Test [VAK]"
question_count = 30
answers_per_question = 1
answer_start_index = 3
submit_title = "Kirim"

[IQ]
navigation_title = "Aptitude Test [IQ]"
entry_title = "Masukkan Hasil Penilaian"
form_title = "Lembar Jawaban Aptitude Test [IQ]"
question_count = 60
answers_per_question = 1
answer_start_index = 3
submit_title = "Kirim"
''', encoding="utf-8")
    content = f'''[data_source]
type = {_quoted(source_type)}

[frexor]
adapter = "windows"
executable_path = {_quoted(executable_path)}
window_title_re = "^Frexor Psychology Assessment System$"
window_class_name = "GlassWndClass-GlassWindowClass-2"
startup_timeout_seconds = 30
action_timeout_seconds = 10
ui_map_path = "frexor_ui_map.toml"

[sheets]
spreadsheet_id = {_quoted(spreadsheet_id)}
credentials_path = {_quoted(credentials_path)}
participants_sheet = "Participants"
disc_sheet = "DISC"
vak_sheet = "VAK"
iq_sheet = "IQ"

[excel]
workbook_path = {_quoted(excel_path)}
participants_sheet = "Participants"
disc_sheet = "DISC"
vak_sheet = "VAK"
iq_sheet = "IQ"

[api]
base_url = {_quoted(api_base_url)}
token = {_quoted(api_token)}
timeout_seconds = 30

[processing]
max_retries = 3
retry_base_delay_seconds = 1.0
stop_on_fatal_error = true
continue_after_participant_error = false

[pdf]
base_directory = {_quoted(pdf_watch_directory)}
output_directory = {_quoted(output_directory)}
timeout_seconds = 60
poll_interval_seconds = 0.5
stable_seconds = 1.0
minimum_size_bytes = 100

[pdf.module_directories]
DISC = "DISC"
VAK = "VAK"
IQ = "IQ"

[logging]
level = "INFO"
directory = "logs"
'''
    path.write_text(content, encoding="utf-8")
