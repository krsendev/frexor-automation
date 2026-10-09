# Windows Background Worker

## Tujuan

Menjalankan automation sebagai `Frexor Worker.exe` tanpa terminal terbuka. Worker dimulai oleh Windows Task Scheduler ketika akun automation login.

UI Automation tetap membutuhkan:

- sesi user automation sudah login;
- desktop aktif dan tidak terkunci;
- Frexor dapat dibuka pada sesi tersebut;
- tidak ada user lain yang memakai desktop VM;
- hanya satu worker dan satu Frexor berjalan.

Task ini bukan Windows Service dan tidak boleh dijalankan pada Session 0.

## Build

Jalankan pada Windows dari root repository:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_worker_windows.ps1
```

Output:

```text
dist\Frexor Worker\
├── Frexor Worker.exe
├── config.example.toml
└── frexor_ui_map.example.toml
```

Salin konfigurasi aktif ke folder output:

```powershell
Copy-Item config.toml "dist\Frexor Worker\config.toml"
Copy-Item frexor_ui_map.toml "dist\Frexor Worker\frexor_ui_map.toml"
```

Pastikan path pada `config.toml` tetap valid dari working directory baru. Gunakan absolute path untuk executable Frexor dan folder PDF.

## Tes Manual Sebelum Background

```powershell
& ".\dist\Frexor Worker\Frexor Worker.exe" `
  --config ".\dist\Frexor Worker\config.toml" worker
```

Karena executable bertipe windowed, terminal tidak menampilkan output. Periksa:

```text
dist\Frexor Worker\logs\automation.log
```

Jika konfigurasi gagal sebelum logger utama siap, periksa:

```text
%APPDATA%\FrexorAssessmentAutomation\worker-bootstrap.log
```

Hentikan tes melalui Task Manager sebelum memasang scheduled task.

## Install Scheduled Task

Jalankan sebagai akun Windows khusus automation:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_worker_task.ps1
```

Untuk folder instalasi lain:

```powershell
powershell -ExecutionPolicy Bypass `
  -File scripts\install_worker_task.ps1 `
  -WorkerDirectory "C:\Frexor Automation\Frexor Worker"
```

Installer membuat task `Frexor Automation Worker` dengan aturan:

- trigger saat user saat ini login;
- `Interactive` logon type;
- hidden;
- berjalan tanpa execution time limit;
- restart setelah satu menit jika proses keluar;
- instance baru diabaikan jika worker masih hidup;
- langsung dijalankan setelah instalasi.

## Operasi

Status:

```powershell
Get-ScheduledTask -TaskName "Frexor Automation Worker"
Get-ScheduledTaskInfo -TaskName "Frexor Automation Worker"
```

Restart:

```powershell
Stop-ScheduledTask -TaskName "Frexor Automation Worker"
Start-ScheduledTask -TaskName "Frexor Automation Worker"
```

Uninstall:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\uninstall_worker_task.ps1
```

## Validasi

1. Login sebagai akun automation.
2. Pastikan task berstatus `Running`.
3. Pastikan `Frexor Worker.exe` hanya satu pada Task Manager.
4. Kirim satu assessment dummy.
5. Pastikan Frexor memproses DISC, VAK, IQ.
6. Pastikan merged PDF dibuat dan diunggah.
7. Pastikan job `DONE` dan result dapat diunduh.
8. Tutup proses worker melalui Task Manager; task harus memulai ulang sekitar satu menit.
9. Pastikan restart tidak membuat dua worker.

## VM Reboot

Task `At log on` tidak dapat bekerja sebelum user login. Jika VM reboot:

- login manual sebagai akun automation; atau
- gunakan Windows auto-logon hanya jika disetujui IT dan risikonya diterima.

Jangan gunakan `Run whether user is logged on or not`. Mode tersebut tidak menyediakan desktop interaktif yang dibutuhkan Frexor.

## Remote Access

- RustDesk yang mempertahankan sesi console biasanya lebih aman.
- RDP dapat mengganti atau memutus sesi interaktif.
- Jangan logout, lock, mengganti user, atau mengubah virtual desktop saat job berjalan.
- Lakukan maintenance ketika antrean kosong dan worker dihentikan.
