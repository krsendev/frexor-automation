# PRD Frexor Automation Platform v3

## 1. Status Dokumen

| Field | Nilai |
|---|---|
| Produk | Frexor Assessment Automation Platform |
| Versi PRD | 3.0 |
| Status | Production candidate, belum production-approved |
| Lingkup | Form website, automation API, Windows worker, hasil PDF, dan dashboard admin |
| Baseline | Implementasi webhook queue dan worker sudah berjalan |

PRD ini menjadi dokumen induk terbaru. PRD v1, v2, desktop operator, dan integration PRD tetap menjadi referensi historis serta detail implementasi tertentu.

## 2. Ringkasan Produk

Platform menerima data tes psikologi dari website form, menyimpannya sebagai antrean pada FastAPI dan SQLite, lalu Windows worker mengendalikan aplikasi Frexor secara otomatis. Frexor menghasilkan PDF DISC, VAK, dan IQ.

Fase berikutnya akan menggabungkan ketiga PDF menjadi satu dokumen, mengunggah hasil gabungan ke server, dan menyediakan dashboard agar HR/operator dapat mengunduh hasil tanpa membuka VM Windows.

```text
Website Form
  -> Automation API
  -> SQLite Queue
  -> Windows Worker
  -> Frexor
  -> DISC.pdf + VAK.pdf + IQ.pdf
  -> Merge
  -> Upload ke Server
  -> Dashboard Admin/HR
```

## 3. Masalah yang Diselesaikan

- Pengisian ulang jawaban dari website ke Frexor memerlukan waktu dan rawan salah.
- Frexor hanya dapat dioperasikan melalui desktop Windows interaktif.
- Job perlu tetap aman ketika worker offline atau jaringan terputus.
- Hasil PDF saat ini berada di VM Windows dan tidak praktis diambil HR.
- Data duplikat dan retry perlu ditangani tanpa membuat proses Frexor ganda.
- Status proses harus dapat dilihat tanpa mengakses langsung SQLite atau VM.

## 4. Tujuan

### 4.1 Tujuan Saat Ini

- Menerima satu submission lengkap melalui webhook.
- Memvalidasi identitas dan 114 jawaban.
- Menyimpan submission secara idempotent.
- Memproses job satu per satu melalui Windows worker.
- Menghasilkan dan memverifikasi tiga PDF Frexor.
- Melindungi proses dengan lease, heartbeat, dan recovery aman.

### 4.2 Tujuan Fase Berikutnya

- Menggabungkan PDF dengan urutan DISC, VAK, IQ.
- Mengunggah PDF gabungan ke server Linux.
- Menyimpan metadata file dan checksum.
- Menyediakan dashboard dengan login dan role.
- Memungkinkan download hasil dari perangkat HR/operator.
- Mencatat audit download dan perubahan status hasil.

## 5. Non-Goals

- Menilai atau menginterpretasikan hasil psikologi.
- Mengubah jawaban peserta.
- Menentukan jawaban otomatis ketika data kosong.
- Memodifikasi source aplikasi Frexor.
- Menjalankan UI Automation tanpa desktop Windows interaktif.
- Menyediakan link PDF publik tanpa autentikasi.
- Menggunakan browser peserta untuk memanggil Automation API secara langsung pada production.

## 6. Pengguna dan Role

### Peserta

- Mengisi form DISC, VAK, dan IQ.
- Tidak mengakses Automation API, worker, atau dashboard admin.

### Backend Website

- Memvalidasi submission.
- Mengubah format internal menjadi payload webhook.
- Menyimpan `external_id` dan `job_id`.

### Windows Worker

- Claim satu job.
- Mengambil jawaban per modul.
- Mengoperasikan Frexor.
- Memverifikasi PDF.
- Menjaga lease melalui heartbeat.
- Pada fase berikutnya: merge dan upload PDF.

### Operator/HR

- Melihat status proses.
- Mengunduh hasil PDF gabungan.
- Tidak perlu login ke VM untuk mengambil file.

### Administrator Sistem

- Mengelola deployment, token, backup, worker, recovery, dan audit.

## 7. Arsitektur Produk

### 7.1 Komponen Aktif

1. Website form dan backend website.
2. FastAPI Automation API pada Linux.
3. SQLite pada host Automation API.
4. Windows worker pada VM dengan desktop interaktif.
5. Aplikasi Frexor.
6. Folder PDF lokal Windows.

### 7.2 Komponen Rencana

1. PDF merge service di worker.
2. Endpoint upload hasil.
3. Penyimpanan hasil di Linux.
4. API dashboard.
5. Website dashboard admin/HR.
6. Audit download dan retensi file.

## 8. Kontrak Submission

Endpoint:

```http
POST /api/v1/webhooks/assessments
Authorization: Bearer <webhook-token>
Content-Type: application/json
```

Payload wajib memiliki:

```text
external_id
name
position
test_date
answers.disc[24]
answers.vak[30]
answers.iq[60]
```

Aturan lengkap berada di `PRD_Website_Frexor_Webhook_Integration_v1.md`.

## 9. Persyaratan Fungsional Aktif

### FR-01 Validasi Submission

- Nama dan posisi wajib, maksimal 20 karakter.
- Tanggal wajib `YYYY-MM-DD`.
- DISC wajib lengkap dan pasangan jawaban berbeda.
- VAK dan IQ wajib lengkap serta sesuai opsi.
- Jawaban kosong ditolak dengan HTTP `422`.

### FR-02 Idempotency

- `external_id` unik untuk satu attempt.
- Retry attempt yang sama mengembalikan job yang sama.
- Duplicate request tidak membuat jawaban atau job kedua.

### FR-03 Queue

- Job baru berstatus `QUEUED`.
- Worker claim secara atomik.
- Satu job hanya dimiliki satu worker aktif.

### FR-04 Lease dan Heartbeat

- Claim menghasilkan lease terbatas.
- Worker aktif memperpanjang lease.
- `CLAIMED` yang kedaluwarsa dapat diantrekan kembali.
- `PROCESSING` yang kedaluwarsa menjadi `REVIEW_REQUIRED`.

### FR-05 Proses Modul

- Urutan eksekusi selalu DISC, VAK, IQ.
- Modul `DONE` tidak diulang.
- Status `DONE` hanya diberikan setelah PDF lokal terverifikasi.

### FR-06 PDF Lokal

- PDF harus baru atau berubah setelah submit.
- Filename harus cocok dengan modul, tanggal, posisi, dan nama.
- PDF harus memiliki struktur dasar yang valid dan ukuran minimum.
- File arsip tidak boleh ditimpa.

## 10. Persyaratan Fungsional Roadmap

### FR-07 Merge PDF

- Input: PDF DISC, VAK, dan IQ yang telah terverifikasi.
- Urutan merge: DISC, VAK, IQ.
- Output tunggal: `Hasil Psikotes <DD-MM-YYYY> <posisi> <nama>.pdf`.
- Merge tidak mengubah tiga file sumber.
- Output diverifikasi dapat dibuka, memiliki page count yang benar, dan checksum SHA-256.
- Jika satu modul belum tersedia, merge tidak dijalankan.

### FR-08 Upload Hasil

- Worker mengunggah file gabungan melalui endpoint worker terautentikasi.
- Upload menggunakan multipart/form-data.
- Server memverifikasi ownership job, lease, PDF, ukuran, dan checksum.
- File ditulis ke temporary file lalu dipindahkan secara atomik.
- Job tidak menjadi final `DONE` sebelum upload terkonfirmasi.

### FR-09 Penyimpanan Server

- PDF disimpan di luar document root.
- Direktori menggunakan `job_id`, bukan nama peserta.
- Metadata file disimpan di SQLite.
- File tidak boleh dapat diakses tanpa endpoint terautentikasi.

### FR-10 Dashboard Admin

- Login individual untuk HR/operator.
- Daftar submission dengan filter status dan tanggal.
- Detail peserta, modul, error, dan ketersediaan hasil.
- Tombol download hanya ketika hasil `AVAILABLE`.
- Audit download mencatat user, waktu, job, modul/hasil, dan IP.

## 11. Model Status

### Job Saat Ini

```text
QUEUED
CLAIMED
PROCESSING
DONE
RETRY_PENDING
FAILED
REVIEW_REQUIRED
```

### Modul Saat Ini

```text
PENDING
PROCESSING
DONE
ERROR
```

### Result Roadmap

```text
PENDING
MERGING
UPLOAD_PENDING
UPLOADING
AVAILABLE
ERROR
```

Status result dibuat terpisah agar kegagalan merge/upload tidak mengubah fakta bahwa tiga modul Frexor mungkin sudah selesai.

## 12. Persyaratan Non-Fungsional

### Reliability

- Transaksi write SQLite menggunakan `BEGIN IMMEDIATE`.
- Claim bersifat atomik.
- Retry tidak menyebabkan duplikasi submission.
- Crash setelah submit tidak boleh otomatis mengirim ulang tanpa pemeriksaan.

### Security

- Webhook token dan worker token berbeda.
- Token hanya berada pada environment/config rahasia.
- API dibatasi firewall LAN.
- Dashboard menggunakan session dan role, bukan worker token.
- PDF dan database tidak berada di document root.

### Privacy

- Log tidak menyimpan jawaban, token, atau payload lengkap.
- Retensi data dan PDF harus disepakati dengan HR.
- Backup wajib dilindungi seperti database utama.

### Performance

- Worker tetap memproses satu job pada satu waktu.
- API harus tetap responsif ketika antrean bertambah.
- Dashboard menggunakan pagination.
- Pengujian beban harus dilakukan sebelum menetapkan kapasitas produksi.

## 13. Status Verifikasi Saat Ini

| Area | Status |
|---|---|
| Validasi schema | Lulus automated test |
| Webhook dan idempotency | Lulus controlled test |
| Claim, heartbeat, dan recovery function | Lulus automated test |
| Worker mock HTTP end-to-end | Lulus |
| Satu participant Frexor nyata | Dilaporkan berhasil |
| Batch banyak participant | Belum diuji memadai |
| Crash saat CLAIMED | Belum diuji operasional |
| Crash saat PROCESSING | Belum diuji operasional |
| Network interruption | Belum diuji |
| Backup dan restore | Backup script diuji, restore operasional belum |
| Task Scheduler/systemd | Belum dinyatakan lulus |
| Merge PDF | Implemented; automated tests lulus, batch nyata belum diuji |
| Upload PDF server | Implemented; automated upload/download test lulus |
| Dashboard download | Belum dibuat |

## 14. Acceptance Criteria Release Saat Ini

- Submission valid menghasilkan job.
- Submission invalid ditolak dengan detail.
- Worker memproses tiga modul berurutan.
- Tiga PDF lokal terverifikasi.
- Status akhir menjadi `DONE`.
- Duplicate `external_id` tidak membuat job kedua.
- Worker lain tidak dapat mengambil job aktif.

## 15. Acceptance Criteria Release PDF Dashboard

- Tiga PDF digabung dalam urutan benar.
- Output merge lulus validasi PDF dan checksum.
- Upload retry tidak membuat file ganda.
- Dashboard menampilkan hasil hanya setelah upload selesai.
- HR dapat mengunduh PDF dari perangkat LAN lain.
- User tanpa role tidak dapat mengunduh file.
- Setiap download tercatat pada audit log.
- VM Windows tidak perlu dibuka untuk mengambil hasil.

## 16. Gate Production

Production approval membutuhkan:

1. Batch test dengan volume representatif.
2. Failure injection untuk crash dan network loss.
3. Backup-restore drill.
4. Auto-start Linux dan Windows.
5. Firewall serta secret rotation.
6. Retention policy.
7. Controlled pilot menggunakan data dummy dan batch kecil.
