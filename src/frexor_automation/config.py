from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from .errors import ConfigurationError


@dataclass(frozen=True)
class FrexorConfig:
    adapter: str
    executable_path: Path
    window_title_re: str
    window_class_name: str
    startup_timeout_seconds: int
    action_timeout_seconds: int
    ui_map_path: Path


@dataclass(frozen=True)
class SheetsConfig:
    spreadsheet_id: str
    credentials_path: Path
    participants_sheet: str
    disc_sheet: str
    vak_sheet: str
    iq_sheet: str


@dataclass(frozen=True)
class ExcelConfig:
    workbook_path: Path
    participants_sheet: str
    disc_sheet: str
    vak_sheet: str
    iq_sheet: str


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    token: str
    timeout_seconds: float
    worker_id: str
    poll_interval_seconds: float
    heartbeat_interval_seconds: float


@dataclass(frozen=True)
class ProcessingConfig:
    max_retries: int
    retry_base_delay_seconds: float
    stop_on_fatal_error: bool
    continue_after_participant_error: bool


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    directory: Path


@dataclass(frozen=True)
class PdfConfig:
    base_directory: Path
    module_directories: dict[str, str]
    output_directory: Path
    timeout_seconds: float
    poll_interval_seconds: float
    stable_seconds: float
    minimum_size_bytes: int


@dataclass(frozen=True)
class AppConfig:
    data_source: str
    frexor: FrexorConfig
    sheets: SheetsConfig
    excel: ExcelConfig
    api: ApiConfig
    processing: ProcessingConfig
    pdf: PdfConfig
    logging: LoggingConfig


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path).resolve()
    if not config_path.exists():
        raise ConfigurationError(f"Configuration not found: {config_path}")
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    base = config_path.parent
    try:
        f = raw["frexor"]
        s = raw["sheets"]
        p = raw["processing"]
        pdf = raw["pdf"]
        log = raw["logging"]
        source = raw.get("data_source", {})
        excel = raw.get("excel", {})
        api = raw.get("api", {})
        return AppConfig(
            data_source=source.get("type", "google_sheets"),
            frexor=FrexorConfig(
                adapter=f["adapter"],
                executable_path=Path(f["executable_path"]),
                window_title_re=f["window_title_re"],
                window_class_name=f.get("window_class_name", ""),
                startup_timeout_seconds=int(f["startup_timeout_seconds"]),
                action_timeout_seconds=int(f["action_timeout_seconds"]),
                ui_map_path=(base / f["ui_map_path"]).resolve(),
            ),
            sheets=SheetsConfig(
                spreadsheet_id=s["spreadsheet_id"],
                credentials_path=(base / s["credentials_path"]).resolve(),
                participants_sheet=s["participants_sheet"],
                disc_sheet=s["disc_sheet"],
                vak_sheet=s["vak_sheet"],
                iq_sheet=s["iq_sheet"],
            ),
            excel=ExcelConfig(
                workbook_path=(base / excel.get("workbook_path", "assessment-data.xlsx")).resolve(),
                participants_sheet=excel.get("participants_sheet", "Participants"),
                disc_sheet=excel.get("disc_sheet", "DISC"),
                vak_sheet=excel.get("vak_sheet", "VAK"),
                iq_sheet=excel.get("iq_sheet", "IQ"),
            ),
            api=ApiConfig(
                base_url=api.get("base_url", "").rstrip("/"),
                token=api.get("token", ""),
                timeout_seconds=float(api.get("timeout_seconds", 30)),
                worker_id=api.get("worker_id", "").strip(),
                poll_interval_seconds=float(api.get("poll_interval_seconds", 5)),
                heartbeat_interval_seconds=float(api.get("heartbeat_interval_seconds", 60)),
            ),
            processing=ProcessingConfig(**p),
            pdf=PdfConfig(
                base_directory=Path(pdf.get("base_directory", pdf.get("watch_directory", ""))),
                module_directories=dict(pdf.get("module_directories", {
                    "DISC": "DISC", "VAK": "VAK", "IQ": "IQ",
                })),
                output_directory=(base / pdf["output_directory"]).resolve(),
                timeout_seconds=float(pdf["timeout_seconds"]),
                poll_interval_seconds=float(pdf["poll_interval_seconds"]),
                stable_seconds=float(pdf["stable_seconds"]),
                minimum_size_bytes=int(pdf["minimum_size_bytes"]),
            ),
            logging=LoggingConfig(level=log["level"], directory=(base / log["directory"]).resolve()),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigurationError(f"Invalid configuration: {exc}") from exc
