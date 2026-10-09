# Admin Backend Integration Design

## 1. Boundary

Web admin adalah client HTTP dari Frexor Automation API. Implementasi bebas bahasa dan framework.

```text
Browser --session--> Admin Backend --service token--> Automation API
                                                  |-> SQLite metadata
                                                  `-> Result storage
```

Admin backend tidak membaca SQLite atau result directory secara langsung. Aturan ini mencegah coupling schema, path traversal, permission leak, dan masalah saat storage dipindahkan.

## 2. Current Integration

### Read Known Job

```http
GET /api/v1/jobs/{job_id}
Authorization: Bearer <webhook-token>
Accept: application/json
```

Field penting:

```json
{
  "job_id": "uuid",
  "external_id": "SPR003-ATTEMPT-001",
  "status": "DONE",
  "result": {
    "available": true,
    "filename": "Hasil Psikotes 08-10-2026 CEO YOHAN.pdf",
    "sha256": "...",
    "size_bytes": 123456,
    "uploaded_at": "2026-10-09T01:00:00+00:00"
  }
}
```

### Download Known Job

```http
GET /api/v1/admin/jobs/{job_id}/result
Authorization: Bearer <webhook-token>
Accept: application/pdf
```

Current token choice is transitional. Replace it with dedicated admin-service authentication before production dashboard release.

## 3. Recommended Admin Backend Flow

```text
1. Browser requests admin detail using authenticated session.
2. Admin backend checks local role/permission.
3. Admin backend resolves stored job_id.
4. Admin backend calls Automation API status endpoint.
5. If result.available is not true, return controlled not-ready state.
6. For download, call result endpoint with service token.
7. Stream upstream bytes to browser.
8. Write audit record after outcome is known.
```

Jangan membuat URL download langsung menuju Automation API karena hal itu memerlukan token di browser.

## 4. Language-Neutral Pseudocode

```text
function downloadResult(currentUser, jobId):
    requireAuthenticated(currentUser)
    requireRole(currentUser, [HR, SUPERVISOR])

    upstream = http.get(
        AUTOMATION_API_URL + "/api/v1/admin/jobs/" + urlEncode(jobId) + "/result",
        headers = {
            "Authorization": "Bearer " + ADMIN_SERVICE_TOKEN,
            "Accept": "application/pdf",
            "X-Correlation-ID": correlationId
        },
        stream = true,
        timeout = DOWNLOAD_TIMEOUT
    )

    if upstream.status == 404:
        audit(currentUser, jobId, "DOWNLOAD_NOT_FOUND")
        return notFound()

    if upstream.status != 200:
        audit(currentUser, jobId, "DOWNLOAD_FAILED")
        return safeGatewayError(correlationId)

    audit(currentUser, jobId, "DOWNLOAD_OK")
    return streamToBrowser(
        upstream.body,
        contentType = "application/pdf",
        contentDisposition = upstream.contentDisposition,
        cacheControl = "private, no-store"
    )
```

## 5. Target List Contract

Endpoint ini belum tersedia dan menjadi pekerjaan berikutnya:

```http
GET /api/v1/admin/jobs?page=1&page_size=25&status=DONE&result_available=true
Authorization: Bearer <admin-service-token>
```

Target response:

```json
{
  "items": [
    {
      "job_id": "uuid",
      "external_id": "SPR003-ATTEMPT-001",
      "name": "YOHAN",
      "position": "CEO",
      "test_date": "2026-10-08",
      "status": "DONE",
      "result_available": true,
      "result_filename": "Hasil Psikotes 08-10-2026 CEO YOHAN.pdf",
      "updated_at": "2026-10-09T01:00:00+00:00"
    }
  ],
  "page": 1,
  "page_size": 25,
  "total": 1,
  "total_pages": 1
}
```

Sort default: `test_date DESC, created_at DESC`. Query harus memakai parameter binding dan index yang sesuai.

## 6. Authentication Migration

### Current

- Website submission/status: webhook token.
- Worker upload: worker token + worker ID.
- Admin download: sementara webhook token.

### Production Target

- Website submission: webhook token.
- Worker operations: worker token + worker ID.
- Admin backend: dedicated `FREXOR_ADMIN_TOKEN` atau OAuth2/mTLS/internal gateway.
- Browser user: session login + role.

Token tidak boleh dipakai lintas komponen. Rotasi satu token tidak boleh memutus worker atau website submission.

## 7. Download Proxy Rules

- Gunakan streaming/chunked transfer; jangan base64 PDF dalam JSON.
- Jangan menyimpan temporary file kecuali framework memerlukannya.
- Jangan percaya filename dari query/browser.
- Teruskan filename yang diberikan Automation API setelah sanitasi header oleh framework.
- Set `Cache-Control: private, no-store` untuk data sensitif.
- Batalkan upstream request jika browser terputus bila framework mendukung.
- Batasi concurrent download agar memory dan koneksi tidak habis.

## 8. Audit Schema Recommendation

```text
admin_result_audit
- id
- user_id
- job_id
- action: VIEW_DETAIL | DOWNLOAD
- outcome: SUCCESS | DENIED | NOT_FOUND | UPSTREAM_ERROR
- ip_address
- user_agent
- correlation_id
- created_at
```

Audit tidak menyimpan token, jawaban, isi PDF, atau filesystem path.

## 9. Error Translation

```text
Automation 401/403 -> 502 configuration error for normal users; alert admin
Automation 404     -> 404 result not found/not ready
Automation 409     -> 409 state conflict
Automation 422     -> 502 contract mismatch; developer action required
Automation 5xx     -> 502/503 with correlation ID
Timeout            -> 504 with retry option
```

Jangan meneruskan seluruh body upstream jika berisi detail internal. Log detail secara terbatas di server.

## 10. Contract Test Checklist

Semua implementasi bahasa harus lulus tes berikut:

- Authorization header terkirim tanpa tercatat di log.
- JSON status dapat diparse ketika `result.available=false` dan `true`.
- Download PDF mempertahankan byte dan checksum.
- Filename Unicode/spasi ditangani dengan aman.
- Upstream `401`, `404`, `409`, `422`, `500`, dan timeout dipetakan benar.
- Browser tidak melihat internal bearer token.
- User tanpa role tidak memicu request upstream.
- Dua download bersamaan tidak mencampur isi file.
- File besar tidak dimuat seluruhnya ke memory.

## 11. Implementation Handoff

Agent/developer backend admin harus menerima:

- base URL Automation API per environment;
- service token melalui secret manager/environment;
- endpoint contract dari `docs/API_CONTRACT.md`;
- role matrix organisasi;
- retention dan audit policy;
- timeout dan maximum expected PDF size;
- sample job ID dan synthetic PDF untuk integration test.

Jika framework atau bahasa berubah, kontrak HTTP tetap sama. Perubahan endpoint wajib dilakukan melalui versioned API atau change request.
