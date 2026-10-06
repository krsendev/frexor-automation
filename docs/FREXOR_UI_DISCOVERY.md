# Frexor UI Discovery

## Confirmed Window

- UI technology exposed through UI Automation: JavaFX.
- Window title: `Frexor Psychology Assessment System`.
- Window class reported by Windows: `GlassWndClass-GlassWindowClass-2`.
- Root automation ID: `JavaFX1`.

## Confirmed Navigation

| Action | Control type | Automation ID |
|---|---|---|
| Home | Button | `JavaFX21` |
| DISC | Button | `JavaFX10` |
| IQ | Button | `JavaFX12` |
| VAK | Button | `JavaFX14` |
| Pengaturan | Button | `JavaFX2` |

## Confirmed Assessment Submenu

- Selecting DISC, VAK, or IQ first opens an assessment submenu.
- The data-entry tile is exposed as nested text controls titled `Masukkan Hasil Penilaian`.
- The text itself is not actionable. Automation uses its position to click the tile image directly above it, then waits for the module form heading.
- Form headings are exposed as nested duplicate `Text` controls. Presence checks accept one or more exact matches.
- JavaFX automation IDs are not used because they change between screens.

## Confirmed DISC Form

- Heading: `Lembar Jawaban Attitude Test [DISC]`, text control `JavaFX61`.
- Submit: `Kirim`, button `JavaFX67`.
- Back: `Kembali`, button `JavaFX65`.
- Visible edit controls: 51.
- Edit index 0: Nama, `JavaFX106`.
- Edit index 1: Posisi, `JavaFX114`.
- Edit index 2: Tanggal, `JavaFX127`.
- Edit indices 3-50: 48 answer fields for 24 DISC questions.
- Each question uses two consecutive fields: Mirip, then Tidak Mirip.

This confirms `answer_start_index = 3` and `answers_per_question = 2` for DISC.

## Confirmed VAK Form

- Heading: `Lembar Jawaban Working Style Test [VAK]`.
- Visible edit controls: 33.
- Edit indices 0-2: Nama, Posisi, Tanggal.
- Edit indices 3-32: 30 answer fields.
- `answer_start_index = 3`, `answers_per_question = 1`.

## Confirmed IQ Form

- Heading: `Lembar Jawaban Aptitude Test [IQ]`.
- Visible edit controls: 63.
- Edit indices 0-2: Nama, Posisi, Tanggal.
- Edit indices 3-62: 60 answer fields.
- `answer_start_index = 3`, `answers_per_question = 1`.

## Confirmed Submission Dialog

- The dialog is a descendant `Window` inside the main Frexor window, not a separate top-level process window.
- Title: `Perhatian`.
- Message begins with `Hasil Tes sudah disimpan di` and includes the module output folder.
- Confirmation button: `OK`.
- The main assessment form remains open behind the dialog.
- If Edge delays the dialog beyond the initial UI timeout, automation checks again after the PDF is verified and closes `Perhatian` before continuing.

Automation IDs changed between DISC, VAK, IQ, and post-submit captures. Stable visible titles and validated ordered edit counts are therefore used instead of fixed JavaFX automation IDs.
The JavaFX control tree may refresh after a field value changes. Automation reacquires the ordered visible `Edit` controls before filling every identity and answer field.
If a JavaFX field rejects the UIA value pattern, automation falls back to focusing the field and entering the value through keyboard input.
DISC may show `Perhatian` after `Mirip` is entered while `Tidak Mirip` is still empty. Automation closes only this exact warning, then fills the second value.
DISC answer fields auto-advance after one letter: first to the adjacent column, then to the next row. Automation types each two-letter answer pair through keyboard input so Frexor performs its normal focus movement without raising the transient warning.
VAK and IQ also auto-advance after one letter. Their answers are entered through keyboard input and verified after each automatic focus movement.
For speed, VAK and IQ are typed as one auto-advancing keyboard stream. Every resulting field is read back and compared with the source data before submission; any mismatch stops processing without clicking `Kirim`.

## Confirmed Login

- Login screen has exactly three visible `Edit` controls.
- Login action is a button titled `LOG IN`.
- Automation does not store or fill Frexor credentials.
- Automation immediately clicks `LOG IN` without reading or validating the login fields, then waits for the DISC navigation button.
- If the assessment menu does not appear, processing stops with `LOGIN_REQUIRED`.

The earlier `beranda.txt` represented Windows File Explorer and was excluded. The replacement
`menu-test.txt` confirms the Frexor assessment submenu.

## Pending

- Controlled integration test with dummy participants.
