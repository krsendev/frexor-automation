from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import sys
import time

from .config import load_config
from .errors import AutomationError
from .factory import build_adapter, build_pdf_manager, build_repository
from .logging_setup import configure_logging
from .orchestrator import Orchestrator


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Frexor Assessment Automation")
    result.add_argument("--config", default="config.toml")
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="Validate Sheets data without opening Frexor")
    sub.add_parser("run", help="Process READY/PARTIAL participants")
    sub.add_parser("retry-errors", help="Retry ERROR modules without repeating DONE modules")
    sub.add_parser("worker", help="Continuously claim and process API jobs")
    sub.add_parser("ui", help="Launch the operator desktop UI")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    logger: logging.Logger | None = None
    try:
        if args.command == "ui":
            from .ui import run_ui
            run_ui(args.config)
            return 0
        from PySide6.QtCore import QLockFile

        app_data = os.environ.get("APPDATA")
        lock_root = Path(app_data) / "FrexorAssessmentAutomation" if app_data else Path(args.config).resolve().parent
        lock_root.mkdir(parents=True, exist_ok=True)
        instance_lock = QLockFile(str(lock_root / "application.lock"))
        instance_lock.setStaleLockTime(0)
        if not instance_lock.tryLock(100):
            print(
                "ERROR: Aplikasi Frexor Automation lain masih berjalan. "
                "Tutup UI atau proses CLI sebelumnya, lalu coba lagi.",
                file=sys.stderr,
            )
            return 1
        config = load_config(args.config)
        logger = configure_logging(config.logging.directory, config.logging.level)
        repository = build_repository(config)
        orchestrator = Orchestrator(
            repository,
            build_adapter(config),
            build_pdf_manager(config),
            logger,
            continue_after_participant_error=config.processing.continue_after_participant_error,
        )
        if args.command == "validate":
            results = orchestrator.validate_batch()
            for result in results:
                detail = "VALID" if result.valid else "INVALID: " + "; ".join(result.errors)
                print(f"{result.participant_id} -> {detail}")
            return 0 if all(result.valid for result in results) else 2
        if args.command == "worker":
            if config.data_source != "api":
                raise ValueError("The worker command requires data_source.type = 'api'")
            logger.info("WORKER_START worker_id=%s api=%s", repository.worker_id, config.api.base_url)
            print(f"Worker {repository.worker_id} connected to {config.api.base_url}")
            try:
                while True:
                    summary = orchestrator.run_batch()
                    if summary.total == 0:
                        time.sleep(config.api.poll_interval_seconds)
                    else:
                        logger.info(
                            "WORKER_JOB_COMPLETE total=%s success=%s failed=%s",
                            summary.total, summary.success, summary.failed,
                        )
                        print(
                            f"Job complete: success={summary.success} "
                            f"failed={summary.failed}"
                        )
            except KeyboardInterrupt:
                logger.info("WORKER_STOP requested by operator")
                print("Worker stopped safely")
                return 0
            finally:
                repository.close()

        summary = orchestrator.run_batch(retry_errors=args.command == "retry-errors")
        print(
            f"Batch complete: total={summary.total} success={summary.success} "
            f"failed={summary.failed} skipped={summary.skipped}"
        )
        for participant_id, error_code, detail in summary.failed_participants:
            suffix = f" - {detail}" if detail else ""
            print(f"FAILED {participant_id}: {error_code}{suffix}")
        return 0
    except (AutomationError, OSError, ValueError) as exc:
        if logger is not None:
            logger.exception("FATAL %s", exc)
        if sys.stderr is not None:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        if logger is not None:
            logger.exception("UNEXPECTED_FATAL %s", exc)
        if sys.stderr is not None:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
