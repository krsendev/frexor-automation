# Product Requirements Document (PRD)
# Frexor Assessment Automation

**Version:** 1.0 Draft for Implementation
**Status:** Implementation handoff draft
**Primary consumer:** Codex / coding agent
**Target platform:** Windows
**Target application:** Frexor Psychology Assessment System (`.exe`)
**Primary data source:** Google Sheets

---

## 1. Executive Summary

Frexor Assessment Automation adalah aplikasi otomasi desktop yang membaca data jawaban peserta dari Google Sheets lalu memasukkan jawaban tersebut ke aplikasi **Frexor Psychology Assessment System** yang berjalan sebagai aplikasi `.exe` pada Windows.

Sistem ini **tidak menentukan jawaban**, **tidak melakukan scoring**, dan **tidak melakukan proses scan lembar jawaban**. Proses scan/konversi lembar jawaban menjadi data terstruktur sudah dilakukan oleh tools lain. Automation hanya bertugas memindahkan data yang sudah tersedia di Google Sheets ke Frexor secara akurat, terkontrol, dapat dilacak, dan dapat dipulihkan apabila terjadi error.

Terdapat tiga jenis assessment yang harus didukung:

1. **Attitude Test [DISC]** — setiap soal memiliki dua jawaban: `Mirip` dan `Tidak Mirip`.
2. **Working Style Test [VAK]** — setiap soal memiliki satu jawaban pilihan ganda.
3. **Aptitude Test [IQ]** — setiap soal memiliki satu jawaban pilihan ganda.

Ketiga assessment diperlakukan sebagai modul terpisah dalam satu peserta. Kegagalan pada satu modul tidak boleh menyebabkan modul yang sudah berhasil diulang secara otomatis.

---

# 2. Problem Statement

Saat ini hasil assessment yang berasal dari lembar jawaban perlu dimasukkan kembali secara manual ke Frexor. Proses tersebut memiliki beberapa masalah:

- input berulang dan memakan waktu;
- risiko salah mengetik atau salah memilih jawaban;
- sulit melakukan batch processing untuk banyak peserta;
- sulit mengetahui peserta mana yang sudah selesai dan mana yang gagal;
- jika proses terhenti di tengah jalan, operator berisiko mengulang peserta yang sebenarnya sudah berhasil diproses;
- tidak ada mekanisme terpusat untuk mencatat keberhasilan, kegagalan, dan alasan error.

Solusi yang dibutuhkan adalah automation layer yang menjadikan Google Sheets sebagai sumber data dan Frexor sebagai target input.

---

# 3. Product Goal

## 3.1 Goal utama

Menghilangkan sebanyak mungkin proses input manual dari Google Sheets ke Frexor tanpa mengubah logika assessment Frexor.

## 3.2 Goal operasional

Automation harus dapat:

- mengambil peserta yang berstatus siap diproses;
- memvalidasi data sebelum membuka/mengisi assessment;
- membuka atau fokus ke Frexor;
- mengisi assessment DISC, VAK, dan IQ sesuai data;
- memastikan data berhasil di-submit sebelum menandai modul sebagai selesai;
- mencatat status per modul;
- menangani error dengan aman;
- melanjutkan peserta berikutnya hanya jika kondisi aman;
- mencegah reprocessing yang tidak diperlukan.

---

# 4. Non-Goals / Out of Scope

Hal-hal berikut **bukan tanggung jawab aplikasi ini**:

### 4.1 Scan lembar jawaban

Tidak perlu membangun OCR, OMR, image recognition, atau scanner integration. Hasil scan sudah tersedia melalui tools yang sudah ada.

### 4.2 Menentukan jawaban

Automation tidak boleh menghasilkan atau mengubah jawaban peserta.

### 4.3 Scoring / interpretation

Perhitungan DISC, VAK, IQ, interpretasi kepribadian, atau hasil psikologis tetap menjadi tanggung jawab Frexor.

### 4.4 Modifikasi aplikasi Frexor

Tidak boleh mengubah executable, database internal, atau source code Frexor kecuali investigasi teknis benar-benar membuktikan perubahan tersebut mutlak diperlukan dan disetujui kemudian.

### 4.5 Penggantian Frexor

Sistem tidak bertujuan membuat assessment engine sendiri.

---

# 5. Users / Roles

## 5.1 Operator

Operator adalah pengguna utama aplikasi.

Tanggung jawab:

- memastikan Google Sheets berisi data yang benar;
- menjalankan automation;
- memantau progress;
- menangani peserta yang berstatus `ERROR`;
- menjalankan retry/reprocess jika diperlukan.

## 5.2 Administrator / Developer

Memiliki akses konfigurasi untuk:

- koneksi Google Sheets;
- lokasi / executable Frexor;
- mapping field Frexor;
- konfigurasi timeout dan retry;
- logging;
- diagnostic mode.

---

# 6. High-Level Architecture

```text
┌─────────────────────┐
│  Google Sheets      │
│  Source of Truth    │
└─────────┬───────────┘
          │
          │ Google Sheets API
          ▼
┌─────────────────────┐
│ Automation Agent    │
│ Windows             │
│                     │
│ 1. Reader           │
│ 2. Validator        │
│ 3. Orchestrator     │
│ 4. Frexor Adapter   │
│ 5. Logger           │
│ 6. Status Updater   │
└─────────┬───────────┘
          │
          │ Windows UI Automation / other
          ▼
┌─────────────────────┐
│ Frexor Psychology   │
│ Assessment System   │
│ (.exe)              │
└─────────────────────┘
```

### Prinsip arsitektur

- Google Sheets adalah sumber data utama untuk input automation.
- Frexor adalah target aplikasi.
- Automation tidak menyimpan salinan jawaban sebagai sumber kebenaran baru.
- Proses harus idempotent sejauh memungkinkan.
- Status per modul harus dapat dilacak.
- Detail implementasi UI Frexor harus dienkapsulasi dalam `FrexorAdapter`, sehingga mekanisme interaksi dapat diganti tanpa mengubah logika bisnis utama.

---

# 7. Execution Environment

Target deployment awal:

- Windows 10/11 atau Windows Server dengan desktop session yang dapat menjalankan Frexor;
- komputer tersebut harus memiliki akses jaringan ke Google Sheets;
- Frexor `.exe` ter-install pada komputer tersebut;
- automation harus berjalan pada session Windows yang memungkinkan interaksi dengan UI jika Frexor membutuhkan UI interaction.

### Catatan penting

Frexor diketahui berjalan sebagai `.exe`, tetapi **jenis kontrol UI di dalam aplikasi belum dipastikan**. Karena itu implementasi harus melalui abstraction layer.

Urutan investigasi teknis yang disarankan:

1. Windows UI Automation / Microsoft UI Automation;
2. pywinauto atau library UI automation setara;
3. jika aplikasi memakai embedded web UI, gunakan mekanisme yang sesuai dengan embedded browser;
4. keyboard automation / AutoHotkey sebagai fallback;
5. coordinate/image-based automation hanya sebagai pilihan terakhir.

Jangan mengunci desain bisnis pada salah satu library sebelum struktur UI Frexor diinspeksi.

---

# 8. Assessment Modules

## 8.1 DISC — Attitude Test

**Model jawaban:** dua jawaban per soal.

Field:

- `Mirip`
- `Tidak Mirip`

Contoh:

```text
Question 1
Mirip       = A
Tidak Mirip = C
```

Automation wajib mengisi kedua field untuk setiap soal DISC.

### Validation DISC

- setiap soal harus memiliki tepat satu jawaban `Mirip`;
- setiap soal harus memiliki tepat satu jawaban `Tidak Mirip`;
- jawaban harus termasuk dalam pilihan yang diperbolehkan Frexor;
- pasangan jawaban tidak boleh tertukar;
- jumlah soal harus sesuai konfigurasi assessment.

---

## 8.2 VAK — Working Style Test

**Model jawaban:** satu jawaban pilihan ganda per soal.

Contoh:

```text
Question 1
Answer = B
```

Automation hanya mengisi satu pilihan untuk setiap soal.

### Validation VAK

- setiap soal harus memiliki satu jawaban;
- jawaban harus termasuk dalam pilihan yang diperbolehkan;
- tidak boleh ada soal kosong.

---

## 8.3 IQ — Aptitude Test

**Model jawaban:** satu jawaban pilihan ganda per soal.

Contoh:

```text
Question 1
Answer = C
```

Automation hanya mengisi satu pilihan untuk setiap soal.

### Validation IQ

- setiap soal harus memiliki satu jawaban;
- jawaban harus termasuk dalam pilihan yang diperbolehkan;
- tidak boleh ada soal kosong.

---

# 9. Data Model

Desain data harus memisahkan identitas peserta, status assessment, dan jawaban detail.

Struktur final Google Sheets boleh disesuaikan setelah format sheet aktual diketahui, tetapi model logis berikut wajib dipertahankan.

## 9.1 Sheet `Participants`

Contoh:

| participant_id | name | position | overall_status | created_at | updated_at |
|---|---|---|---|---|---|
| P001 | Andi | Operator | READY | 2026-10-03 | 2026-10-03 |
| P002 | Budi | Engineer | PROCESSING | 2026-10-03 | 2026-10-03 |

### Status yang disarankan

- `READY`
- `PROCESSING`
- `PARTIAL`
- `DONE`
- `ERROR`
- `SKIPPED`

---

## 9.2 Sheet `DISC`

Contoh:

| participant_id | question_no | mirip | tidak_mirip |
|---|---:|---|---|
| P001 | 1 | A | C |
| P001 | 2 | B | D |
| P001 | 3 | D | A |

---

## 9.3 Sheet `VAK`

Contoh:

| participant_id | question_no | answer |
|---|---:|---|
| P001 | 1 | B |
| P001 | 2 | A |
| P001 | 3 | C |

---

## 9.4 Sheet `IQ`

Contoh:

| participant_id | question_no | answer |
|---|---:|---|
| P001 | 1 | C |
| P001 | 2 | D |
| P001 | 3 | B |

---

# 10. Status Model

Status wajib dilacak minimal pada level participant dan assessment module.

Contoh:

| ID | Name | DISC | VAK | IQ | Overall |
|---|---|---|---|---|---|
| P001 | Andi | DONE | DONE | DONE | DONE |
| P002 | Budi | DONE | ERROR | READY | PARTIAL |
| P003 | Citra | READY | READY | READY | READY |

## 10.1 State definitions

### READY

Modul belum diproses dan memiliki data valid.

### PROCESSING

Automation sedang mengerjakan modul.

### DONE

Automation telah selesai mengisi dan mendapat indikasi bahwa submit berhasil.

### ERROR

Automation gagal menjalankan modul.

### PARTIAL

Sebagian modul peserta sudah selesai tetapi masih ada modul yang belum selesai / error.

### SKIPPED

Modul sengaja dilewati berdasarkan konfigurasi atau keputusan operator.

---

# 11. Core Processing Flow

## 11.1 Startup

1. Jalankan automation.
2. Load konfigurasi.
3. Validasi koneksi Google Sheets.
4. Validasi path Frexor.
5. Pastikan Frexor dapat dijalankan / ditemukan.
6. Tampilkan status environment.

Jika environment tidak valid, **jangan memproses peserta**.

---

## 11.2 Load participant

1. Ambil peserta dengan status yang memenuhi kriteria processing.
2. Pilih modul yang belum `DONE`.
3. Pastikan data modul tersedia.
4. Lakukan validation.

Contoh:

```text
Participant P002
DISC = DONE
VAK  = ERROR
IQ   = READY

Next modules:
VAK, IQ
```

DISC tidak boleh diulang otomatis.

---

## 11.3 Process DISC

```text
Load DISC answers
        ↓
Validate completeness
        ↓
Open/focus Frexor
        ↓
Navigate to DISC
        ↓
Identify question 1
        ↓
Input Mirip
Input Tidak Mirip
        ↓
Repeat until last question
        ↓
Validate form state
        ↓
Submit
        ↓
Verify submission
        ↓
Mark DISC = DONE
```

---

## 11.4 Process VAK

```text
Load VAK answers
        ↓
Validate completeness
        ↓
Navigate to VAK
        ↓
Input one answer per question
        ↓
Validate form state
        ↓
Submit
        ↓
Verify submission
        ↓
Mark VAK = DONE
```

---

## 11.5 Process IQ

```text
Load IQ answers
        ↓
Validate completeness
        ↓
Navigate to IQ
        ↓
Input one answer per question
        ↓
Validate form state
        ↓
Submit
        ↓
Verify submission
        ↓
Mark IQ = DONE
```

---

# 12. Important Safety Rule: Never Mark DONE Prematurely

Status `DONE` hanya boleh ditulis setelah automation memiliki bukti yang cukup bahwa submit berhasil.

Contoh bukti yang dapat digunakan setelah investigasi UI:

- halaman berubah;
- confirmation muncul;
- tombol / state berubah;
- record/participant berpindah ke tahap berikutnya;
- pesan sukses;
- atau indikator lain yang dapat diidentifikasi secara deterministik.

Jika submit tidak dapat diverifikasi, status harus tetap `ERROR` atau `PROCESSING` sesuai recovery strategy. **Jangan menganggap klik tombol submit sebagai bukti keberhasilan.**

---

# 13. Idempotency and Resume

Sistem harus aman apabila:

- aplikasi automation ditutup tiba-tiba;
- komputer restart;
- Frexor crash;
- koneksi internet ke Google Sheets putus;
- user menghentikan proses;
- satu modul gagal sementara modul lain sudah selesai.

### Prinsip utama

```text
Jika DISC = DONE
maka restart tidak boleh mengulang DISC secara otomatis.
```

Sistem melanjutkan modul yang belum `DONE`.

---

# 14. Error Handling

Kategori error minimal:

### Data error

Contoh:

- participant ID kosong;
- jawaban kurang;
- jawaban tidak valid;
- duplikasi question number;
- jumlah soal tidak sesuai konfigurasi.

Action:

- jangan membuka assessment untuk participant tersebut;
- tandai `ERROR`;
- simpan alasan yang jelas.

### Frexor application error

Contoh:

- executable tidak ditemukan;
- aplikasi crash;
- window tidak ditemukan;
- control tidak ditemukan.

Action:

- retry terbatas jika aman;
- jika tetap gagal, tandai `ERROR`;
- jangan melanjutkan dengan kondisi UI yang tidak diketahui.

### Network / Google Sheets error

Contoh:

- timeout;
- API unavailable;
- authentication error;
- rate limit.

Action:

- retry dengan exponential backoff untuk error yang bersifat sementara;
- jangan mengubah status peserta jika update status ke Sheet belum berhasil diverifikasi.

---

# 15. Retry Policy

Retry tidak boleh dilakukan tanpa batas.

Default MVP yang disarankan:

- `max_attempts = 3` untuk operasi transient;
- delay meningkat antar percobaan;
- error UI yang berpotensi menyebabkan data salah **tidak boleh otomatis di-retry tanpa reset state**.

Contoh:

```text
Attempt 1 → fail
Attempt 2 → fail
Attempt 3 → fail
        ↓
ERROR
```

Untuk kegagalan input field, sistem harus lebih konservatif daripada kegagalan network.

---

# 16. Batch Processing

Automation harus mendukung pemrosesan banyak peserta.

Contoh:

```text
P001 → DONE
P002 → DONE
P003 → ERROR
P004 → DONE
P005 → READY
```

Behavior default:

- peserta `DONE` dilewati;
- peserta `READY` diproses;
- peserta `PARTIAL` diproses hanya pada modul yang belum selesai;
- peserta `ERROR` dapat ditangani dalam retry/reprocess mode;
- error fatal pada environment dapat menghentikan seluruh batch untuk mencegah kerusakan data.

---

# 17. Reprocess / Retry Manual

Operator harus dapat memilih peserta dengan status `ERROR` untuk diproses ulang setelah masalah diperbaiki.

Contoh:

```text
P002
DISC = DONE
VAK  = ERROR
IQ   = READY
```

Setelah operator memilih `Retry`, sistem harus:

```text
DISC → SKIP
VAK  → PROCESS
IQ   → PROCESS
```

Bukan mengulang DISC.

---

# 18. Dry Run / Validation Mode

Sebelum production processing, sistem sebaiknya menyediakan mode validasi yang:

- membaca Google Sheets;
- melakukan validation;
- menemukan data yang invalid;
- memeriksa konfigurasi;
- **tidak mengirim submit ke Frexor**.

Contoh output:

```text
P001 → VALID
P002 → VALID
P003 → INVALID: DISC question 17 missing
P004 → INVALID: IQ question 12 invalid option
```

Dry run sangat disarankan untuk mencegah input batch yang salah.

---

# 19. UI Requirements

MVP tidak membutuhkan UI yang kompleks.

Minimum UI:

```text
┌──────────────────────────────────────────┐
│       FREXOR ASSESSMENT AUTOMATION       │
├──────────────────────────────────────────┤
│ Google Sheet: Connected                  │
│ Frexor: Ready                            │
│                                          │
│ Participants: 100                        │
│ Ready:        75                         │
│ Processing:    1                         │
│ Done:         23                         │
│ Error:         1                         │
│                                          │
│ [ Validate ] [ Start ] [ Stop ]          │
│ [ Retry Error ]                          │
│                                          │
│ Current: P024 - VAK                      │
│ Progress: 12 / 20                        │
└──────────────────────────────────────────┘
```

### UI behavior

- `Validate` → hanya melakukan validation.
- `Start` → mulai batch processing.
- `Stop` → meminta automation berhenti pada safe point.
- `Retry Error` → memproses item yang error sesuai aturan.

Stop tidak boleh mematikan proses secara paksa jika sedang berada pada tahap input yang belum aman. Automation harus berhenti pada safe point atau setelah menyelesaikan rollback/recovery yang tersedia.

---

# 20. Logging

Semua aktivitas penting harus dilog.

Format minimal:

```text
2026-10-03 10:21:04 INFO  P001 START participant
2026-10-03 10:21:05 INFO  P001 DISC validation passed
2026-10-03 10:21:07 INFO  P001 DISC input question=1
2026-10-03 10:21:15 INFO  P001 DISC submit clicked
2026-10-03 10:21:17 INFO  P001 DISC submit verified
2026-10-03 10:21:18 INFO  P001 DISC DONE
```

Error:

```text
2026-10-03 10:24:31 ERROR P002 VAK control_not_found question=17
```

Log minimal harus memiliki:

- timestamp;
- level;
- participant ID;
- module;
- operation;
- detail error jika ada.

Jangan simpan data pribadi secara berlebihan dalam log.

---

# 21. Audit Trail in Google Sheets

Minimal status fields yang dapat diperbarui:

- module status;
- overall status;
- last processed timestamp;
- error message / error code;
- attempt count.

Contoh:

| ID | DISC | VAK | IQ | Overall | Last Error | Attempts |
|---|---|---|---|---|---|---:|
| P001 | DONE | DONE | DONE | DONE | | 3 |
| P002 | DONE | ERROR | READY | PARTIAL | VAK_Q17_NOT_FOUND | 2 |

Error message harus ringkas, machine-readable bila memungkinkan, dan mudah dipahami operator.

---

# 22. Configuration

Konfigurasi tidak boleh di-hardcode di banyak tempat.

Contoh konfigurasi:

```yaml
frexor:
  executable_path: "C:\\Path\\To\\Frexor.exe"
  startup_timeout_seconds: 30
  action_timeout_seconds: 10

sheets:
  spreadsheet_id: "..."
  participants_sheet: "Participants"
  disc_sheet: "DISC"
  vak_sheet: "VAK"
  iq_sheet: "IQ"

processing:
  max_retries: 3
  stop_on_fatal_error: true
  skip_done: true

logging:
  level: INFO
  directory: "logs"
```

Nilai di atas hanya contoh. Jangan memasukkan credential aktual ke source code atau commit repository.

---

# 23. Google Sheets Integration Requirements

Automation harus menggunakan Google Sheets API atau library resmi/terpercaya yang sesuai.

Minimal kemampuan:

- read participant data;
- read DISC answers;
- read VAK answers;
- read IQ answers;
- update module status;
- update overall status;
- update error information;
- update timestamps;
- melakukan update secara aman dan terkontrol.

### Caching

Data yang dibaca untuk satu peserta boleh dipertahankan di memory selama satu processing cycle, tetapi Google Sheets tetap menjadi source of truth.

Jangan membuat salinan lokal yang kemudian dianggap sebagai sumber utama.

---

# 24. Data Validation Rules

## Participant validation

- `participant_id` wajib ada.
- `name` wajib ada jika Frexor memerlukannya.
- `position` wajib ada jika Frexor memerlukannya.
- participant tidak boleh diproses apabila identifier ambigu.

## DISC validation

- setiap question number unik;
- semua question yang diharapkan tersedia;
- `mirip` terisi;
- `tidak_mirip` terisi;
- value valid;
- tidak ada field yang tertukar.

## VAK validation

- setiap question number unik;
- semua question yang diharapkan tersedia;
- satu answer per question;
- answer valid.

## IQ validation

- setiap question number unik;
- semua question yang diharapkan tersedia;
- satu answer per question;
- answer valid.

---

# 25. Frexor Adapter Design

Semua interaksi langsung dengan Frexor harus diisolasi.

Konsep interface:

```text
FrexorAdapter
├── launch()
├── connect()
├── login_if_required()
├── open_participant_context()
├── open_disc()
├── fill_disc_question(question_no, mirip, tidak_mirip)
├── submit_disc()
├── verify_disc_submission()
├── open_vak()
├── fill_vak_question(question_no, answer)
├── submit_vak()
├── verify_vak_submission()
├── open_iq()
├── fill_iq_question(question_no, answer)
├── submit_iq()
├── verify_iq_submission()
└── recover_from_error()
```

Nama method boleh berubah sesuai implementasi, tetapi prinsipnya wajib dipertahankan.

Business logic tidak boleh bergantung langsung pada koordinat layar.

---

# 26. Separation of Concerns

Codebase minimal harus dipisahkan menjadi komponen berikut:

```text
/config
/google_sheets
/domain
/validation
/orchestrator
/frexor
/logging
/ui
/tests
```

Contoh tanggung jawab:

### `google_sheets`
Membaca dan menulis data Sheet.

### `domain`
Model participant, assessment, answer, state.

### `validation`
Memvalidasi data sebelum automation.

### `orchestrator`
Mengatur alur processing.

### `frexor`
Berisi implementasi UI automation Frexor.

### `logging`
Logging dan audit.

### `ui`
UI operator.

### `tests`
Unit/integration tests yang memungkinkan dilakukan tanpa Frexor.

---

# 27. Recommended Processing State Machine

```text
READY
  │
  ▼
VALIDATING
  │
  ├── invalid ───────► ERROR
  │
  ▼
PROCESSING
  │
  ├── recoverable error ─► RETRY
  │
  ├── fatal error ───────► ERROR
  │
  ▼
VERIFYING
  │
  ├── failed ───────────► ERROR
  │
  ▼
DONE
```

Untuk participant dengan beberapa module:

```text
Participant
   ├── DISC  → DONE
   ├── VAK   → ERROR
   └── IQ    → READY

Overall = PARTIAL
```

---

# 28. Security Requirements

Karena data assessment merupakan data yang harus ditangani secara terbatas, aplikasi harus:

- tidak menyimpan password Google secara plaintext di repository;
- tidak menyimpan API/token di source code;
- menggunakan environment variable / secure local credential store untuk secret;
- membatasi akses credential sesuai kebutuhan;
- tidak mengirim jawaban ke service AI eksternal;
- tidak meng-upload screenshot/data peserta ke service publik kecuali memang diperlukan dan disetujui;
- menjaga log agar tidak memuat informasi pribadi lebih dari yang diperlukan.

---

# 29. Performance Requirements

MVP tidak memiliki target throughput yang ekstrem. Prioritas utama adalah **akurasi dan keselamatan data**.

Target perilaku:

- proses peserta secara sequential secara default;
- jangan melakukan parallel processing pada satu instance Frexor kecuali kemudian dibuktikan aman;
- jangan mengorbankan verification hanya demi kecepatan;
- hindari pembukaan ulang aplikasi jika tidak diperlukan;
- reuse Frexor session jika aman dan stabil.

---

# 30. Reliability Requirements

Automation harus lebih memilih **gagal dengan aman** daripada menginput data yang berpotensi salah.

Contoh:

Jika control soal nomor 17 tidak ditemukan:

```text
SALAH:
anggap berhasil → lanjut soal 18 → submit

BENAR:
stop/recover → tandai ERROR → simpan alasan
```

Jika status submit tidak dapat diverifikasi:

```text
JANGAN langsung menulis DONE.
```

---

# 31. Acceptance Criteria — MVP

MVP dinyatakan berhasil jika seluruh kondisi berikut terpenuhi.

## AC-01 Google Sheets

- Sistem dapat terhubung ke Google Sheets.
- Sistem dapat membaca participant data.
- Sistem dapat membaca DISC, VAK, dan IQ answers.
- Sistem dapat mengubah status processing.

## AC-02 Validation

- Data kosong ditolak.
- Data jawaban invalid ditolak.
- DISC harus lengkap dua jawaban per soal.
- VAK harus lengkap satu jawaban per soal.
- IQ harus lengkap satu jawaban per soal.

## AC-03 DISC

- Sistem dapat mengisi `Mirip`.
- Sistem dapat mengisi `Tidak Mirip`.
- Sistem mengisi soal sesuai question number.
- Sistem dapat submit DISC.
- Sistem hanya menandai DISC `DONE` setelah submit terverifikasi.

## AC-04 VAK

- Sistem dapat mengisi satu pilihan per soal.
- Sistem dapat submit VAK.
- Sistem hanya menandai VAK `DONE` setelah submit terverifikasi.

## AC-05 IQ

- Sistem dapat mengisi satu pilihan per soal.
- Sistem dapat submit IQ.
- Sistem hanya menandai IQ `DONE` setelah submit terverifikasi.

## AC-06 Resume

Jika DISC sudah `DONE` tetapi VAK gagal, ketika proses dijalankan ulang:

- DISC tidak diulang;
- VAK dapat di-retry;
- IQ diproses jika statusnya `READY`;
- hasil akhirnya diperbarui dengan benar.

## AC-07 Error

Jika sebuah control tidak ditemukan:

- data tidak boleh dianggap sukses;
- error harus tercatat;
- participant/module harus ditandai `ERROR`;
- automation tidak boleh melanjutkan secara buta.

## AC-08 Batch

Sistem dapat memproses beberapa peserta secara berurutan dan melewati participant yang sudah `DONE`.

## AC-09 Logging

Setiap processing cycle dapat ditelusuri berdasarkan participant ID dan module.

---

# 32. Testing Strategy

Testing harus dilakukan bertahap.

## Level 1 — Unit Test

Tanpa membuka Frexor.

Test:

- parsing Sheet;
- validation;
- state transition;
- status calculation;
- retry logic.

## Level 2 — Mock Frexor Adapter

Gunakan fake adapter untuk menguji orchestrator.

Contoh:

```text
FakeFrexorAdapter
→ open_disc() = success
→ fill_disc_question() = success
→ submit_disc() = success
```

Hal ini memungkinkan mayoritas business logic dites tanpa aplikasi Frexor.

## Level 3 — Frexor UI Integration Test

Jalankan pada Windows yang memiliki Frexor.

Test minimal:

- launch;
- navigation;
- field identification;
- DISC input;
- VAK input;
- IQ input;
- submit verification;
- recovery.

## Level 4 — Controlled Real Data Test

Gunakan sejumlah kecil peserta uji yang aman untuk diproses sebelum batch besar.

Jangan langsung menggunakan batch besar saat automation pertama kali dinyalakan.

---

# 33. Diagnostic / Debug Mode

Developer mode harus menyediakan informasi lebih detail mengenai:

- window yang ditemukan;
- control yang ditemukan;
- current module;
- current question;
- action yang sedang dilakukan;
- screenshot saat error jika secara keamanan diperbolehkan secara lokal;
- timing / timeout.

Screenshot diagnostic harus disimpan lokal dan tidak otomatis dikirim ke pihak eksternal.

---

# 34. Unknowns That Must Be Investigated Before Final Implementation

Codex **tidak boleh mengarang detail berikut**. Lakukan discovery pada environment terlebih dahulu.

1. Path dan nama executable Frexor yang sebenarnya.
2. Apakah Frexor membutuhkan login.
3. Apakah login dilakukan setiap kali aplikasi dibuka.
4. Struktur navigasi untuk DISC, VAK, dan IQ.
5. Jumlah soal untuk masing-masing assessment.
6. Jenis control UI setiap jawaban.
7. Cara sistem berpindah antar soal.
8. Apakah semua soal ada dalam satu halaman atau beberapa halaman.
9. Cara submit masing-masing module.
10. Indikator submit berhasil.
11. Apakah ada confirmation dialog.
12. Bagaimana aplikasi menangani duplicate participant.
13. Apakah peserta dipilih berdasarkan ID, nama, atau field lain.
14. Apakah Frexor memerlukan mouse/keyboard foreground.
15. Apakah Frexor dapat digunakan jika window diminimize.
16. Apakah automation dijalankan langsung di server Windows atau workstation operator.
17. Bentuk final Google Sheet yang digunakan di lapangan.
18. Mekanisme authentication Google Sheets yang diperbolehkan di environment target.

Jika informasi tersebut belum tersedia, implementasikan abstraction/mock terlebih dahulu dan tandai discovery item sebagai `BLOCKED` atau `TBD`, bukan menebak.

---

# 35. Recommended Development Order

Codex sebaiknya mengerjakan secara bertahap, bukan langsung membuat seluruh automation UI.

### Phase 1 — Project skeleton

- konfigurasi;
- logging;
- domain model;
- state machine;
- Google Sheets repository interface;
- Frexor adapter interface.

### Phase 2 — Google Sheets

- read participant;
- read DISC/VAK/IQ;
- validation;
- status update.

### Phase 3 — Orchestrator

- participant selection;
- module selection;
- state transition;
- retry;
- resume.

### Phase 4 — Frexor discovery

- inspect UI;
- identify controls;
- document navigation;
- implement adapter.

### Phase 5 — DISC integration

- navigation;
- input two fields;
- submit verification.

### Phase 6 — VAK integration

- navigation;
- single-choice input;
- submit verification.

### Phase 7 — IQ integration

- navigation;
- single-choice input;
- submit verification.

### Phase 8 — Operator UI

- validation;
- start/stop;
- progress;
- retry error.

### Phase 9 — Hardening

- edge cases;
- recovery;
- logging;
- security;
- packaging.

---

# 36. Definition of Done

Fitur dianggap selesai apabila:

- kode tidak menggunakan hardcoded screen coordinates sebagai satu-satunya mekanisme input;
- Google Sheets integration berjalan;
- validation berjalan;
- state machine berjalan;
- DISC, VAK, dan IQ masing-masing memiliki adapter flow yang benar;
- submit dapat diverifikasi;
- status Sheet diperbarui berdasarkan hasil nyata;
- restart tidak mengulang module `DONE`;
- error tercatat;
- retry tidak menyebabkan duplicate processing yang tidak diinginkan;
- automated tests untuk business logic tersedia;
- konfigurasi dan credential dipisahkan dari source code;
- dokumentasi setup tersedia.

---

# 37. Important Implementation Rules for Codex

1. **Jangan mengarang struktur UI Frexor.** Lakukan discovery terlebih dahulu.
2. **Jangan mengubah jawaban dari Google Sheets.** Automation hanya membaca dan memasukkan.
3. **Jangan menandai `DONE` hanya karena tombol submit berhasil diklik.** Harus ada verification.
4. **Jangan mengulang module yang sudah `DONE` pada resume normal.**
5. **Jangan melanjutkan jika state aplikasi tidak diketahui setelah error.**
6. **Jangan membuat koordinat mouse sebagai source of truth.** Gunakan semantic UI control jika memungkinkan.
7. **Jangan memasukkan credential ke repository.**
8. **Jangan membangun OCR/scan dalam proyek ini.**
9. **Jangan menambahkan AI/LLM ke processing flow tanpa requirement yang eksplisit.**
10. **Utamakan correctness dan recoverability dibanding speed.**

---

# 38. Example End-to-End Scenario

## Input

Participant:

```text
ID       : P001
Nama     : Andi
Position : Operator
```

DISC:

```text
Q1 → Mirip A, Tidak Mirip C
Q2 → Mirip B, Tidak Mirip D
...
```

VAK:

```text
Q1 → B
Q2 → A
...
```

IQ:

```text
Q1 → C
Q2 → D
...
```

Initial state:

```text
DISC = READY
VAK  = READY
IQ   = READY
```

## Processing

```text
P001 selected
↓
Validation passed
↓
DISC PROCESSING
↓
DISC submitted + verified
↓
DISC DONE
↓
VAK PROCESSING
↓
VAK submitted + verified
↓
VAK DONE
↓
IQ PROCESSING
↓
IQ submitted + verified
↓
IQ DONE
```

Final state:

```text
DISC = DONE
VAK  = DONE
IQ   = DONE
Overall = DONE
```

---

# 39. Example Failure Scenario

VAK question 17 tidak dapat diakses.

Expected:

```text
DISC = DONE
VAK  = ERROR
IQ   = READY
Overall = PARTIAL / ERROR
```

Log:

```text
ERROR P001 VAK Q17 CONTROL_NOT_FOUND
```

Ketika operator memperbaiki masalah dan menjalankan retry:

```text
DISC → SKIP
VAK  → RETRY
IQ   → PROCESS
```

Tidak ada pengulangan DISC.

---

# 40. Final Product Principle

Produk ini bukan sistem assessment baru.

Produk ini adalah **data-entry automation layer** dengan alur inti:

```text
Google Sheets
      ↓
Validation
      ↓
Orchestration
      ↓
Frexor UI Automation
      ↓
Verification
      ↓
Status Update
```

Prioritas utama:

1. **Accuracy** — jawaban yang dimasukkan harus sama dengan data sumber.
2. **Safety** — jangan melanjutkan dalam kondisi UI yang tidak diketahui.
3. **Traceability** — setiap processing dapat dilacak.
4. **Recoverability** — proses dapat dilanjutkan tanpa mengulang modul yang sudah selesai.
5. **Maintainability** — UI automation Frexor dipisahkan dari business logic.
6. **Simplicity** — jangan menambah komponen yang tidak diperlukan oleh kebutuhan nyata.

---

# 41. Immediate Next Steps for Codex

Sebelum mengimplementasikan Frexor automation secara penuh, Codex harus melakukan langkah berikut:

### Step 1
Buat project skeleton dan domain model.

### Step 2
Buat Google Sheets repository dengan mock/test data.

### Step 3
Implementasikan validation dan state machine.

### Step 4
Buat `FrexorAdapter` interface dan `MockFrexorAdapter`.

### Step 5
Jalankan discovery terhadap Frexor `.exe` pada Windows target dan dokumentasikan:

- window hierarchy;
- control types;
- labels/automation IDs;
- navigation;
- submit verification;
- failure states.

### Step 6
Setelah discovery cukup, implementasikan adapter DISC, kemudian VAK, kemudian IQ.

### Step 7
Baru integrasikan seluruh flow dengan Google Sheets dan operator UI.

---

# 42. Open Decisions

Item berikut belum diputuskan dan harus dikonfirmasi sebelum production deployment:

- struktur kolom final Google Sheets;
- jumlah soal DISC/VAK/IQ;
- nama kolom dan identifier participant yang digunakan Frexor;
- kebutuhan login Frexor;
- lokasi executable Frexor;
- metode UI automation;
- behavior saat error satu peserta terjadi;
- apakah batch harus berhenti pada error atau boleh lanjut;
- mekanisme credential Google;
- retention log;
- kebutuhan screenshot diagnostic;
- apakah automation harus memiliki foreground ownership atas Frexor.

**Jangan mengunci keputusan tersebut berdasarkan asumsi.**

---

## Summary for Implementation Agent

Bangun aplikasi Windows yang membaca data assessment dari Google Sheets dan memasukkannya ke Frexor `.exe`.

Tiga module wajib:

```text
DISC → 2 answers / question:
       Mirip + Tidak Mirip

VAK  → 1 answer / question:
       Multiple Choice

IQ   → 1 answer / question:
       Multiple Choice
```

Gunakan status per module, verification setelah submit, logging, retry terbatas, resume capability, dan abstraction `FrexorAdapter`.

**Jangan mengimplementasikan OCR. Jangan menentukan jawaban. Jangan mengarang UI Frexor. Lakukan discovery terlebih dahulu.**

Target MVP adalah automation yang dapat memproses peserta secara aman dari Google Sheets sampai submit di Frexor, dengan kemampuan melanjutkan proses tanpa mengulang module yang sudah `DONE`.
