from __future__ import annotations

from .config import AppConfig
from .errors import ConfigurationError
from .frexor.base import FrexorAdapter
from .frexor.mock import MockFrexorAdapter
from .repositories import ApiRepository, ExcelRepository, GoogleSheetsRepository
from .pdf_results import MockPdfResultManager, PdfResultManager


def build_repository(config: AppConfig):
    if config.data_source == "google_sheets":
        return GoogleSheetsRepository(config.sheets, config.processing.max_retries)
    if config.data_source == "excel":
        return ExcelRepository(config.excel)
    if config.data_source == "api":
        return ApiRepository(config.api)
    raise ConfigurationError(f"Unknown data source: {config.data_source}")


def build_adapter(config: AppConfig) -> FrexorAdapter:
    if config.frexor.adapter == "mock":
        return MockFrexorAdapter()
    if config.frexor.adapter == "windows":
        from .frexor.windows import WindowsFrexorAdapter
        return WindowsFrexorAdapter(config.frexor)
    raise ConfigurationError(f"Unknown Frexor adapter: {config.frexor.adapter}")


def build_pdf_manager(config: AppConfig):
    if config.frexor.adapter == "mock":
        return MockPdfResultManager()
    return PdfResultManager(config.pdf)
