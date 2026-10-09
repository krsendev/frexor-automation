# Dummy Integration Data

Dataset ini hanya untuk controlled integration test. Jawaban menggunakan pola sintetis dan tidak boleh dipakai untuk interpretasi psikologis atau keputusan karyawan.

## Participant

- ID: `DUMMY001`
- Name: `DUMMY AUTOMATION`
- Position: `TEST`

Import setiap CSV ke tab Google Sheets yang namanya sama. Gunakan spreadsheet uji terpisah dari data produksi.

Expected PDF filenames pada tanggal pengujian:

```text
Hasil DISC YYYY-MM-DD TEST DUMMY AUTOMATION.pdf
Hasil VAK YYYY-MM-DD TEST DUMMY AUTOMATION.pdf
Hasil IQ YYYY-MM-DD TEST DUMMY AUTOMATION.pdf
```

Sebelum test, pastikan tidak ada file dengan nama tersebut di folder Frexor atau folder arsip automation. Jalankan `validate` terlebih dahulu, lalu proses hanya satu participant ini.
