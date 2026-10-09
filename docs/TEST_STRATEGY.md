# Test Strategy and Production Readiness

## 1. Current Evidence

- Automated unit/integration suite terakhir: 48 tests lulus.
- API queue flow diuji dari webhook sampai status `DONE` menggunakan mock worker.
- Satu controlled Frexor real flow dilaporkan berhasil.
- Validasi payload website berhasil menolak jawaban DISC kosong atau sama.

Keberhasilan tersebut belum membuktikan kapasitas batch, recovery pada semua timing, atau keamanan operasional production.

## 2. Test Levels

### Unit

- Validation rules.
- State calculation.
- PDF filename dan structure validation.
- Repository mapping.
- Merge order, source preservation, page count, dan idempotent local output.

### API Integration

- Authentication.
- Webhook persistence.
- Idempotency.
- Claim ownership.
- Heartbeat.
- Module transition.
- Lease recovery.
- Future PDF upload/download.

### Worker Mock E2E

- Website-like JSON sampai job `DONE` tanpa membuka Frexor.
- Menjadi smoke test setiap release.

### Frexor Controlled E2E

- Satu dummy.
- Batch kecil.
- Failure injection.
- Resume dan recovery.

## 3. Required Test Matrix

| ID | Scenario | Expected | Status |
|---|---|---|---|
| T01 | Valid one job | Semua modul DONE | Lulus terkontrol |
| T02 | Duplicate external_id | Satu job, response idempotent | Automated lulus |
| T03 | Missing DISC answer | HTTP 422 | Terbukti |
| T04 | Three queued jobs | Sequential, tidak tertukar | Belum |
| T05 | 10 queued jobs | Semua selesai, urutan konsisten | Belum |
| T06 | Worker killed while CLAIMED | Requeue setelah lease | Function test lulus, operasional belum |
| T07 | Worker killed while PROCESSING | REVIEW_REQUIRED | Function test lulus, operasional belum |
| T08 | Network lost during fill | Tidak silent DONE | Belum |
| T09 | Network lost after submit | Tidak auto-resubmit | Belum |
| T10 | API restart with queue | Job tetap ada | Belum |
| T11 | Worker restart | Tidak mengulang DONE | Unit lulus, operasional belum |
| T12 | PDF timeout | Module ERROR | Belum real |
| T13 | Wrong PDF filename | PDF_ASSOCIATION_FAILED | Unit lulus |
| T14 | Multiple changed PDFs | Ditolak | Belum real |
| T15 | Backup restore | Queue/status utuh | Belum |
| T16 | Task Scheduler restart | Satu worker aktif | Belum |
| T17 | systemd restart | API kembali sehat | Belum |

## 4. Batch Test Plan

### Batch 3

- Tiga external ID unik.
- Variasi jawaban valid.
- Worker memproses satu per satu.
- PDF masing-masing participant tidak tertukar.
- Semua status dan attempt count benar.

### Batch 10

- Jalankan setelah batch 3 lulus.
- Catat durasi per participant dan total.
- Catat CPU, memory, ukuran database, dan error.
- Jangan memakai data peserta nyata.

### Soak Test

- Worker menunggu antrean minimal 2 jam.
- Kirim job pada beberapa interval.
- Pastikan polling tidak membuat memory leak atau duplicate claim.

## 5. Failure Injection Plan

### CLAIMED Crash

1. Job diklaim.
2. Hentikan worker sebelum status modul `PROCESSING`.
3. Tunggu atau pendekkan lease pada environment test.
4. Trigger claim worker baru.
5. Pastikan attempt bertambah dan job aman diproses.

### PROCESSING Crash

1. Mulai DISC.
2. Hentikan worker setelah sebagian input.
3. Tunggu lease expired.
4. Pastikan `REVIEW_REQUIRED`.
5. Pastikan worker lain tidak mengulang otomatis.

### Post-Submit Crash

1. Biarkan Frexor membuat PDF.
2. Hentikan worker sebelum status tersimpan.
3. Restart worker.
4. Pastikan archive recovery digunakan atau job meminta review; submit tidak boleh terjadi dua kali.

## 6. PDF Merge and Upload Tests

- Merge order DISC, VAK, IQ. Automated lulus.
- Source PDFs tetap ada. Automated lulus.
- Page count output sama dengan total input. Automated lulus.
- Corrupt source ditolak. Automated lulus.
- Missing source ditolak. Automated lulus.
- Existing output valid digunakan kembali. Automated lulus.
- SHA-256 stabil untuk file yang sama.
- Upload interruption dapat diulang.
- Duplicate upload checksum sama tidak membuat file baru.
- Checksum berbeda memicu review atau error.

## 7. Dashboard Tests

- User tanpa login ditolak.
- Role non-HR tidak dapat download.
- Job tanpa hasil tidak memiliki tombol download aktif.
- Download menghasilkan PDF valid.
- Filename response aman.
- Audit record dibuat sekali per download.
- Pagination dan filter bekerja pada volume uji.

## 8. Exit Criteria Production

- T01-T17 critical path lulus.
- Batch 10 dummy selesai tanpa data tertukar.
- Backup restore berhasil.
- Tidak ada secret pada Git atau log.
- Worker hanya satu instance.
- Recovery manual didokumentasikan dan dipahami operator.
- Security review untuk dashboard dan file selesai.
