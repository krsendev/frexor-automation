# PRD Website to Frexor Webhook Integration v1

## 1. Ringkasan

Website psikotes menerima jawaban peserta melalui form internal, lalu backend website harus mengubah data tersebut menjadi kontrak JSON Frexor Automation API. Backend website menjadi satu-satunya komponen website yang boleh mengetahui webhook token.

Alur target:

```text
Browser peserta
  -> Backend website
  -> Frexor Automation API
  -> SQLite queue
  -> Windows worker
  -> Frexor
```

Integrasi browser langsung ke Frexor Automation API tidak termasuk solusi production. Browser hanya berkomunikasi dengan backend website.

## 2. Latar Belakang Masalah

Frontend saat ini mengirim data internal berikut ke backend website:

```text
id_peserta
csrf_token
jawaban (JSON dalam bentuk string)
```

Backend website sudah mencoba meneruskan data ke webhook, tetapi Frexor Automation API mengembalikan HTTP `422`. Masalah yang sudah ditemukan:

1. VAK dan IQ dipetakan memakai key `answers`, sedangkan webhook mewajibkan `answer`.
2. Backend membaca `$ans['answers']`, sedangkan frontend mengirim `$ans['answer']`.
3. Backend selalu mengembalikan HTTP `200` kepada frontend walaupun webhook mengembalikan `422`.
4. Webhook token ditulis langsung dalam source code PHP dan sudah terekspos. Token lama wajib dicabut dan diganti.
5. Payload debug berisi identitas dan seluruh jawaban serta disimpan pada direktori aplikasi.
6. `external_id` memakai ID peserta, sehingga tes ulang peserta berpotensi dianggap sebagai submission duplikat.
7. Belum ada validasi lokal untuk jumlah jawaban, nomor soal, nama, posisi, dan pilihan jawaban sebelum webhook dipanggil.

## 3. Tujuan

Backend website harus:

- menerima submission form internal;
- memvalidasi session dan CSRF;
- mengambil profil serta metadata soal dari database website;
- membentuk payload webhook yang valid;
- mengirim payload sebagai `application/json`;
- menyimpan `job_id` dari Frexor Automation API;
- meneruskan status HTTP dan detail error yang tepat kepada frontend;
- tidak mengekspos token atau jawaban psikotes melalui browser, source code, maupun file debug publik;
- mendukung retry idempotent tanpa membuat job baru.

## 4. Di Luar Scope

PRD ini tidak mencakup:

- perubahan automation UI Frexor;
- upload PDF dari Windows worker ke Linux;
- website dashboard HR;
- scoring atau interpretasi hasil psikologi;
- perubahan soal dan opsi jawaban;
- akses browser langsung ke Frexor Automation API.

## 5. Aktor dan Komponen

### 5.1 Browser Peserta

- Mengirim jawaban ke backend website.
- Tidak mengetahui Automation API URL internal.
- Tidak mengetahui webhook token.

### 5.2 Backend Website

- Memvalidasi peserta, session, CSRF, dan jawaban.
- Melakukan transformasi payload.
- Memanggil webhook secara server-to-server.
- Menyimpan relasi submission dengan `job_id`.

### 5.3 Frexor Automation API

- Memvalidasi payload dengan Pydantic.
- Menyimpan job dan jawaban ke SQLite.
- Mengembalikan `job_id` dan status antrean.

## 6. Endpoint Automation API

```http
POST /api/v1/webhooks/assessments
Authorization: Bearer <FREXOR_WEBHOOK_TOKEN>
Content-Type: application/json
Accept: application/json
```

Contoh URL LAN:

```text
http://192.168.20.45:8000/api/v1/webhooks/assessments
```

URL wajib berasal dari environment variable dan tidak boleh ditulis langsung dalam source code.

## 7. Konfigurasi Environment Backend Website

Gunakan environment variable:

```env
FREXOR_API_URL=http://192.168.20.45:8000
FREXOR_WEBHOOK_TOKEN=replace-with-new-secret
```

Persyaratan:

- Token lama yang pernah ditulis pada source code wajib diganti.
- Webhook token dan worker token harus berbeda.
- File environment tidak boleh masuk Git.
- Token tidak boleh dicetak pada log atau response frontend.
- Aplikasi harus gagal saat startup/request jika konfigurasi wajib tidak tersedia.

## 8. Kontrak Payload Webhook

```json
{
  "external_id": "SPR003-ATTEMPT-001",
  "name": "Nama Peserta",
  "position": "Operator",
  "test_date": "2026-10-08",
  "answers": {
    "disc": [
      {
        "question_no": 1,
        "mirip": "A",
        "tidak_mirip": "B"
      }
    ],
    "vak": [
      {
        "question_no": 1,
        "answer": "A"
      }
    ],
    "iq": [
      {
        "question_no": 1,
        "answer": "A"
      }
    ]
  }
}
```

Array pada contoh dipersingkat. Payload aktual wajib memiliki 24 DISC, 30 VAK, dan 60 IQ.

## 9. Aturan Validasi

### 9.1 Identitas

| Field | Aturan |
|---|---|
| `external_id` | String unik untuk satu attempt, panjang 1-100 |
| `name` | String non-kosong, maksimal 20 karakter |
| `position` | String non-kosong, maksimal 20 karakter |
| `test_date` | Tanggal pengerjaan peserta, format `YYYY-MM-DD` |

Nama dan posisi tidak boleh dipotong diam-diam. Jika melebihi 20 karakter, backend mengembalikan validasi yang dapat dipahami pengguna/operator.

### 9.2 DISC

- Tepat 24 item.
- `question_no` lengkap 1 sampai 24.
- Tidak ada nomor duplikat.
- `mirip` dan `tidak_mirip` hanya `A`, `B`, `C`, atau `D`.
- `mirip` tidak boleh sama dengan `tidak_mirip`.

### 9.3 VAK

- Tepat 30 item.
- `question_no` lengkap 1 sampai 30.
- Tidak ada nomor duplikat.
- Key jawaban harus bernama `answer`.
- Nilai hanya `A`, `B`, atau `C`.

### 9.4 IQ

- Tepat 60 item.
- `question_no` lengkap 1 sampai 60.
- Tidak ada nomor duplikat.
- Key jawaban harus bernama `answer`.
- Nomor 12, 24, 44, dan 56 hanya menerima A-C.
- Nomor 15 dan 54 menerima A-H.
- Nomor lainnya menerima A-E.

Semua jawaban dinormalisasi menjadi huruf kapital sebelum dikirim.

## 10. Mapping Data Website

Input internal frontend:

```json
{
  "id_soal": "53",
  "kategori": "DISC",
  "mirip": "A",
  "tidak_mirip": "B"
}
```

`id_soal` adalah primary key database dan tidak boleh langsung digunakan sebagai `question_no`. Backend mengambil nomor soal relatif dari metadata database.

Query metadata harus menghasilkan:

```text
id_soal
kategori: DISC | VAK | IQ
nomor_urut: nomor relatif dalam kategori
```

Jika `id_kategori` berupa foreign key, query wajib melakukan join ke tabel kategori. Jangan membandingkan angka foreign key dengan string `DISC`, `VAK`, atau `IQ`.

Contoh query konseptual:

```sql
SELECT
    s.id_soal,
    k.nama_kategori AS kategori,
    s.nomor_urut
FROM soal AS s
JOIN kategori AS k
    ON k.id_kategori = s.id_kategori;
```

Hasil metadata wajib memenuhi:

```text
DISC: MIN=1, MAX=24, COUNT=24
VAK:  MIN=1, MAX=30, COUNT=30
IQ:   MIN=1, MAX=60, COUNT=60
```

## 11. Mapping PHP Wajib

Mapping jawaban harus menggunakan bentuk berikut:

```php
if ($kategori === 'DISC') {
    $discAnswers[] = [
        'question_no' => $nomorUrut,
        'mirip' => strtoupper(trim($answer['mirip'] ?? '')),
        'tidak_mirip' => strtoupper(trim($answer['tidak_mirip'] ?? '')),
    ];
} elseif ($kategori === 'VAK') {
    $vakAnswers[] = [
        'question_no' => $nomorUrut,
        'answer' => strtoupper(trim($answer['answer'] ?? '')),
    ];
} elseif ($kategori === 'IQ') {
    $iqAnswers[] = [
        'question_no' => $nomorUrut,
        'answer' => strtoupper(trim($answer['answer'] ?? '')),
    ];
}
```

Penggunaan berikut dilarang karena tidak sesuai kontrak:

```php
'answers' => $answer['answers']
```

## 12. Idempotency dan Attempt

`external_id` harus mewakili satu pengerjaan, bukan hanya satu peserta.

Disarankan menambahkan tabel submission/attempt website dengan primary key permanen:

```text
assessment_attempt_id
participant_id
frexor_job_id
frexor_status
submitted_at
completed_at
last_error
```

Contoh `external_id`:

```text
SPR003-ATTEMPT-001
```

Retry untuk attempt yang sama wajib memakai `external_id` yang sama. Jangan membuat ID berbasis timestamp baru pada setiap retry.

## 13. Pengiriman HTTP dari PHP

Persyaratan:

- Gunakan `json_encode` dengan `JSON_THROW_ON_ERROR`.
- Gunakan `Content-Type: application/json`.
- Gunakan bearer token dari environment.
- Timeout koneksi dan keseluruhan request harus dikonfigurasi.
- Simpan HTTP status dan response body untuk pengambilan keputusan.
- Jangan log token atau seluruh jawaban pada production.

Contoh inti:

```php
$apiUrl = rtrim((string) getenv('FREXOR_API_URL'), '/');
$token = (string) getenv('FREXOR_WEBHOOK_TOKEN');

if ($apiUrl === '' || $token === '') {
    throw new RuntimeException('Konfigurasi Frexor API belum lengkap.');
}

$payloadJson = json_encode(
    $payload,
    JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
);

$curl = curl_init($apiUrl . '/api/v1/webhooks/assessments');
curl_setopt_array($curl, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => $payloadJson,
    CURLOPT_HTTPHEADER => [
        'Authorization: Bearer ' . $token,
        'Content-Type: application/json',
        'Accept: application/json',
    ],
    CURLOPT_CONNECTTIMEOUT => 5,
    CURLOPT_TIMEOUT => 20,
]);
```

## 14. Penanganan Response

### 14.1 Job Baru

Automation API mengembalikan HTTP `201`:

```json
{
  "message": "Assessment diterima",
  "job_id": "uuid",
  "external_id": "SPR003-ATTEMPT-001",
  "status": "QUEUED",
  "created": true
}
```

Backend website menyimpan `job_id` pada record attempt.

### 14.2 Request Idempotent

Automation API mengembalikan HTTP `200` dan `created: false`. Backend website tetap memperbarui atau memastikan `frexor_job_id` tersimpan.

### 14.3 Validation Error

Automation API mengembalikan HTTP `422`. Backend website harus:

- membaca JSON response;
- mencatat ringkasan teknis tanpa token/jawaban;
- mengembalikan HTTP `422` kepada frontend;
- tidak mengembalikan `success: true`;
- menampilkan pesan yang dapat ditindaklanjuti.

### 14.4 Authentication Error

- HTTP `401`: token salah.
- HTTP `403`: credential tidak dikirim atau tidak diterima.
- Backend mengembalikan `502` atau status integrasi yang disepakati kepada frontend, tanpa mengekspos token.

### 14.5 Network Error

Jika cURL gagal terhubung atau timeout:

- backend mengembalikan HTTP `502 Bad Gateway`;
- submission lokal tidak boleh dianggap berhasil terkirim;
- attempt ditandai `WEBHOOK_PENDING` atau `WEBHOOK_FAILED`;
- retry menggunakan `external_id` yang sama.

## 15. Kontrak Response Backend Website

### Sukses

HTTP `200` atau `201`:

```json
{
  "success": true,
  "message": "Jawaban diterima dan masuk antrean.",
  "submission_id": "SPR003-ATTEMPT-001",
  "job_id": "uuid",
  "status": "QUEUED"
}
```

### Validasi Gagal

HTTP `422`:

```json
{
  "success": false,
  "message": "Data assessment tidak valid.",
  "errors": []
}
```

### Automation API Tidak Dapat Dihubungi

HTTP `502`:

```json
{
  "success": false,
  "message": "Layanan automation belum dapat dihubungi. Submission dapat dicoba kembali."
}
```

Backend website dilarang mengembalikan HTTP `200` ketika pengiriman webhook gagal.

## 16. Keamanan dan Privasi

- Ganti webhook token yang telah terekspos sebelum pengujian berikutnya.
- Jangan hardcode credential database atau webhook token dalam repository.
- Gunakan secret/environment configuration sesuai deployment website.
- Hapus `last_payload_debug.json` sebelum production.
- Jangan simpan payload lengkap di document root.
- Jangan log jawaban psikotes, token, atau session ID.
- Error response production tidak boleh berisi raw exception database.
- Pertahankan validasi CSRF menggunakan `hash_equals`.
- Batasi Automation API melalui firewall agar hanya backend website dan worker yang dapat mengaksesnya.

## 17. Observability

Log integrasi website boleh memuat:

```text
external_id
job_id
HTTP status
durasi request
error type
timestamp
```

Log tidak boleh memuat:

```text
webhook token
CSRF token
session cookie
seluruh jawaban
payload identitas lengkap
```

## 18. Acceptance Criteria

### AC-01 Payload Valid

Given satu attempt dengan 24 DISC, 30 VAK, dan 60 IQ yang valid, ketika backend mengirim webhook, Automation API mengembalikan `201`, `created: true`, dan `job_id` tersimpan di database website.

### AC-02 VAK dan IQ Menggunakan `answer`

Payload akhir tidak memiliki key `answers` pada item VAK/IQ. Setiap item memakai key `answer` dengan nilai kapital.

### AC-03 Nomor Soal Relatif

Payload menggunakan `question_no` 1-24 untuk DISC, 1-30 untuk VAK, dan 1-60 untuk IQ, terlepas dari nilai primary key `id_soal`.

### AC-04 Idempotent Retry

Ketika attempt yang sama dikirim ulang dengan `external_id` sama, Automation API mengembalikan `200`, `created: false`, dan `job_id` sama.

### AC-05 Error Tidak Disamarkan

Ketika Automation API mengembalikan `422`, backend website tidak mengembalikan HTTP `200` dan tidak menampilkan submission sebagai berhasil.

### AC-06 Token Aman

Webhook token tidak ada pada source code, response browser, JavaScript bundle, repository Git, atau log.

### AC-07 Data Tidak Valid Ditolak Lokal

Backend menolak jumlah jawaban salah, nomor duplikat/hilang, opsi ilegal, identitas terlalu panjang, dan tanggal tidak valid sebelum memanggil Automation API.

### AC-08 Network Failure Dapat Diulang

Ketika Automation API tidak dapat dihubungi, attempt tetap memiliki `external_id` yang sama dan dapat dikirim ulang tanpa membuat job duplikat.

## 19. Test Cases Wajib

1. Submission valid menghasilkan `201`.
2. Submission yang sama menghasilkan `200` dan `created: false`.
3. DISC hanya 23 item ditolak.
4. VAK hanya 29 item ditolak.
5. IQ hanya 59 item ditolak.
6. DISC `mirip` sama dengan `tidak_mirip` ditolak.
7. VAK lowercase dinormalisasi menjadi uppercase.
8. IQ nomor 12 dengan jawaban D ditolak.
9. Nama lebih dari 20 karakter ditolak.
10. Posisi lebih dari 20 karakter ditolak.
11. `test_date` bukan `YYYY-MM-DD` ditolak.
12. Token salah tidak diterjemahkan menjadi sukses.
13. API timeout menghasilkan HTTP `502` dari backend website.
14. Retry timeout memakai `external_id` yang sama.
15. Source dan log tidak mengandung token atau payload lengkap.

## 20. Definition of Done

- Seluruh acceptance criteria terpenuhi.
- Seluruh test case wajib lulus.
- Token lama sudah diganti.
- Token baru dibaca dari environment.
- `last_payload_debug.json` sudah dihapus dan tidak dapat diakses melalui web.
- Backend website menyimpan `job_id` dan status integrasi.
- Response frontend mencerminkan hasil webhook sebenarnya.
- Satu controlled test end-to-end mencapai status Automation API `DONE`.
