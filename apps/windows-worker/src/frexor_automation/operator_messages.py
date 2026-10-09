from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OperatorMessage:
    title: str
    description: str
    action: str
    can_retry: bool = True


MESSAGES = {
    "LOGIN_REQUIRED": OperatorMessage(
        "Frexor memerlukan login",
        "Data login Frexor belum terisi sehingga automation tidak dapat melanjutkan dengan aman.",
        "Masuk ke Frexor dengan akun yang diizinkan, lalu pilih Periksa Lagi.",
    ),
    "PDF_TIMEOUT": OperatorMessage(
        "Hasil PDF belum ditemukan",
        "Program menghentikan proses agar hasil peserta berikutnya tidak tertukar.",
        "Pastikan Frexor selesai membuat PDF, lalu pilih Coba Lagi.",
    ),
    "PDF_INVALID": OperatorMessage(
        "Hasil PDF tidak dapat digunakan",
        "File hasil ditemukan, tetapi belum lengkap atau tidak dapat dibaca.",
        "Periksa folder hasil Frexor, lalu pilih Coba Lagi.",
    ),
    "PDF_ASSOCIATION_FAILED": OperatorMessage(
        "Hasil PDF tidak dapat dipastikan",
        "Lebih dari satu hasil berubah atau nama hasil sudah digunakan.",
        "Minta administrator memeriksa folder hasil sebelum melanjutkan.",
        False,
    ),
    "SUBMISSION_NOT_VERIFIED": OperatorMessage(
        "Pengiriman hasil belum terkonfirmasi",
        "Frexor tidak menunjukkan perubahan halaman yang diharapkan setelah Kirim.",
        "Periksa layar Frexor, lalu pilih Coba Lagi jika data belum terkirim.",
    ),
    "DATA_INVALID": OperatorMessage(
        "Data peserta belum lengkap",
        "Ada jawaban yang kosong, tidak valid, atau jumlah soal tidak sesuai.",
        "Perbaiki data pada Google Sheets, lalu lakukan pemeriksaan ulang.",
    ),
    "INTERRUPTED_REVIEW_REQUIRED": OperatorMessage(
        "Proses sebelumnya terhenti",
        "Program tidak dapat memastikan apakah hasil terakhir sudah terkirim.",
        "Periksa peserta terakhir di Frexor sebelum memilih Coba Lagi.",
    ),
    "PARTICIPANT_OPEN_FAILED": OperatorMessage(
        "Frexor belum siap menerima peserta",
        "Halaman peserta atau form assessment tidak dapat dibuka.",
        "Pastikan Frexor terbuka dan tidak sedang menampilkan dialog lain.",
    ),
}


def friendly_error(code: str, technical_message: str = "") -> OperatorMessage:
    if code in MESSAGES:
        return MESSAGES[code]
    return OperatorMessage(
        "Proses tidak dapat dilanjutkan",
        "Program menemukan kondisi yang tidak aman dan menghentikan batch.",
        "Pilih Lihat Detail untuk administrator, atau hubungi dukungan teknis.",
        False,
    )
