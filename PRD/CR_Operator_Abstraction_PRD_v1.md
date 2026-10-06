# Frexor Assessment Automation
## Change Request / PRD Addendum — Operator Abstraction & No-Technical-Knowledge UX

**Version:** 1.0  
**Purpose:** Replace/expand the previous "No Raw Technical Errors" and operator-facing requirements with a complete requirement for a non-technical operator experience.  
**Target implementation:** Existing Frexor automation project  
**Audience:** Codex / Software Engineer

---

## 1. Context

The automation engine may contain complex implementation details:

- Google Sheets authentication and API access
- Windows UI automation
- Frexor application state
- assessment workflow state
- PDF generation and verification
- retries and recovery
- logging
- process synchronization

These details must remain hidden from ordinary operators.

The operator should use the software as a normal Windows desktop application. The operator must not need programming, command-line, Google API, Python, UI automation, or Frexor internals knowledge.

---

## 2. Core Requirement

The software MUST abstract the technical implementation from the operator.

For normal daily operation, the operator workflow should be:

```text
Open application
      ↓
Check that data is ready
      ↓
Click "Mulai Proses"
      ↓
Monitor progress
      ↓
Handle an exceptional error only if requested
      ↓
See final result
```

The application should not require:

- terminal commands
- Python
- PowerShell
- editing configuration files
- manually entering Google credentials every run
- manually entering Google Sheet IDs every run
- manually finding PDF files
- manually clicking Frexor controls for each participant
- manually pressing `Kirim` for each participant
- interpreting raw exception messages
- manually changing internal processing states

---

## 3. Operator Roles

### 3.1 Operator

The standard user who processes assessment batches.

Operator capabilities:

- View current data readiness
- Start a batch
- Pause/stop safely
- Resume a failed batch
- View participant-level problems
- Retry a failed participant
- Open result folder
- View simple progress and summary

Operator should NOT need access to:

- credentials
- API configuration
- technical selectors
- automation internals
- raw debug configuration

### 3.2 Administrator / Technician

Optional advanced role.

Administrator can access:

- Google Sheets configuration
- Frexor executable path
- output folder
- timeout values
- retry configuration
- advanced logs
- diagnostics
- connectivity tests

These settings should be hidden from normal operator mode.

---

# 4. First-Run Setup

The first time the software is launched, show a setup wizard.

## Step 1 — Connect Data Source

```text
Hubungkan sumber data peserta

Google Sheets

[ Hubungkan Google ]

Status:
✓ Akun terhubung
```

The user should not need to paste OAuth tokens or API keys.

## Step 2 — Configure Frexor

```text
Lokasi Frexor

Frexor.exe

[ Pilih Aplikasi ]

Status:
✓ Frexor ditemukan
✓ Dapat dijalankan
```

The application should attempt automatic detection before asking the user to browse for the executable.

## Step 3 — Configure Output

```text
Folder hasil PDF

C:\Frexor\Results

[ Pilih Folder ]

Status:
✓ Folder tersedia
```

## Step 4 — Finish

```text
Setup selesai.

Semua pengaturan tersimpan.
Anda siap memproses assessment.

[ Mulai ]
```

After initial setup, these steps should not appear during normal use unless configuration is changed.

---

# 5. Pre-flight Check

Before the batch can start, run an automatic pre-flight check.

Required checks:

- Google Sheets is reachable.
- Required worksheet/data is available.
- Participant data can be read.
- Required answers exist.
- No invalid participant rows are included.
- Frexor executable is found.
- Frexor can start.
- Output directory is available.
- Previous automation session is not running.
- Required Windows permissions are available.
- The system is not already processing another batch.

Example UI:

```text
Pemeriksaan sebelum mulai

✓ Data peserta tersedia
✓ 60 peserta siap diproses
✓ Jawaban DISC lengkap
✓ Jawaban VAK lengkap
✓ Jawaban IQ lengkap
✓ Frexor tersedia
✓ Folder hasil tersedia

Semua siap.

[ Mulai Proses ]
```

If something fails:

```text
⚠ 3 peserta memiliki jawaban yang belum lengkap.

[ Lihat Peserta ]
```

The Start button should be disabled when a blocking issue exists.

---

# 6. Friendly Error Requirement

Every operator-visible error MUST explain:

1. What happened.
2. Which participant is affected, when applicable.
3. Whether the process is safe to continue.
4. What action the operator can take.

Bad:

```text
TimeoutError: Waited 30s for selector...
```

Good:

```text
Hasil PDF belum ditemukan.

Peserta:
Budi Santoso (ID 023)

Program menghentikan proses untuk mencegah
peserta berikutnya diproses dalam kondisi yang salah.

[ Coba Lagi ]
[ Lewati Peserta ]
[ Berhenti ]
```

Raw technical details can remain in the technical log but should not be the primary UI message.

---

# 7. Normal Operation Must Require Minimal Interaction

During a successful batch, the operator should not have to:

- switch windows repeatedly;
- click Frexor manually;
- press Submit manually;
- locate PDFs manually;
- update Google Sheets manually;
- restart the program between participants.

For a batch of 60 participants:

```text
Operator:
Open software → Start

Automation:
001 → 002 → 003 → ... → 060
```

---

# 8. Progress Presentation

The UI must make it obvious that the application is working.

Show:

- current participant;
- batch progress;
- current assessment;
- current step;
- PDF state;
- overall success/error counts.

Example:

```text
Memproses peserta 23 dari 60

Budi Santoso
ID 023

✓ Data peserta
✓ DISC
✓ VAK
● IQ
○ Kirim hasil
○ Verifikasi PDF

23 / 60
```

Avoid generic:

```text
Processing...
```

because users may assume the program has frozen.

---

# 9. Pause / Stop

The operator should be able to stop the batch safely.

The application must distinguish:

- `Pause/Stop requested`
- `Stopped safely`
- `Error`

Stopping should not leave a participant incorrectly marked as DONE.

Example:

```text
Proses akan dihentikan setelah langkah aman selesai.

[ Hentikan Sekarang ]
[ Batal ]
```

If immediate termination could corrupt state, use graceful stop.

---

# 10. Resume

After a stop or error, the home screen should expose:

```text
Batch sebelumnya ditemukan

58 peserta selesai
1 peserta bermasalah
1 peserta belum diproses

[ Lanjutkan Proses ]
```

The application must continue from the first eligible participant rather than reprocessing completed participants.

---

# 11. Result Screen

At the end of the batch:

```text
Proses selesai

60 peserta
58 berhasil
2 perlu diperiksa

PDF berhasil: 58

[ Buka Folder Hasil ]
[ Lihat Masalah ]
[ Selesai ]
```

The UI must distinguish successful completion from partial completion.

---

# 12. Technical Details Policy

Technical logs may contain:

- exception details
- selector information
- stack traces
- timing
- Windows automation diagnostics
- PDF detection diagnostics

But those logs must not be required for normal operator use.

Use two layers:

```text
Operator Message
+
Technical Log
```

---

# 13. Acceptance Criteria

The change is accepted when a non-technical operator can:

1. Launch the `.exe`.
2. See whether the system is ready.
3. Start a 60-participant batch with one explicit action.
4. Understand current progress without technical knowledge.
5. Understand a failure from a plain-language message.
6. Retry or resume without editing files or entering commands.
7. Open the generated results without locating technical paths manually.
8. Complete normal operation without interacting directly with Frexor for every participant.

---

# 14. Design Principle

The product should follow:

> Complex automation behind the scenes, simple workflow in front.

The software should feel like an internal business tool, not a developer tool.
