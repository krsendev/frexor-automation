# API Contract

## 1. Authentication Classes

| Client | Credential | Scope |
|---|---|---|
| Website backend | Webhook bearer token | Create/read website jobs |
| Windows worker | Worker bearer token + `X-Worker-ID` | Claim, answers, status, heartbeat |
| Dashboard HR | Planned user session/role | List and download results |

Webhook token dan worker token wajib berbeda.

## 2. Health

```http
GET /health
```

Response:

```json
{"status":"ok"}
```

## 3. Website Endpoints

### Create Assessment

```http
POST /api/v1/webhooks/assessments
Authorization: Bearer <webhook-token>
Content-Type: application/json
```

Body summary:

```json
{
  "external_id": "SPR003-ATTEMPT-001",
  "name": "YOHAN",
  "position": "CEO",
  "test_date": "2026-10-08",
  "answers": {
    "disc": [],
    "vak": [],
    "iq": []
  }
}
```

Responses:

- `201`: job baru.
- `200`: idempotent duplicate.
- `401`: token salah.
- `403`: bearer credential tidak tersedia.
- `422`: schema atau jawaban tidak valid.

### Read Job Status

```http
GET /api/v1/jobs/{job_id}
Authorization: Bearer <webhook-token>
```

## 4. Worker Endpoints

### Claim

```http
POST /api/v1/worker/jobs/claim
Authorization: Bearer <worker-token>
Content-Type: application/json
```

```json
{"worker_id":"frexor-vm-01"}
```

- `200`: job metadata.
- `204`: antrean kosong.

### Read Answers

```http
GET /api/v1/worker/jobs/{job_id}/answers/{module}
Authorization: Bearer <worker-token>
X-Worker-ID: frexor-vm-01
```

`module` adalah `DISC`, `VAK`, atau `IQ`.

### Update Module

```http
PATCH /api/v1/worker/jobs/{job_id}/modules/{module}
Authorization: Bearer <worker-token>
X-Worker-ID: frexor-vm-01
Content-Type: application/json
```

Processing:

```json
{
  "status": "PROCESSING",
  "error_code": "",
  "error_message": "",
  "pdf_path": ""
}
```

Done:

```json
{
  "status": "DONE",
  "error_code": "",
  "error_message": "",
  "pdf_path": "C:\\archive\\DISC.pdf"
}
```

Error:

```json
{
  "status": "ERROR",
  "error_code": "PDF_TIMEOUT",
  "error_message": "PDF tidak muncul dalam batas waktu",
  "pdf_path": ""
}
```

### Heartbeat

```http
POST /api/v1/worker/jobs/{job_id}/heartbeat
Authorization: Bearer <worker-token>
X-Worker-ID: frexor-vm-01
```

Tidak memiliki request body.

## 5. Result Endpoints

### Upload Merged Result

```http
POST /api/v1/worker/jobs/{job_id}/result
Authorization: Bearer <worker-token>
X-Worker-ID: frexor-vm-01
Content-Type: multipart/form-data
```

Form fields:

```text
file=<merged PDF>
sha256=<64 lowercase hexadecimal characters>
```

Status: `CURRENT`. Upload hanya diterima dari worker pemilik job setelah DISC dan VAK `DONE` serta IQ `PROCESSING`. Upload checksum sama bersifat idempotent.

### Admin List

```http
GET /api/v1/admin/jobs
```

Status: `PLANNED`.

### Admin Download

```http
GET /api/v1/admin/jobs/{job_id}/result
Authorization: Bearer <webhook-token>
```

Status: `CURRENT` untuk integrasi backend web admin. Token tidak boleh dikirim ke browser. Endpoint mengembalikan attachment PDF.

## 6. Error Body

Pydantic validation:

```json
{
  "detail": [
    {
      "loc": ["body", "answers", "disc", 20, "tidak_mirip"],
      "msg": "Input should be 'A', 'B', 'C' or 'D'",
      "type": "literal_error"
    }
  ]
}
```

Client harus membaca response body pada status non-2xx dan tidak menyamarkannya sebagai sukses.
