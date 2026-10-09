# Frexor Assessment Automation

Dokumentasi project lengkap dimulai dari `docs/PROJECT_DOCUMENTATION_INDEX.md`. Requirement induk terbaru berada di `PRD/PRD_Frexor_Automation_Platform_v3.md`.

Aplikasi Windows untuk memindahkan jawaban assessment dari Google Sheets, workbook Excel lokal, atau API ke Frexor secara sequential, tervalidasi, dapat dilanjutkan, dan dapat diaudit. Aplikasi tidak melakukan OCR, scoring, interpretasi, atau pembuatan jawaban.

## Cakupan yang sudah diimplementasikan

- DISC: 24 soal, jawaban `Mirip` dan `Tidak Mirip`, opsi A-D.
- VAK: 30 soal, satu jawaban, opsi A-C.
- IQ: 60 soal, satu jawaban; opsi divalidasi per struktur soal pada PDF.
- Sumber data dapat dipilih antara Google Sheets, workbook Excel lokal, dan API; pilihan tersimpan dalam konfigurasi operator.
- PDF hasil menjadi syarat `DONE`: file harus baru/berubah setelah submit, stabil, terbaca, berukuran minimum, dan memiliki struktur PDF dasar yang valid.
- PDF diarsipkan tanpa overwrite ke `output/<participant_id>_<name>/<MODULE>.pdf`.
- Setelah ketiga modul lengkap, PDF digabung atomik dalam urutan DISC, VAK, IQ menjadi `Hasil Psikotes <DD-MM-YYYY> <posisi> <nama>.pdf`; tiga file sumber tetap disimpan.
- Retry request Google API memakai exponential backoff bawaan client dan batas `max_retries` dari konfigurasi.
- Dry-run validation, batch processing, safe stop, retry error, dan resume tanpa mengulang modul `DONE`.
- Submit baru ditandai `DONE` setelah adapter menemukan perubahan halaman dan PDF modul berhasil diverifikasi.
- Mock adapter dan automated tests untuk business logic.
- Adapter Windows berbasis Microsoft UI Automation melalui `pywinauto`.
- Desktop UI PySide6 untuk operator, dengan Beranda, Proses, Peserta, Hasil, Pengaturan, setup pertama, preflight, safe stop, resume metadata, dan pesan error Bahasa Indonesia.

Ketiga form sudah dipetakan dari foto UI:

- `IMG_20261003_102859.jpg`: DISC, 24 soal dan 48 input.
- `IMG_20261003_122458.jpg`: VAK, 30 soal dan 30 input.
- `IMG_20261003_122444.jpg`: IQ, 60 soal dan 60 input.

Semua form memiliki Nama, Posisi, Tanggal, tombol `Kembali`, dan tombol `Kirim`. Adapter memakai control UIA berdasarkan label dan urutan visible `Edit`, bukan koordinat layar. Runtime berhenti jika jumlah control tidak sesuai.

Saat Frexor masih berada pada halaman login, automation mendeteksi tiga field dan tombol `LOG IN`. Credential tidak disimpan atau diisi oleh automation. Jika field sudah terisi oleh Frexor, tombol login ditekan otomatis; jika belum, proses berhenti agar operator login terlebih dahulu.

Setelah `Kirim`, Frexor tetap pada form dan menampilkan dialog `Perhatian` dengan pesan `Hasil Tes sudah disimpan di ...` serta tombol `OK`. Automation memvalidasi pesan tersebut, menekan `OK`, menunggu PDF pada folder modul, lalu memfokuskan kembali Frexor jika Edge membuka PDF pada tab baru.

Control tree DISC, VAK, IQ, dialog setelah submit, dan struktur folder PDF sudah dikonfirmasi. Tahap berikutnya adalah controlled integration test dengan peserta dummy sebelum penggunaan produksi.

## Setup Windows

1. Untuk development, install Python 3.11 atau lebih baru. Operator produksi menggunakan `.exe` hasil packaging dan tidak perlu Python.
2. Buat virtual environment dan install project:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -e ".[worker]"
Copy-Item config.example.toml config.toml
Copy-Item frexor_ui_map.example.toml frexor_ui_map.toml
```

3. Pilih sumber data pada setup pertama aplikasi: Google Sheets, Excel lokal, atau API.
4. Untuk Google Sheets, buat service account, aktifkan Google Sheets API, simpan JSON credential secara lokal, lalu share spreadsheet kepada email service account sebagai Editor.
5. Jangan commit credential, token API, atau `config.toml`. Konfigurasi operator tersimpan di `%APPDATA%\FrexorAssessmentAutomation`.

## Format Data

Google Sheets dan workbook Excel memakai empat sheet dengan struktur yang sama. Import file di `templates/` dan pertahankan header berikut.

`Participants`:

```text
participant_id,name,position,overall_status,disc_status,vak_status,iq_status,test_date,last_processed_at,last_error,error_code,attempt_count,pdf_status,pdf_path
```

`DISC`: `participant_id,question_no,mirip,tidak_mirip`

`VAK` dan `IQ`: `participant_id,question_no,answer`

Gunakan huruf kapital untuk jawaban. Loader juga menormalisasi input menjadi kapital. Status awal peserta baru adalah `READY` untuk overall dan ketiga modul.
`test_date` wajib berformat `YYYY-MM-DD` dan berisi tanggal peserta mengerjakan tes.

Untuk mode otomatis berbasis API, frontend mengirim assessment ke server queue dan worker Windows memakai endpoint terpisah:

```text
POST  /api/v1/webhooks/assessments
GET   /api/v1/jobs/{job_id}
POST  /api/v1/worker/jobs/claim
GET   /api/v1/worker/jobs/{job_id}/answers/{module}
PATCH /api/v1/worker/jobs/{job_id}/modules/{module}
POST  /api/v1/worker/jobs/{job_id}/heartbeat
POST  /api/v1/worker/jobs/{job_id}/result
GET   /api/v1/admin/jobs/{job_id}/result
```

Webhook dan worker memakai bearer token yang berbeda. Endpoint upload memakai token worker. Endpoint download sementara memakai token webhook dan hanya boleh dipanggil backend web admin; jangan menaruh token tersebut di JavaScript browser.

Data sintetis untuk controlled integration test tersedia di `.test-data/dummy/`. Jangan gunakan fixture tersebut untuk interpretasi psikologis atau keputusan karyawan.

`pdf_status` dimulai dari `PENDING`, berubah menjadi `PARTIAL` setelah sebagian hasil tersedia, `VERIFIED` setelah seluruh modul selesai dan hasil gabungan valid, atau `ERROR` jika verifikasi/merge PDF gagal. Setelah selesai, `pdf_path` menunjuk file `Hasil Psikotes <DD-MM-YYYY> <posisi> <nama>.pdf`.

## Konfigurasi PDF

Isi bagian `[pdf]` di `config.toml`:

- `base_directory`: `Documents\Frexor PAS`, yang memiliki subfolder `DISC`, `VAK`, dan `IQ`;
- `output_directory`: direktori arsip terkelola automation;
- `timeout_seconds`: batas tunggu hasil setelah `Kirim`;
- `stable_seconds`: waktu ukuran/mtime file harus stabil;
- `minimum_size_bytes`: ukuran minimum untuk menolak file kosong/rusak.

Automation mengambil snapshot pada folder modul sebelum submit. Hanya satu PDF baru atau berubah yang boleh muncul. Filename wajib mengikuti `Hasil <MODULE> <YYYY-MM-DD> <posisi> <nama>.pdf`. Lebih dari satu kandidat atau filename yang tidak cocok menghasilkan `PDF_ASSOCIATION_FAILED`.

## Perintah

```powershell
# Hanya membaca dan memvalidasi sumber data aktif; Frexor tidak dibuka.
frexor-automation --config config.toml validate

# Memproses READY/PARTIAL dan melewati modul DONE.
frexor-automation --config config.toml run

# Menyertakan modul ERROR untuk retry, tetap melewati DONE.
frexor-automation --config config.toml retry-errors

# Worker API permanen; claim dan proses satu job pada satu waktu.
frexor-automation --config config.toml worker

# UI operator.
frexor-automation --config config.toml ui
```

Jalankan API Linux dengan environment variable dari `.env.frexor.example`:

```bash
frexor-api
```

Panduan deployment lengkap berada di `docs/PRODUCTION_DEPLOYMENT.md`.

Pada build produksi, operator membuka `Frexor Assessment Automation.exe`. Konfigurasi tersimpan di `%APPDATA%\FrexorAssessmentAutomation` dan setup pertama tampil otomatis.

Untuk uji alur tanpa Frexor, pertahankan `adapter = "mock"`. Mock menguji plumbing dan status, tetapi tidak membuktikan integrasi UI Frexor.

## Discovery Frexor

Jalankan Frexor pada desktop Windows, buka halaman yang relevan, lalu inspeksi control tree:

```powershell
py scripts\inspect_frexor.py --title "^Frexor Psychology Assessment System$" --depth 10
```

Foto layar membantu memahami layout, tetapi tidak menampilkan `auto_id`, `control_type`, atau urutan control UIA. Catat untuk participant, DISC, VAK, dan IQ:

- title, `auto_id`, `control_type`, dan hierarchy control;
- cara navigasi dan pagination;
- selector setiap pilihan jawaban;
- tombol submit dan dialog konfirmasi;
- indikator sukses deterministik dan lokasi PDF yang dihasilkan;
- perilaku saat participant sudah ada atau aplikasi crash.

Mapping `form_title`, urutan visible `Edit`, dan dialog setelah `Kirim` sudah dikonfirmasi melalui UIA. `discovery_complete` kini aktif; tetap lakukan pengujian satu participant dummy sebelum batch lebih besar.

## Tests

```powershell
py -m unittest discover -s tests -v
```

Test integration nyata wajib dijalankan bertahap di Windows: launch/connect, satu modul dengan data dummy, verifikasi submit, recovery, satu participant lengkap, lalu batch kecil terkontrol.

## Build Windows

Jalankan pada Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Output executable berada di `dist\Frexor Assessment Automation\Frexor Assessment Automation.exe`. Installer `Setup.exe`, code signing, dan shortcut Start Menu/Desktop merupakan langkah deployment setelah executable lolos integration test Frexor.

## Safety

- Proses berhenti pada batas aman antar modul atau participant setelah tombol Stop ditekan.
- Error input menghentikan participant tersebut; modul setelahnya tetap `READY`.
- Status `PROCESSING` yang tertinggal setelah crash diubah menjadi `ERROR` dengan kode `INTERRUPTED_REVIEW_REQUIRED`; operator harus memeriksa Frexor sebelum menjalankan retry.
- Kegagalan verifikasi submit menghasilkan `ERROR`, bukan `DONE`.
- `DONE` memerlukan PDF terverifikasi; klik `Kirim` saja tidak cukup.
- Batch berhenti pada error secara default (`continue_after_participant_error = false`).
- Jika proses crash setelah PDF diarsipkan tetapi sebelum status Sheet tersimpan, resume memulihkan status dari arsip PDF tervalidasi tanpa submit ulang.
- Log lokal berada di `logs/automation.log` dan tidak memuat jawaban atau nama peserta.
- File credential, konfigurasi lokal, log, dan diagnostics diabaikan oleh Git.
