# Project Documentation Index

## Start Here

1. `README.md` - setup dan penggunaan repository.
2. `PRD/PRD_Frexor_Automation_Platform_v3.md` - requirement induk terbaru.
3. `docs/SYSTEM_DESIGN.md` - arsitektur current dan planned.
4. `docs/TEST_STRATEGY.md` - pengujian yang sudah dan belum dilakukan.
5. `docs/WINDOWS_SINGLE_VM_DEPLOYMENT.md` - instalasi ulang dan operasi pada satu VM Windows.
6. `docs/PRODUCTION_DEPLOYMENT.md` - alternatif deployment API Linux dan worker Windows.

## Product Requirements

- `PRD/PRD_Frexor_Automation_Platform_v3.md` - baseline terbaru.
- `PRD/PRD_Website_Frexor_Webhook_Integration_v1.md` - integrasi backend website.
- `PRD/PRD_Frexor_Admin_Backend_v1.md` - requirement backend web admin dan akses hasil.
- `PRD/PRD_Frexor_Assessment_Automation_v1.md` - requirement awal.
- `PRD/PRD_Frexor_Assessment_Automation_v2_Batch_PDF.md` - batch dan PDF baseline.
- `PRD/PRD_DESIGN_Frexor_Desktop_Operator_v1.md` - desain desktop operator historis.
- `PRD/CR_Operator_Abstraction_PRD_v1.md` - change request UX operator historis.

## Engineering Design

- `docs/SYSTEM_DESIGN.md` - boundaries, sequence, queue, recovery, dan scaling.
- `docs/API_CONTRACT.md` - endpoint dan autentikasi antar sistem.
- `docs/ADMIN_BACKEND_INTEGRATION_DESIGN.md` - desain bahasa-agnostik untuk list/detail/download admin.
- `docs/ARCHITECTURE_DECISIONS.md` - keputusan desain dan alasan.
- `docs/DATA_AND_STATE_MODEL.md` - schema dan state machine.
- `docs/FREXOR_UI_DISCOVERY.md` - UI Automation discovery.
- `docs/OPERATOR_DESKTOP_IMPLEMENTATION.md` - desktop implementation lama.

## Operations and Quality

- `docs/TEST_STRATEGY.md` - test matrix dan production gate.
- `docs/OPERATIONS_RUNBOOK.md` - operasi, backup, incident, dan token rotation.
- `docs/WINDOWS_SINGLE_VM_DEPLOYMENT.md` - panduan utama satu VM: install, build, start, stop, update, backup, dan rollback.
- `docs/PRODUCTION_DEPLOYMENT.md` - instalasi service dan worker.
- `docs/WINDOWS_BACKGROUND_WORKER.md` - build executable dan Task Scheduler worker tanpa terminal.

## Roadmap

- `docs/ROADMAP_PDF_MERGE_ADMIN_PORTAL.md` - merge PDF, upload server, dan dashboard HR.

## Current Truth

- Webhook queue dan worker tersedia.
- Satu end-to-end normal flow berhasil.
- Automated tests tersedia.
- Batch besar dan failure scenarios belum seluruhnya diuji.
- Merge dan upload PDF sudah implemented dan diuji otomatis; backend/dashboard admin selain download by job ID masih planned.

Jika dokumen lama bertentangan dengan PRD v3, gunakan PRD v3 dan source code aktif sebagai acuan, lalu catat keputusan baru sebagai change request.
