# Architecture Decisions

## ADR-001 - FastAPI as Queue API

Decision: gunakan FastAPI untuk webhook, worker contract, status, dan future result API.

Reason: kontrak JSON tervalidasi, mudah diuji, dan cocok untuk komunikasi LAN.

## ADR-002 - SQLite Owned by API Host

Decision: satu file SQLite untuk seluruh job; hanya API host yang mengaksesnya.

Reason: deployment sederhana, transaksi lokal, dan worker tidak memerlukan network filesystem.

Revisit when: API perlu multi-instance atau volume/reporting melebihi kapasitas operasional SQLite.

## ADR-003 - Worker Pulls Jobs

Decision: Windows worker melakukan polling dan claim, bukan API mendorong pekerjaan ke Windows.

Reason: Windows/VM dapat offline, tidak perlu membuka inbound port worker, dan retry lebih aman.

## ADR-004 - One Active Job per Worker

Decision: satu worker hanya memproses satu job sampai terminal state.

Reason: Frexor adalah UI desktop stateful dan tidak aman diparalelkan dalam satu session.

## ADR-005 - Lease and Heartbeat

Decision: ownership job dibatasi lease dan dipertahankan heartbeat.

Reason: server dapat mendeteksi worker mati tanpa menganggap semua job aman untuk diulang.

## ADR-006 - Processing Expiry Requires Review

Decision: expired `PROCESSING` menjadi `REVIEW_REQUIRED`, bukan otomatis `QUEUED`.

Reason: tombol submit mungkin sudah ditekan dan pengulangan dapat membuat hasil ganda.

## ADR-007 - Website Calls API Server-to-Server

Decision: browser tidak memanggil webhook production secara langsung.

Reason: bearer token tidak boleh terlihat di browser dan CORS bukan kontrol keamanan credential.

## ADR-008 - Separate Tokens

Decision: webhook token dan worker token berbeda.

Reason: compromise satu client tidak memberikan akses ke endpoint client lain.

## ADR-009 - PDFs Stored as Files

Decision: PDF tidak disimpan sebagai SQLite BLOB. SQLite hanya menyimpan metadata/path/checksum.

Reason: backup, streaming download, dan storage lifecycle lebih mudah dikelola.

## ADR-010 - Merge Runs on Worker

Decision: merge dilakukan setelah worker memiliki tiga PDF tervalidasi, sebelum modul terakhir disimpan sebagai `DONE`.

Reason: menghindari tiga upload awal dan worker sudah memiliki seluruh source file lokal.

Alternative: upload tiga source PDF lalu merge pada server. Revisit jika source PDF juga harus disimpan terpusat.

## ADR-011 - Dashboard Never Exposes Storage Paths

Decision roadmap: browser mengunduh melalui authorized endpoint.

Reason: filesystem path bukan authorization mechanism dan dapat membocorkan struktur server.

## ADR-012 - Result Lifecycle Separate from Module Lifecycle

Decision roadmap: result memiliki state merge/upload sendiri.

Reason: tiga modul dapat selesai walaupun merge atau upload gagal; retry result tidak boleh mengulang Frexor.
