# Roadmap PDF Merge and Admin Portal

## 1. Target Outcome

Setelah DISC, VAK, dan IQ selesai, worker menghasilkan satu PDF gabungan dan mengunggahnya ke server. HR/operator membuka dashboard dari perangkat lain dan mengunduh file tanpa membuka VM Windows.

## 2. Delivery Phases

### Phase 0 - Stabilization

- Selesaikan batch dan failure tests.
- Rotasi token yang pernah terekspos.
- Pasang systemd dan Task Scheduler.
- Uji backup restore.

Exit criteria: current flow reliable pada batch dummy.

### Phase 1 - Local PDF Merge (Implemented)

Worker menggunakan `pypdf` untuk menggabungkan arsip PDF lokal.

```text
DISC DONE
VAK DONE
IQ DONE
  -> locate three archived PDFs
  -> merge to temporary file
  -> validate output
  -> atomic rename
```

Output local recommendation:

```text
output/<job_id>_<safe_name>/Hasil Psikotes <DD-MM-YYYY> <posisi> <nama>.pdf
```

Exit criteria:

- Urutan halaman benar.
- Source tidak berubah.
- Corrupt atau missing input menghasilkan controlled error.
- Automated merge tests lulus.

Status: implemented dan lulus automated tests. Pengujian batch nyata tetap diperlukan sebelum production.

### Phase 2 - Server Upload

Endpoint proposed:

```http
POST /api/v1/worker/jobs/{job_id}/result
Authorization: Bearer <worker-token>
X-Worker-ID: <worker-id>
Content-Type: multipart/form-data
```

Multipart fields:

```text
file
sha256
page_count
```

Server responsibilities:

- Verifikasi ownership dan job state.
- Batasi ukuran upload.
- Validasi `%PDF-` dan `%%EOF`.
- Hitung SHA-256 sendiri.
- Simpan temporary lalu atomic move.
- Catat metadata pada `result_files`.
- Return idempotent response untuk checksum sama.

Exit criteria:

- Upload sukses pada LAN.
- Network interruption dapat di-retry.
- File tidak corrupt.
- Duplicate upload tidak menggandakan data.

### Phase 3 - Result API

Endpoints proposed:

```http
GET /api/v1/admin/jobs
GET /api/v1/admin/jobs/{job_id}
GET /api/v1/admin/jobs/{job_id}/result
```

List filters:

```text
status
result_status
test_date_from
test_date_to
name
position
external_id
page
page_size
```

Download response:

```http
Content-Type: application/pdf
Content-Disposition: attachment; filename="Frexor Result <safe identity>.pdf"
```

Exit criteria:

- Pagination.
- Authorization.
- Safe filenames.
- Audit download.

### Phase 4 - Admin/HR Website

Pages:

1. Login.
2. Dashboard summary.
3. Job/result list.
4. Detail status.
5. Review-required queue.
6. Download history.

Browser tidak menerima filesystem path atau service token.

Exit criteria:

- HR dapat download dari perangkat LAN lain.
- VM access tidak diperlukan untuk result retrieval.
- Unauthorized user ditolak.

### Phase 5 - Operations and Governance

- Retention jobs.
- Scheduled deletion.
- Storage monitoring.
- Backup PDF metadata dan files.
- Restore drill.
- Optional antivirus scan.
- Optional object storage migration.

## 3. Recommended State Handling

```text
Modules DONE
  -> MERGING
  -> UPLOAD_PENDING
  -> UPLOADING
  -> AVAILABLE
```

Failures:

```text
MERGE_ERROR
UPLOAD_ERROR
STORAGE_ERROR
CHECKSUM_MISMATCH
```

Retry merge atau upload tidak boleh membuka Frexor atau mengulang module submission.

## 4. Security Requirements

- Result endpoint membutuhkan authenticated HR session.
- Worker token tidak dapat digunakan sebagai dashboard login.
- Files disimpan di luar web root.
- Download melalui authorization handler.
- Audit setiap download sukses.
- Terapkan rate limit dan session expiration.
- Gunakan HTTPS ketika dashboard keluar dari isolated test network.

## 5. Open Decisions

- Dashboard framework dan identity provider.
- Local filesystem versus object storage.
- Retention duration.
- Maximum file size.
- Apakah tiga PDF asli ikut dapat diunduh.
- Apakah merged PDF memiliki cover page.
- Apakah digital signature atau watermark diperlukan.
- Apakah job `DONE` sebelum atau setelah result upload.

Recommended default: simpan source PDF sampai upload terkonfirmasi, expose hanya merged PDF kepada HR, dan gunakan result `AVAILABLE` sebagai completion yang terlihat dashboard.
