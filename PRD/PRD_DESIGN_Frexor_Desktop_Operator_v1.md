# PRD + Product Design — Frexor Assessment Automation Desktop

**Version:** 1.0  
**Status:** Draft for Codex implementation  
**Platform:** Windows Desktop  
**Application Type:** Standalone Windows desktop application (`.exe`)  
**Primary User:** Assessment Operator  
**Secondary User:** Administrator / Technician  
**Existing Target:** `Frexor.exe`  
**Source of Truth:** Google Sheets  
**Primary Output:** Verified assessment result PDFs

---

# 1. Product Definition

Frexor Assessment Automation is a Windows desktop application that automates the transfer of participant assessment answers from Google Sheets into the Frexor Psychology Assessment System.

The application is an operator-facing desktop control center. It hides the underlying automation implementation and presents a simple workflow suitable for users with little or no technical knowledge.

The intended daily experience is:

```text
Open application
      ↓
System checks readiness
      ↓
Operator clicks "Mulai Proses"
      ↓
Application automatically processes participants
      ↓
Frexor receives DISC + VAK + IQ answers
      ↓
Application automatically clicks "Kirim"
      ↓
Frexor generates PDF
      ↓
Application verifies PDF
      ↓
Application marks participant as completed
      ↓
Next participant
      ↓
Final summary
```

---

# 2. Product Goals

## 2.1 Primary

- Make batch processing of assessment participants simple.
- Remove repetitive manual data entry.
- Automatically submit each assessment.
- Automatically detect and verify result PDFs.
- Prevent accidental duplicate processing.
- Make failures understandable to non-technical users.
- Provide safe resume/recovery.

## 2.2 UX Goal

A normal operator should be able to operate the application without understanding:

- Google APIs
- OAuth
- Python
- Windows UI Automation
- Frexor internals
- PDF generation internals
- application logs
- database concepts

---

# 3. Assessment Domain

The system supports three assessment modules.

## DISC — Attitude Test

Two answers per question:

```text
Mirip
Tidak Mirip
```

## VAK — Working Style Test

One answer per question:

```text
Multiple choice
```

## IQ — Aptitude Test

One answer per question:

```text
Multiple choice
```

The automation must send the participant's existing answers to Frexor. It must never invent, change, or score answers.

---

# 4. User Personas

## 4.1 Operator

Typical skills:

- Basic Windows usage
- Can open an application
- Can use a mouse and keyboard
- Can review a spreadsheet

Operator should not be expected to troubleshoot code or automation internals.

## 4.2 Administrator

Responsible for initial configuration and technical support.

Can access:

- settings
- connection diagnostics
- application paths
- logs
- advanced retry configuration

---

# 5. Desktop Application Model

The product should ship as a Windows application.

Preferred distribution:

```text
Frexor Assessment Automation Setup.exe
```

Installation creates:

```text
Frexor Assessment Automation.exe
```

The operator should be able to launch it from:

- Desktop shortcut
- Start Menu

No terminal should be required for normal operation.

---

# 6. Recommended Technology Direction

The implementation technology may be chosen by Codex/engineering, but the product requirements are:

- native-feeling Windows desktop UX;
- reliable packaging as `.exe`;
- secure credential storage;
- robust Windows application automation;
- responsive UI while automation is running;
- clean separation between UI and automation engine.

A suitable implementation could use:

- Python + PySide6 for the desktop UI;
- existing automation engine;
- Windows UI Automation / pywinauto for Frexor interaction;
- Google Sheets API for data access;
- local persistent state for run recovery.

This is a recommendation, not a hard requirement if the existing codebase uses another stack.

---

# 7. Information Architecture

The application should have a very small number of primary screens.

```text
Home
│
├── Run / Current Batch
│
├── Participants / Problems
│
├── Results
│
└── Settings
```

The default operator workflow should require only:

```text
Home → Start → Progress → Result
```

---

# 8. Visual Design Principles

The visual language must be:

- clean;
- modern;
- professional;
- calm;
- minimal;
- readable;
- not visually noisy;
- not similar to old-school Windows admin tools.

Avoid:

- excessive gradients;
- heavy 3D effects;
- dense tables on the home page;
- too many colors;
- tiny text;
- multiple competing primary buttons;
- decorative UI that does not help operation.

Use:

- generous spacing;
- clear visual hierarchy;
- restrained colors;
- rounded but not overly playful components;
- simple icons;
- modern typography;
- consistent card and button treatment;
- obvious status indicators.

Recommended design direction:

> Modern internal-business application, closer to a contemporary productivity app than a classic WinForms utility.

---

# 9. Design Tokens

Suggested baseline:

## Typography

- Font: Segoe UI Variable or another modern system font.
- Primary text: 16 px.
- Secondary text: 13–14 px.
- Page title: 24–28 px.
- Major number / KPI: 30–40 px.

Avoid using more than 3–4 font sizes on one screen.

## Spacing

Use an 8 px spacing grid:

```text
8
16
24
32
40
48
```

## Corner Radius

Suggested:

- small controls: 6–8 px
- cards: 10–14 px
- dialogs: 12–16 px

Avoid extremely rounded "mobile app" pills everywhere.

## Color Semantics

Use restrained semantic colors:

- neutral = normal/information;
- green = success;
- amber = attention/warning;
- red = error;
- blue/accent = primary action.

Do not color every component.

---

# 10. Main Navigation

Use a compact sidebar or top navigation.

Recommended:

```text
┌─────────────────────────────┐
│ Logo / App Name              │
│                              │
│  Beranda                     │
│  Proses                      │
│  Peserta                     │
│  Hasil                       │
│                              │
│                              │
│  Pengaturan                  │
└─────────────────────────────┘
```

For a small application, a sidebar of approximately 220–240 px is sufficient.

Do not create a large enterprise-style navigation system for an application with only a few functions.

---

# 11. Home Screen Design

The Home screen is the most important operator screen.

## Goal

Answer these questions immediately:

1. Is everything ready?
2. How many participants are waiting?
3. What happened in the previous run?
4. Can I start?

## Wireframe

```text
┌───────────────────────────────────────────────────────────┐
│ Frexor Assessment Automation                              │
├──────────────┬────────────────────────────────────────────┤
│              │                                            │
│ Beranda      │  Selamat datang                            │
│              │  Semua sistem siap digunakan.              │
│ Proses       │                                            │
│ Peserta      │  ┌──────────────────────────────────────┐  │
│ Hasil        │  │ 60                                   │  │
│              │  │ peserta siap diproses                 │  │
│              │  └──────────────────────────────────────┘  │
│              │                                            │
│              │  Pemeriksaan                                │
│              │  ✓ Data peserta                             │
│              │  ✓ DISC                                    │
│              │  ✓ VAK                                     │
│              │  ✓ IQ                                      │
│              │  ✓ Frexor                                  │
│              │  ✓ Folder hasil                            │
│              │                                            │
│              │             [ Mulai Proses ]               │
│              │                                            │
│              │  Terakhir diproses: 02 Okt 2026            │
└──────────────┴────────────────────────────────────────────┘
```

---

# 12. Primary Action

The Home screen should have exactly one dominant action:

```text
Mulai Proses
```

Avoid multiple equal-weight primary buttons.

Secondary actions:

```text
Lihat Peserta
Pengaturan
Buka Hasil
```

must visually recede.

---

# 13. Run / Progress Screen

When processing begins, move to a dedicated progress screen.

## Wireframe

```text
┌───────────────────────────────────────────────────────────┐
│ Proses Assessment                                         │
├───────────────────────────────────────────────────────────┤
│                                                           │
│             Memproses peserta 23 dari 60                 │
│                                                           │
│  ███████████████████░░░░░░░░░░░░░░░                      │
│                                                           │
│  Budi Santoso                                            │
│  ID 023                                                  │
│                                                           │
│  ✓ Data peserta                                          │
│  ✓ DISC                                                   │
│  ✓ VAK                                                    │
│  ● IQ                                                     │
│  ○ Mengirim hasil                                        │
│  ○ Memverifikasi PDF                                     │
│                                                           │
│  Berhasil 22       Bermasalah 0       Tersisa 37         │
│                                                           │
│                              [ Hentikan Proses ]          │
└───────────────────────────────────────────────────────────┘
```

The current step must be obvious.

---

# 14. Do Not Show Fake Progress

Progress must reflect real processing state.

Do not animate a fake progress bar that reaches 90% and stops.

The displayed stage should be tied to actual automation states.

Example:

```text
DISC
VAK
IQ
Submit
PDF
Done
```

---

# 15. Current Participant Card

Use one clear card:

```text
Budi Santoso
ID 023

Sedang mengerjakan:
IQ Test
```

Do not display excessive raw data.

---

# 16. Stop Behavior

When the user clicks `Hentikan Proses`:

```text
Apakah Anda yakin ingin menghentikan proses?

Program akan menyelesaikan langkah aman yang sedang berjalan
sebelum berhenti.

[ Lanjutkan Proses ] [ Hentikan ]
```

If stopping immediately could be unsafe, explain it.

---

# 17. Participant Screen

The Participants screen helps operators review status without exposing technical complexity.

Recommended columns:

| ID | Nama | DISC | VAK | IQ | Hasil |
|---|---|---|---|---|---|
| 001 | Andi | ✓ | ✓ | ✓ | Selesai |
| 002 | Budi | ✓ | ✓ | ! | Perlu diperiksa |
| 003 | Citra | ✓ | ✓ | ✓ | Selesai |

Use icons/text together; do not rely on color alone.

Filters:

```text
Semua
Siap diproses
Berjalan
Selesai
Perlu diperiksa
```

Search:

```text
Cari nama atau ID...
```

---

# 18. Error Detail Screen

When a participant fails:

```text
┌─────────────────────────────────────────────┐
│ Perlu diperiksa                            │
│                                             │
│ Budi Santoso                                │
│ ID 023                                      │
│                                             │
│ Hasil PDF belum ditemukan.                  │
│                                             │
│ Proses dihentikan untuk menjaga keamanan    │
│ data peserta berikutnya.                    │
│                                             │
│ [ Coba Lagi ]                               │
│ [ Lewati Peserta ]                          │
│ [ Lihat Detail ]                            │
└─────────────────────────────────────────────┘
```

`Lihat Detail` can expose technical information to authorized users.

---

# 19. Result Screen

After successful batch:

```text
┌───────────────────────────────────────────────────────────┐
│ Proses Selesai                                            │
│                                                           │
│                  ✓                                        │
│            Semua proses selesai                           │
│                                                           │
│     60 Peserta                                            │
│     58 Berhasil                                           │
│      2 Perlu diperiksa                                    │
│                                                           │
│     PDF berhasil: 58                                     │
│                                                           │
│   [ Buka Folder Hasil ]   [ Lihat Masalah ]               │
└───────────────────────────────────────────────────────────┘
```

Do not use "Semua proses selesai" when errors remain.

In partial success:

```text
Proses selesai dengan 2 peserta yang perlu diperiksa.
```

---

# 20. Results Screen

Show the generated files in a simple list.

| Peserta | Status | PDF |
|---|---|---|
| Andi | Siap | Buka |
| Budi | Siap | Buka |
| Citra | Siap | Buka |

Actions:

- Open PDF
- Open participant folder
- Open results folder

The system should resolve file paths internally.

The operator must not need to copy a path manually.

---

# 21. Settings Screen

Settings should be grouped.

## Connection

```text
Google Account
Connected ✓
[ Test Connection ]
```

## Frexor

```text
Frexor Application
C:\...\Frexor.exe
[ Change ]
[ Test ]
```

## Results

```text
Output Folder
C:\...\Results
[ Change ]
[ Open ]
```

## Advanced

Put technical settings behind:

```text
Advanced Settings
```

Advanced settings may include:

- timeout;
- retry count;
- stop-on-error behavior;
- logging level;
- diagnostics.

---

# 22. First-Run Setup UX

Use a wizard with 3–4 simple steps.

### Screen 1

```text
Selamat datang di Frexor Assessment Automation

Mari siapkan aplikasi ini untuk pertama kali.

[ Mulai Setup ]
```

### Screen 2

```text
Hubungkan Google Sheets

[ Hubungkan Akun Google ]
✓ Akun terhubung

[ Lanjut ]
```

### Screen 3

```text
Hubungkan Frexor

Frexor ditemukan:
C:\...\Frexor.exe

[ Test Frexor ]

✓ Frexor dapat dijalankan

[ Lanjut ]
```

### Screen 4

```text
Folder hasil PDF

C:\...\Results

✓ Folder siap digunakan

[ Selesai ]
```

---

# 23. Accessibility

Minimum requirements:

- text must remain readable at common Windows scaling;
- keyboard navigation should work for major actions;
- buttons must have clear labels;
- important states must use text + icons, not color alone;
- focus state must be visible;
- avoid tiny controls;
- avoid information being communicated by color alone.

---

# 24. Responsive Window Behavior

Although this is a desktop application, support common resolutions.

Minimum target:

- 1280×720

Recommended:

- 1366×768
- 1920×1080

The layout should gracefully resize.

Avoid placing critical actions outside the visible viewport.

---

# 25. Window Behavior During Automation

The automation engine may need to interact with Frexor.

The application should manage:

- Frexor window visibility;
- focus;
- unexpected dialogs;
- Frexor crash;
- Frexor being closed;
- loss of focus.

The operator-facing application should clearly show:

```text
Frexor sedang digunakan oleh automation.
```

Avoid requiring the operator to manipulate Frexor while a batch is running.

---

# 26. System Tray

Optional for MVP.

If supported:

- minimize to tray only on explicit user action;
- do not silently hide critical errors;
- tray icon should indicate running/error state.

---

# 27. Notifications

Use lightweight notifications for:

- batch completed;
- batch stopped;
- critical failure requiring attention.

Do not create a notification for every participant.

---

# 28. Security and Privacy UX

The application should not show credentials in normal UI.

For Google account:

```text
Akun tersambung
operator@company...
```

not raw tokens.

Logs should avoid sensitive assessment content where unnecessary.

PDFs should be treated as confidential assessment results.

---

# 29. Technical Architecture

Recommended logical components:

```text
Desktop UI
   |
   +-- Application State
   |
   +-- Batch Orchestrator
   |
   +-- Google Sheets Adapter
   |
   +-- Validation Service
   |
   +-- Frexor Automation Adapter
   |
   +-- PDF Detection/Verification Service
   |
   +-- Output/File Service
   |
   +-- Run/Resume State Store
   |
   +-- Logging Service
```

UI must not directly implement automation logic.

Example:

```text
UI
 ↓
Application Controller
 ↓
Batch Orchestrator
 ↓
Services
```

---

# 30. Separation of Concerns

Do not mix:

- UI rendering;
- Google Sheets access;
- Frexor automation;
- PDF parsing;
- state management.

This separation will make the project easier for Codex to maintain and test.

---

# 31. Local State / Recovery

The application should retain enough local state to recover from:

- application crash;
- Windows restart;
- Frexor crash;
- network interruption.

Do not rely exclusively on in-memory variables.

The local state should be treated as operational metadata, while Google Sheets remains the source of participant input data.

---

# 32. Batch Lifecycle

```text
IDLE
 ↓
PREFLIGHT
 ↓
READY
 ↓
RUNNING
 ↓
COMPLETING
 ↓
COMPLETED
```

Error:

```text
RUNNING
   ↓
ERROR
   ↓
PAUSED_FOR_REVIEW
```

The user can then:

```text
Retry
Resume
Skip
Stop
```

---

# 33. PDF Lifecycle

```text
NOT_STARTED
 ↓
SUBMITTING
 ↓
WAITING
 ↓
DETECTED
 ↓
VERIFIED
```

Failure:

```text
WAITING
 ↓
TIMEOUT / INVALID
 ↓
ERROR
```

A participant cannot become DONE before PDF verification.

---

# 34. Data Validation

Pre-flight validation should report:

```text
60 peserta ditemukan

58 siap diproses
2 perlu diperiksa
```

Clicking "perlu diperiksa" should show exactly which participants and what is missing.

Example:

```text
ID 023
VAK question 17 belum memiliki jawaban.
```

Do not merely display "Invalid data".

---

# 35. Empty States

If there are no participants:

```text
Belum ada peserta siap diproses.

Tambahkan atau perbaiki data pada Google Sheets,
lalu lakukan pemeriksaan ulang.

[ Periksa Lagi ]
```

---

# 36. Loading States

Every waiting operation must show meaningful feedback.

Bad:

```text
Loading...
```

Good:

```text
Memeriksa data peserta...
Memastikan Frexor siap...
Menunggu hasil PDF...
Memperbarui status peserta...
```

---

# 37. Error Recovery UX

The application should never leave the operator guessing what to do.

Each error screen needs:

```text
WHAT
WHY (when safely known)
WHAT NEXT
```

Example:

```text
Frexor tertutup secara tidak sengaja.

Automation dihentikan untuk menjaga data.
Silakan buka Frexor kembali atau pilih "Coba Lagi".

[ Coba Lagi ]
[ Berhenti ]
```

---

# 38. Admin Diagnostics

Advanced diagnostics should be available without cluttering the operator interface.

Example:

```text
Pengaturan → Diagnostik

✓ Google Sheets
✓ Frexor
✓ UI Automation
✓ Output Directory
✓ PDF Detection

[ Jalankan Pemeriksaan Lengkap ]
```

Technical logs can be opened from here.

---

# 39. Packaging / Deployment

The final product should ideally be delivered with:

```text
Frexor Assessment Automation Setup.exe
```

Installation:

```text
Install
 ↓
First-run setup
 ↓
Ready
```

The operator should not install:

- Python;
- pip packages;
- Node.js;
- CLI tools;
- developer dependencies.

Everything required for normal operation should be packaged.

---

# 40. Updates

Prefer an installer-based update process.

A future version may support automatic updates, but MVP can use:

```text
New installer
 ↓
Install
 ↓
Keep settings
```

Do not require operators to manually replace source files.

---

# 41. Logging Design

Two levels:

## Operator History

Simple:

```text
03 Oct 2026 10:31
Batch selesai
60 peserta
58 berhasil
2 bermasalah
```

## Technical Log

Detailed:

- timestamps;
- participant ID;
- automation state;
- error code;
- selector/control diagnostics;
- PDF path;
- timing.

Technical log should be accessible to administrators.

---

# 42. Performance Goals

The UI must stay responsive during batch processing.

Automation should run asynchronously from the UI thread.

The operator should always be able to:

- view progress;
- open details;
- request stop.

Actual processing speed depends on Frexor behavior and must not be artificially rushed.

Safety and verification are more important than maximum throughput.

---

# 43. Reliability Rules

The application must prioritize:

1. Data correctness
2. Correct participant association
3. PDF verification
4. Safe recovery
5. Throughput

Do not optimize away verification steps merely to increase speed.

---

# 44. No Silent Failure

The application must never:

- silently skip a participant;
- mark DONE without verified PDF;
- silently continue after an unknown Frexor state;
- silently replace another participant's PDF;
- discard an error without logging it.

---

# 45. Operator Language

All primary UI copy should use straightforward Indonesian.

Recommended:

- Mulai Proses
- Hentikan Proses
- Lanjutkan
- Coba Lagi
- Lihat Masalah
- Buka Hasil
- Pemeriksaan
- Selesai
- Perlu Diperiksa
- Sedang Diproses
- Menunggu
- Tidak Dapat Dilanjutkan

Avoid developer terminology:

- worker;
- queue;
- job;
- selector;
- token;
- subprocess;
- headless;
- exception;
- stack trace.

These may exist internally but should not appear in normal UI.

---

# 46. Final UX Principle

The application should follow this mental model:

```text
OPERATOR
    |
    | "Saya punya 60 peserta."
    v
APPLICATION
    |
    | "Semua data siap."
    v
OPERATOR
    |
    | "Mulai."
    v
AUTOMATION
    |
    +--> DISC
    +--> VAK
    +--> IQ
    +--> KIRIM
    +--> PDF
    +--> VERIFY
    +--> NEXT
    |
    v
APPLICATION
    |
    | "58 selesai, 2 perlu diperiksa."
    v
OPERATOR
```

The operator should feel that the software is doing the work, not that the operator is controlling a complicated automation framework.

---

# 47. Definition of Done — Desktop Product

The desktop product is ready for operator testing when:

### Installation

- [ ] A non-technical user can install the application.
- [ ] No terminal is required.
- [ ] Required runtime dependencies are packaged.

### Setup

- [ ] First-run wizard works.
- [ ] Google account connection works.
- [ ] Frexor executable can be configured/detected.
- [ ] Output folder can be configured.

### Normal Use

- [ ] Operator can see participant readiness.
- [ ] Operator can start a batch.
- [ ] Operator can monitor progress.
- [ ] Operator can stop safely.
- [ ] Operator can resume.

### Automation

- [ ] DISC data is entered automatically.
- [ ] VAK data is entered automatically.
- [ ] IQ data is entered automatically.
- [ ] Frexor Submit/Kirim is triggered automatically.
- [ ] PDF is detected and verified.
- [ ] Participant status is updated correctly.

### UX

- [ ] No raw technical errors in normal operator UI.
- [ ] All errors explain the next action.
- [ ] Main workflow is understandable without training beyond basic instruction.
- [ ] UI is clean and modern.
- [ ] UI is usable at common Windows resolutions.

### Reliability

- [ ] DONE requires verified PDF.
- [ ] Completed participants are not duplicated.
- [ ] Failed participants can be retried.
- [ ] Batches can resume safely.
- [ ] Unknown Frexor states cause safe handling.

---

# 48. Suggested Codex Implementation Instruction

Before coding, Codex should:

1. Read this PRD completely.
2. Inspect the existing automation codebase.
3. Preserve working features.
4. Identify the current application entry point.
5. Identify the current Google Sheets integration.
6. Identify the current Frexor automation implementation.
7. Identify current status tracking.
8. Identify current PDF handling.
9. Map existing functionality to the architecture in this document.
10. Produce a short implementation plan before making large architectural changes.

Codex must not rewrite working components without reason.

Where the PRD conflicts with the existing implementation, prefer explicit requirements in this document but minimize unnecessary rewrites.

---

# 49. Important Constraint for Codex

Do not treat the UI as a developer/debug interface.

The final desktop application is an operator product.

The application should be:

```text
simple to start
simple to understand
simple to recover
simple to finish
```

while keeping the automation engine sophisticated internally.
