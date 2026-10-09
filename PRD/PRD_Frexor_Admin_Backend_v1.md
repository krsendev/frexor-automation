# PRD Frexor Admin Backend v1

## 1. Ringkasan

Backend web admin menyediakan akses terautentikasi bagi HR/operator untuk melihat status assessment dan mengunduh PDF hasil psikotes tanpa membuka Windows VM. Backend admin berkomunikasi dengan Frexor Automation API melalui HTTP dan dapat dibuat memakai bahasa pemrograman apa pun.

```text
Browser HR
  -> Backend Web Admin
  -> Frexor Automation API
  -> SQLite metadata + Linux result storage
```

Browser tidak boleh memanggil Automation API secara langsung dan tidak boleh menerima bearer token internal.

## 2. Tujuan

- Menampilkan daftar assessment dan status pemrosesannya.
- Menampilkan detail peserta, modul, error, dan ketersediaan hasil.
- Mengunduh merged PDF dengan nama terkontrol.
- Membatasi akses berdasarkan user dan role.
- Mencatat siapa yang mengunduh hasil dan kapan.
- Menangani API timeout/error tanpa menampilkan secret atau path server.

## 3. Di Luar Scope v1

- Mengubah jawaban peserta.
- Menjalankan automation secara manual dari dashboard.
- Scoring atau interpretasi psikologis.
- Menampilkan filesystem path Linux atau Windows.
- Menyimpan worker token pada backend admin.
- Akses browser langsung ke Frexor Automation API.

## 4. Aktor dan Role

| Role | Kemampuan minimum |
|---|---|
| HR/Operator | Melihat job yang diizinkan dan mengunduh hasil tersedia |
| Supervisor | Seluruh kemampuan HR serta melihat job gagal/review |
| System Admin | Mengelola user, konfigurasi, dan audit; tidak otomatis berhak membaca hasil jika kebijakan melarang |

Prinsip default: deny. User tanpa role yang sesuai menerima `403`.

## 5. Arsitektur Bahasa-Agnostik

Backend admin boleh memakai PHP, Node.js, Go, Java, .NET, Ruby, atau teknologi lain karena integrasi hanya membutuhkan:

- HTTP client;
- request/response JSON;
- streaming response PDF;
- bearer authentication server-to-server;
- session authentication untuk browser;
- database aplikasi admin bila user/audit disimpan terpisah.

Backend admin tidak mengimpor module Python, tidak membaca SQLite automation secara langsung, dan tidak mengakses folder result melalui network share.

## 6. Fitur Saat Ini dan Target

### Sudah Tersedia

- `GET /api/v1/jobs/{job_id}` untuk status satu job.
- `GET /api/v1/admin/jobs/{job_id}/result` untuk download PDF.
- Metadata `result.available`, filename, checksum, size, dan waktu upload pada status job.
- File result disimpan di server Linux, bukan sebagai SQLite BLOB.

### Masih Harus Dibangun

- Endpoint list/filter/pagination job admin.
- Credential khusus backend admin; sementara download memakai webhook token.
- Login, session, role, dan user management pada web admin.
- Audit download.
- Endpoint detail admin yang tidak bergantung pada website submission owner.
- Kebijakan retention dan penghapusan result.

## 7. Halaman Minimum

### Login

- Username/email dan password atau identity provider perusahaan.
- Session cookie `HttpOnly`, `Secure` pada HTTPS, dan `SameSite=Lax` atau lebih ketat.
- Rate limit login dan lockout terkontrol.

### Dashboard

- Jumlah `QUEUED`, `PROCESSING`, `DONE`, `FAILED`, dan `REVIEW_REQUIRED`.
- Jumlah hasil tersedia.
- Informasi worker terakhir aktif bila endpoint monitoring tersedia.

### Daftar Assessment

Kolom minimum:

- tanggal tes;
- external ID;
- nama;
- posisi;
- status job;
- status DISC/VAK/IQ;
- result tersedia/tidak;
- updated time;
- aksi detail/download.

### Detail Assessment

- identitas dan tanggal tes;
- status setiap modul;
- attempt count;
- error code/message yang sudah disanitasi;
- metadata result;
- tombol download hanya ketika `result.available=true`.

### Review Queue

- Job `FAILED` dan `REVIEW_REQUIRED`.
- Tidak menyediakan tombol retry otomatis sampai prosedur recovery didefinisikan.

## 8. Endpoint Automation API Target

### List Jobs

```http
GET /api/v1/admin/jobs?status=DONE&page=1&page_size=25
Authorization: Bearer <admin-service-token>
```

Filter target:

```text
status
result_available
test_date_from
test_date_to
external_id
name
position
page
page_size
```

### Job Detail

```http
GET /api/v1/admin/jobs/{job_id}
Authorization: Bearer <admin-service-token>
```

### Download Result

```http
GET /api/v1/admin/jobs/{job_id}/result
Authorization: Bearer <admin-service-token>
```

Catatan transisi: code saat ini memakai webhook token untuk status/download. Sebelum production dashboard, buat `FREXOR_ADMIN_TOKEN` terpisah atau gunakan identity-aware gateway. Jangan memakai worker token.

## 9. Kontrak Backend Admin ke Browser

Browser berkomunikasi dengan backend admin milik website, misalnya:

```http
GET /admin/api/assessments
GET /admin/api/assessments/{job_id}
GET /admin/api/assessments/{job_id}/download
```

Backend admin kemudian memanggil Automation API. Endpoint browser menggunakan session user, bukan bearer token Frexor.

Untuk download, backend admin harus meneruskan body PDF sebagai stream dan menetapkan:

```http
Content-Type: application/pdf
Content-Disposition: attachment; filename="<safe filename>.pdf"
Cache-Control: private, no-store
```

Backend tidak mengembalikan `storage_path`, worker token, webhook token, atau stack trace.

## 10. Aturan Status UI

| API status | Tampilan |
|---|---|
| `QUEUED` | Menunggu worker |
| `CLAIMED` | Diambil worker |
| `PROCESSING` | Sedang diproses |
| `DONE` + result tersedia | Selesai, download aktif |
| `FAILED` | Gagal, tampilkan referensi error |
| `REVIEW_REQUIRED` | Perlu pemeriksaan operator |

Jangan menganggap `DONE` cukup jika `result.available` bukan `true`.

## 11. Error Handling

| Automation API | Respons backend admin |
|---|---|
| `401` | Catat configuration/auth failure; browser menerima `502` generik |
| `403` | Browser menerima `403` jika masalah role lokal; upstream `403` dicatat sebagai integrasi gagal |
| `404` | Tampilkan assessment/result tidak ditemukan |
| `409` | Tampilkan state belum mengizinkan operasi |
| `422` | Catat contract mismatch; jangan retry otomatis |
| `5xx` | `502/503`, correlation ID, retry terbatas untuk request idempotent |
| Timeout | `504`, tidak menyimpulkan file hilang |

Download yang terputus boleh dicoba ulang karena operasi bersifat read-only.

## 12. Security Requirements

- Secret hanya berada pada environment/secret manager backend.
- Browser tidak pernah menerima internal bearer token.
- Semua endpoint admin memerlukan login dan authorization role.
- Gunakan HTTPS jika trafik melewati jaringan yang tidak sepenuhnya terisolasi.
- Terapkan CSRF protection pada operasi browser berbasis cookie.
- Validasi `job_id`; jangan menerima path file dari browser.
- PDF dikirim melalui endpoint authorization, bukan static public directory.
- Log tidak boleh berisi jawaban psikotes, token, atau isi PDF.
- Audit minimal menyimpan user ID, job ID, timestamp, IP, outcome, dan correlation ID.
- Batasi concurrency dan ukuran respons; jangan memuat banyak PDF ke memory sekaligus.

## 13. Data yang Disimpan Backend Admin

Backend admin tidak wajib menyalin PDF. Data minimum yang boleh disimpan:

- relasi user/session;
- mapping submission lokal ke `job_id`;
- cache metadata job dengan TTL pendek bila diperlukan;
- audit download;
- correlation ID request.

Automation API tetap menjadi source of truth untuk status automation dan result file.

## 14. Non-Functional Requirements

- List endpoint menggunakan pagination, default 25, maksimum 100.
- Timeout status/list disarankan 5-10 detik.
- Timeout download disarankan 60-120 detik sesuai ukuran file dan LAN.
- Retry otomatis hanya untuk GET atau request idempotent, maksimal 2-3 kali dengan backoff.
- Semua timestamp API menggunakan ISO 8601 UTC; UI boleh mengubah ke `Asia/Jakarta`.
- Nama file download mempertahankan format `Hasil Psikotes DD-MM-YYYY <posisi> <nama>.pdf`.

## 15. Acceptance Criteria

- User tanpa login menerima `401` atau diarahkan ke login.
- User tanpa role menerima `403`.
- Daftar menggunakan pagination dan filter tidak mengubah data.
- Tombol download hanya aktif saat result tersedia.
- Download menghasilkan PDF valid dengan filename benar.
- Token internal tidak terlihat pada browser network response, HTML, atau JavaScript bundle.
- Path storage tidak terlihat pada response browser.
- Setiap download sukses/gagal tercatat pada audit.
- Gangguan Automation API menghasilkan pesan terkontrol dan correlation ID.
- Backend admin yang dibuat dengan bahasa berbeda lulus contract test yang sama.

## 16. Production Gate

- Admin service token terpisah tersedia.
- Authentication dan authorization diuji.
- Audit download aktif.
- Batch/list test minimal 1000 metadata job.
- Concurrent download test dilakukan sesuai jumlah operator.
- Backup dan restore metadata serta result storage diuji.
- Retention policy disetujui HR/IT/legal.
- Tidak ada secret atau data psikotes pada repository dan log.
