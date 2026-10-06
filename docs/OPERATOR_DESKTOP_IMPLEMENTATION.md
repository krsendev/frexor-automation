# Operator Desktop Implementation

This document maps the operator-focused PRD and change request to the current implementation.

## Implemented

- PySide6 desktop shell with Indonesian operator copy.
- Primary navigation: Beranda, Proses, Peserta, Hasil, Pengaturan.
- First-run wizard for selecting Google Sheets, local Excel, or API and configuring the chosen source, Frexor path, PDF watch folder, and archive folder.
- Automatic pre-flight validation before enabling `Mulai Proses`.
- Real progress sourced from participant/module/question callbacks.
- Safe stop request; the engine stops between safe module/participant boundaries.
- Friendly operator errors with technical details behind an expandable dialog.
- Explicit retry mode for participants containing an `ERROR` module.
- Local atomic run-state metadata for recovery messaging after restart.
- Single-instance lock to prevent two batches using Frexor concurrently.
- Participant status table and validation-detail dialog.
- Batch result summary and `Buka Folder Hasil` action.
- Module-specific PDF monitoring under `Documents/Frexor PAS/DISC`, `VAK`, and `IQ`.
- Participant association through the filename pattern `Hasil <MODULE> <date> <position> <name>.pdf`.
- Frexor window refocus after the generated PDF opens automatically.
- PyInstaller build specification and Windows build script.

## Production Validation Still Required

- Run a controlled end-to-end test for DISC, VAK, and IQ with dummy data.
- Confirm the filename association using files generated during automation.
- Confirm Edge opening a new PDF tab does not disrupt subsequent Frexor focus.
- Build and test the unsigned executable on the target Windows version.
- Add installer, shortcuts, and code signing after the executable passes acceptance testing.

## Security Note

The first-run wizard currently selects an existing Google service-account JSON file. The application stores only its local path in configuration and does not display credential contents. Moving the credential into Windows Credential Manager or replacing it with an approved desktop OAuth flow remains a deployment hardening task.
