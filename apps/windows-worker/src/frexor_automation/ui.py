from __future__ import annotations

import logging
from pathlib import Path
import sys

from .config import load_config
from .config_writer import write_config
from .domain import Module, Status
from .factory import build_adapter, build_pdf_manager, build_repository
from .logging_setup import configure_logging
from .operator_messages import friendly_error
from .orchestrator import Orchestrator
from .state_store import RunState, RunStateStore


STYLE = """
QWidget { color: #182522; font-family: "Aptos", "Segoe UI Variable", "Segoe UI"; font-size: 14px; }
QMainWindow, #content, #workspace { background: #f4f1e9; }
#sidebar { background: #123b3a; min-width: 232px; max-width: 232px; }
#brand { color: #f7f3e8; font-size: 21px; font-weight: 700; padding: 10px 8px 4px 8px; }
#brandCaption { color: #9fc0b9; font-size: 12px; padding: 0 8px 24px 8px; }
#topbar { background: #faf8f2; border-bottom: 1px solid #ded9cd; }
#topbarTitle { color: #29433e; font-size: 13px; font-weight: 600; }
#statusBadge { background: #e7ece7; color: #53615d; border-radius: 12px; padding: 6px 12px; font-weight: 600; }
#statusBadge[status="ready"] { background: #dceee4; color: #17633f; }
#statusBadge[status="working"] { background: #fff0c9; color: #7b5100; }
#statusBadge[status="error"] { background: #f8dfdc; color: #8c2f28; }
QPushButton[nav="true"] { color: #c8d8d6; background: transparent; border: 0; text-align: left; padding: 12px 16px; border-radius: 8px; }
QPushButton[nav="true"]:checked { color: white; background: #1d5358; font-weight: 600; }
QPushButton[nav="true"]:hover { background: #17434a; }
QPushButton { background: #e4e8e1; border: 0; border-radius: 8px; padding: 10px 16px; font-weight: 600; }
QPushButton:hover { background: #d7dfd8; }
QPushButton:disabled { color: #8c9692; background: #e8ebe9; }
QPushButton[primary="true"] { color: white; background: #d76538; padding: 12px 24px; }
QPushButton[primary="true"]:hover { background: #bd542d; }
QPushButton[danger="true"] { color: #8d241f; background: #f7dfdc; }
QFrame[card="true"] { background: #fffdf8; border: 1px solid #ded9cd; border-radius: 14px; }
QFrame[accentCard="true"] { background: #173f3d; border: 0; border-radius: 14px; }
QLabel[title="true"] { font-size: 30px; font-weight: 700; color: #173f3d; }
QLabel[subtitle="true"] { color: #62706b; font-size: 15px; }
QLabel[kpi="true"] { font-size: 42px; font-weight: 700; color: #d76538; }
QLabel[success="true"] { color: #16734d; font-weight: 600; }
QLabel[warning="true"] { color: #9a5a08; font-weight: 600; }
QLabel[error="true"] { color: #a1322b; font-weight: 600; }
QProgressBar { border: 0; background: #dfe5e1; border-radius: 6px; height: 12px; text-align: center; }
QProgressBar::chunk { background: #d76538; border-radius: 6px; }
QTableWidget { background: #fffdf8; border: 1px solid #ded9cd; border-radius: 10px; gridline-color: #ece7dc; alternate-background-color: #f8f5ed; }
QHeaderView::section { background: #e9e5da; border: 0; padding: 10px; font-weight: 600; }
QTableWidget::item { border-bottom: 1px solid #ece7dc; padding: 8px; }
QTableWidget::item:selected { background: #e2eee9; color: #173f3d; }
QLabel[tableStatus="true"] { border-radius: 10px; padding: 5px 9px; font-size: 12px; font-weight: 650; }
QLabel[statusKind="success"] { background: #dceee4; color: #17633f; }
QLabel[statusKind="ready"] { background: #e7ece7; color: #53615d; }
QLabel[statusKind="working"] { background: #fff0c9; color: #7b5100; }
QLabel[statusKind="error"] { background: #f8dfdc; color: #8c2f28; }
QLineEdit, QComboBox { background: #fffdf8; border: 1px solid #cfc9bc; border-radius: 8px; padding: 9px; min-height: 20px; }
QLineEdit:focus, QComboBox:focus { border: 1px solid #d76538; }
"""


def _qt():
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError as exc:
        raise RuntimeError("PySide6 belum terpasang. Install project dependencies terlebih dahulu.") from exc
    return QtCore, QtGui, QtWidgets


class SetupWizard:
    @staticmethod
    def run(config_path: Path) -> bool:
        QtCore, _, QtWidgets = _qt()

        class PathPage(QtWidgets.QWizardPage):
            def __init__(self, title, subtitle, caption, field_name, file_filter="", choose_directory=False):
                super().__init__()
                self.setTitle(title)
                self.setSubTitle(subtitle)
                self.edit = QtWidgets.QLineEdit()
                button = QtWidgets.QPushButton("Pilih...")
                row = QtWidgets.QHBoxLayout()
                row.addWidget(self.edit, 1)
                row.addWidget(button)
                layout = QtWidgets.QVBoxLayout(self)
                layout.addLayout(row)
                self.registerField(f"{field_name}*", self.edit)

                def choose():
                    if choose_directory:
                        value = QtWidgets.QFileDialog.getExistingDirectory(self, caption)
                    else:
                        value, _ = QtWidgets.QFileDialog.getOpenFileName(self, caption, "", file_filter)
                    if value:
                        self.edit.setText(value)

                button.clicked.connect(choose)

        class DataSourcePage(QtWidgets.QWizardPage):
            def __init__(self):
                super().__init__()
                self.setTitle("Pilih sumber data")
                self.setSubTitle("Pilihan ini disimpan dan dapat diubah kembali dari Pengaturan.")
                self.source = QtWidgets.QComboBox()
                self.source.addItem("Google Sheets", "google_sheets")
                self.source.addItem("Excel Lokal", "excel")
                self.source.addItem("API", "api")
                self.stack = QtWidgets.QStackedWidget()

                google = QtWidgets.QWidget()
                google_form = QtWidgets.QFormLayout(google)
                self.sheet_id = QtWidgets.QLineEdit()
                self.credential = QtWidgets.QLineEdit()
                credential_button = QtWidgets.QPushButton("Pilih credential...")
                credential_button.clicked.connect(self._choose_credential)
                google_form.addRow("Spreadsheet ID", self.sheet_id)
                google_form.addRow(self.credential, credential_button)

                excel = QtWidgets.QWidget()
                excel_form = QtWidgets.QFormLayout(excel)
                self.excel_path = QtWidgets.QLineEdit()
                excel_button = QtWidgets.QPushButton("Pilih Excel...")
                excel_button.clicked.connect(self._choose_excel)
                excel_form.addRow(self.excel_path, excel_button)

                api = QtWidgets.QWidget()
                api_form = QtWidgets.QFormLayout(api)
                self.api_url = QtWidgets.QLineEdit()
                self.api_url.setPlaceholderText("https://server-kantor/api")
                self.api_token = QtWidgets.QLineEdit()
                self.api_token.setEchoMode(QtWidgets.QLineEdit.Password)
                api_form.addRow("Base URL", self.api_url)
                api_form.addRow("Token", self.api_token)

                for widget in (google, excel, api):
                    self.stack.addWidget(widget)
                self.source.currentIndexChanged.connect(self.stack.setCurrentIndex)
                layout = QtWidgets.QVBoxLayout(self)
                layout.addWidget(self.source)
                layout.addWidget(self.stack)

            def _choose_credential(self):
                value, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Credential Google", "", "JSON (*.json)")
                if value:
                    self.credential.setText(value)

            def _choose_excel(self):
                value, _ = QtWidgets.QFileDialog.getOpenFileName(self, "File Excel", "", "Excel (*.xlsx)")
                if value:
                    self.excel_path.setText(value)

            def validatePage(self):
                source = self.source.currentData()
                valid = (
                    source == "google_sheets" and self.sheet_id.text().strip() and self.credential.text().strip()
                ) or (source == "excel" and self.excel_path.text().strip()) or (
                    source == "api" and self.api_url.text().strip()
                )
                if not valid:
                    QtWidgets.QMessageBox.warning(self, "Konfigurasi belum lengkap", "Lengkapi sumber data yang dipilih.")
                return bool(valid)

        wizard = QtWidgets.QWizard()
        wizard.setWindowTitle("Setup Frexor Assessment Automation")
        wizard.setWizardStyle(QtWidgets.QWizard.ModernStyle)
        wizard.resize(720, 460)

        welcome = QtWidgets.QWizardPage()
        welcome.setTitle("Selamat datang")
        welcome.setSubTitle("Mari siapkan aplikasi untuk penggunaan pertama.")
        text = QtWidgets.QLabel(
            "Setup ini dilakukan satu kali oleh administrator. Setelah selesai, operator dapat "
            "menjalankan batch tanpa terminal atau mengedit file konfigurasi."
        )
        text.setWordWrap(True)
        QtWidgets.QVBoxLayout(welcome).addWidget(text)
        wizard.addPage(welcome)

        data_source = DataSourcePage()
        wizard.addPage(data_source)

        frexor = PathPage(
            "Hubungkan Frexor", "Pilih Frexor.exe pada komputer ini.",
            "Pilih Frexor.exe", "frexor", "Application (*.exe)", False,
        )
        wizard.addPage(frexor)
        watch = PathPage(
            "Folder keluaran Frexor", "Pilih folder tempat Frexor membuat PDF.",
            "Pilih folder PDF Frexor", "watch", choose_directory=True,
        )
        wizard.addPage(watch)
        output = PathPage(
            "Folder arsip hasil", "Pilih folder aman untuk menyimpan hasil terverifikasi.",
            "Pilih folder arsip", "output", choose_directory=True,
        )
        wizard.addPage(output)

        if wizard.exec() != QtWidgets.QDialog.Accepted:
            return False
        write_config(
            config_path,
            wizard.field("frexor"), data_source.sheet_id.text(), data_source.credential.text(),
            wizard.field("watch"), wizard.field("output"),
            source_type=data_source.source.currentData(),
            excel_path=data_source.excel_path.text(),
            api_base_url=data_source.api_url.text(),
            api_token=data_source.api_token.text(),
        )
        return True


def run_ui(config_path: str | Path) -> None:
    QtCore, QtGui, QtWidgets = _qt()
    config_path = Path(config_path).resolve()
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Frexor Assessment Automation")
    app.setOrganizationName("FrexorAutomation")
    app.setStyleSheet(STYLE)
    if not config_path.exists() and not SetupWizard.run(config_path):
        return
    lock_path = config_path.parent / "application.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    instance_lock = QtCore.QLockFile(str(lock_path))
    instance_lock.setStaleLockTime(0)
    if not instance_lock.tryLock(100):
        QtWidgets.QMessageBox.warning(
            None, "Aplikasi sudah berjalan",
            "Frexor Assessment Automation sudah terbuka pada sesi ini.",
        )
        return

    class EngineWorker(QtCore.QObject):
        preflight_ready = QtCore.Signal(object)
        progress = QtCore.Signal(str, str, int, int)
        batch_progress = QtCore.Signal(object)
        completed = QtCore.Signal(object)
        failed = QtCore.Signal(str, str)
        finished = QtCore.Signal()

        def __init__(self, mode: str):
            super().__init__()
            self.mode = mode
            self.orchestrator = None

        @QtCore.Slot()
        def run(self):
            pythoncom = None
            try:
                if sys.platform == "win32":
                    import pythoncom as win_pythoncom

                    pythoncom = win_pythoncom
                    pythoncom.CoInitialize()
                config = load_config(config_path)
                logger = configure_logging(config.logging.directory, config.logging.level)
                repository = build_repository(config)
                adapter = build_adapter(config)
                pdf_manager = build_pdf_manager(config)
                self.orchestrator = Orchestrator(
                    repository, adapter, pdf_manager, logger,
                    lambda pid, module, current, total: self.progress.emit(
                        pid, module.value if module else "", current, total
                    ),
                    config.processing.continue_after_participant_error,
                    lambda summary, pid: self.batch_progress.emit((summary, pid)),
                )
                if self.mode == "preflight":
                    validations = self.orchestrator.validate_batch(retry_errors=False)
                    adapter.check_environment()
                    pdf_manager.check_environment()
                    participants = repository.list_participants(include_errors=True, include_done=True)
                    self.preflight_ready.emit((validations, participants))
                else:
                    summary = self.orchestrator.run_batch(retry_errors=self.mode == "retry")
                    self.completed.emit(summary)
            except Exception as exc:
                self.failed.emit(getattr(exc, "code", "UNEXPECTED_ERROR"), str(exc))
            finally:
                if pythoncom is not None:
                    pythoncom.CoUninitialize()
                self.finished.emit()

        def request_stop(self):
            if self.orchestrator:
                self.orchestrator.request_stop()

    class MainWindow(QtWidgets.QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Frexor Assessment Automation")
            self.resize(1180, 760)
            self.setMinimumSize(1000, 680)
            self.thread = None
            self.worker = None
            self.participants = []
            self.filtered_participants = []
            self.validation_errors = {}
            self.state_store = RunStateStore(config_path.parent / "state" / "run_state.json")
            self.pages = QtWidgets.QStackedWidget()
            self.nav_buttons = []
            self._build_shell()
            self._build_pages()
            self._restore_window_state()
            self._show_previous_state()
            QtCore.QTimer.singleShot(200, self.run_preflight)

        def _build_shell(self):
            central = QtWidgets.QWidget(objectName="content")
            layout = QtWidgets.QHBoxLayout(central)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            sidebar = QtWidgets.QFrame(objectName="sidebar")
            side = QtWidgets.QVBoxLayout(sidebar)
            side.setContentsMargins(16, 24, 16, 20)
            brand = QtWidgets.QLabel("FREXOR\nAUTOMATION", objectName="brand")
            side.addWidget(brand)
            caption = QtWidgets.QLabel("Operator Console", objectName="brandCaption")
            side.addWidget(caption)
            for index, label in enumerate(("Beranda", "Proses", "Peserta", "Hasil")):
                button = QtWidgets.QPushButton(label)
                button.setProperty("nav", True)
                button.setCheckable(True)
                button.clicked.connect(lambda checked=False, page=index: self.show_page(page))
                self.nav_buttons.append(button)
                side.addWidget(button)
            side.addStretch()
            settings = QtWidgets.QPushButton("Pengaturan")
            settings.setProperty("nav", True)
            settings.setCheckable(True)
            settings.clicked.connect(lambda: self.show_page(4))
            self.nav_buttons.append(settings)
            side.addWidget(settings)
            layout.addWidget(sidebar)
            workspace = QtWidgets.QWidget(objectName="workspace")
            workspace_layout = QtWidgets.QVBoxLayout(workspace)
            workspace_layout.setContentsMargins(0, 0, 0, 0)
            workspace_layout.setSpacing(0)
            topbar = QtWidgets.QFrame(objectName="topbar")
            topbar_layout = QtWidgets.QHBoxLayout(topbar)
            topbar_layout.setContentsMargins(38, 12, 38, 12)
            topbar_layout.addWidget(QtWidgets.QLabel("Assessment Operations", objectName="topbarTitle"))
            topbar_layout.addStretch()
            self.system_status = QtWidgets.QLabel("Memeriksa sistem", objectName="statusBadge")
            self.system_status.setProperty("status", "working")
            topbar_layout.addWidget(self.system_status)
            workspace_layout.addWidget(topbar)
            workspace_layout.addWidget(self.pages, 1)
            layout.addWidget(workspace, 1)
            self.setCentralWidget(central)

        def _set_system_status(self, text: str, status: str):
            self.system_status.setText(text)
            self.system_status.setProperty("status", status)
            self.system_status.style().unpolish(self.system_status)
            self.system_status.style().polish(self.system_status)

        def _page(self, title: str, subtitle: str):
            page = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(page)
            layout.setContentsMargins(38, 32, 38, 32)
            layout.setSpacing(16)
            heading = QtWidgets.QLabel(title)
            heading.setProperty("title", True)
            description = QtWidgets.QLabel(subtitle)
            description.setProperty("subtitle", True)
            description.setWordWrap(True)
            layout.addWidget(heading)
            layout.addWidget(description)
            return page, layout

        def _card(self):
            card = QtWidgets.QFrame()
            card.setProperty("card", True)
            card.setLayout(QtWidgets.QVBoxLayout())
            card.layout().setContentsMargins(22, 20, 22, 20)
            card.layout().setSpacing(10)
            return card

        def _build_pages(self):
            self.home, home = self._page("Selamat datang", "Periksa kesiapan sistem sebelum memulai batch assessment.")
            metrics = QtWidgets.QHBoxLayout()
            ready_card = self._card()
            self.ready_count = QtWidgets.QLabel("—")
            self.ready_count.setProperty("kpi", True)
            ready_card.layout().addWidget(self.ready_count)
            ready_card.layout().addWidget(QtWidgets.QLabel("peserta siap diproses"))
            metrics.addWidget(ready_card)
            previous = self._card()
            self.previous_label = QtWidgets.QLabel("Belum ada riwayat proses")
            self.previous_label.setWordWrap(True)
            previous.layout().addWidget(QtWidgets.QLabel("Batch sebelumnya"))
            previous.layout().addWidget(self.previous_label)
            metrics.addWidget(previous)
            home.addLayout(metrics)
            checks = self._card()
            check_title = QtWidgets.QLabel("Pemeriksaan sebelum mulai")
            check_title.setStyleSheet("font-size: 18px; font-weight: 650;")
            checks.layout().addWidget(check_title)
            self.check_label = QtWidgets.QLabel("Memeriksa data peserta, Frexor, dan folder hasil...")
            self.check_label.setWordWrap(True)
            checks.layout().addWidget(self.check_label)
            home.addWidget(checks)
            actions = QtWidgets.QHBoxLayout()
            self.recheck_button = QtWidgets.QPushButton("Periksa Lagi")
            self.recheck_button.clicked.connect(self.run_preflight)
            self.start_button = QtWidgets.QPushButton("Mulai Proses")
            self.start_button.setProperty("primary", True)
            self.start_button.setEnabled(False)
            self.start_button.clicked.connect(lambda: self.start_batch("run"))
            self.retry_button = QtWidgets.QPushButton("Lanjutkan / Coba Lagi")
            self.retry_button.setEnabled(False)
            self.retry_button.clicked.connect(lambda: self.start_batch("retry"))
            actions.addStretch()
            actions.addWidget(self.recheck_button)
            actions.addWidget(self.retry_button)
            actions.addWidget(self.start_button)
            home.addLayout(actions)
            home.addStretch()
            self.pages.addWidget(self.home)

            self.run_page, run = self._page("Proses Assessment", "Frexor sedang digunakan oleh automation.")
            current = self._card()
            self.current_label = QtWidgets.QLabel("Menunggu proses dimulai")
            self.current_label.setStyleSheet("font-size: 20px; font-weight: 650;")
            self.stage_label = QtWidgets.QLabel("○ Data  ○ DISC  ○ VAK  ○ IQ  ○ Kirim  ○ PDF")
            self.batch_bar = QtWidgets.QProgressBar()
            self.batch_bar.setTextVisible(False)
            self.batch_stats = QtWidgets.QLabel("Berhasil 0   Bermasalah 0   Tersisa 0")
            current.layout().addWidget(self.current_label)
            current.layout().addWidget(self.stage_label)
            current.layout().addWidget(self.batch_bar)
            current.layout().addWidget(self.batch_stats)
            run.addWidget(current)
            self.stop_button = QtWidgets.QPushButton("Hentikan Proses")
            self.stop_button.setProperty("danger", True)
            self.stop_button.setEnabled(False)
            self.stop_button.clicked.connect(self.request_stop)
            run.addWidget(self.stop_button, alignment=QtCore.Qt.AlignRight)
            run.addStretch()
            self.pages.addWidget(self.run_page)

            self.participant_page, participants_layout = self._page(
                "Peserta", "Tinjau peserta siap, selesai, atau perlu diperiksa."
            )
            participant_tools = QtWidgets.QHBoxLayout()
            self.participant_search = QtWidgets.QLineEdit()
            self.participant_search.setPlaceholderText("Cari nama atau ID peserta...")
            self.participant_search.setClearButtonEnabled(True)
            self.participant_filter = QtWidgets.QComboBox()
            self.participant_filter.addItems(
                ("Semua status", "Siap diproses", "Berjalan", "Selesai", "Perlu diperiksa")
            )
            self.participant_search.textChanged.connect(self._apply_participant_filter)
            self.participant_filter.currentIndexChanged.connect(self._apply_participant_filter)
            participant_tools.addWidget(self.participant_search, 1)
            participant_tools.addWidget(self.participant_filter)
            participants_layout.addLayout(participant_tools)
            self.participant_table = QtWidgets.QTableWidget(0, 6)
            self.participant_table.setHorizontalHeaderLabels(("ID Peserta", "Nama", "DISC", "VAK", "IQ", "Status akhir"))
            header = self.participant_table.horizontalHeader()
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
            header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
            for column in (2, 3, 4, 5):
                header.setSectionResizeMode(column, QtWidgets.QHeaderView.Fixed)
            self.participant_table.setColumnWidth(0, 132)
            self.participant_table.setColumnWidth(2, 112)
            self.participant_table.setColumnWidth(3, 112)
            self.participant_table.setColumnWidth(4, 112)
            self.participant_table.setColumnWidth(5, 168)
            self.participant_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            self.participant_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.participant_table.setAlternatingRowColors(True)
            self.participant_table.verticalHeader().setVisible(False)
            self.participant_table.verticalHeader().setDefaultSectionSize(54)
            self.participant_table.cellDoubleClicked.connect(self.show_participant_detail)
            participants_layout.addWidget(self.participant_table)
            self.pages.addWidget(self.participant_page)

            self.result_page, results = self._page("Hasil", "Ringkasan batch dan lokasi PDF terverifikasi.")
            result_card = self._card()
            self.result_title = QtWidgets.QLabel("Belum ada batch selesai")
            self.result_title.setStyleSheet("font-size: 22px; font-weight: 650;")
            self.result_summary = QtWidgets.QLabel("Jalankan pemeriksaan lalu mulai proses.")
            self.open_results = QtWidgets.QPushButton("Buka Folder Hasil")
            self.open_results.clicked.connect(self.open_result_folder)
            result_card.layout().addWidget(self.result_title)
            result_card.layout().addWidget(self.result_summary)
            result_card.layout().addWidget(self.open_results, alignment=QtCore.Qt.AlignLeft)
            results.addWidget(result_card)
            results.addStretch()
            self.pages.addWidget(self.result_page)

            self.settings_page, settings = self._page(
                "Pengaturan", "Pengaturan ini ditujukan untuk administrator atau teknisi."
            )
            settings_card = self._card()
            self.settings_info = QtWidgets.QLabel()
            self.settings_info.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            self.settings_info.setWordWrap(True)
            reload_button = QtWidgets.QPushButton("Jalankan Pemeriksaan Lengkap")
            reload_button.clicked.connect(self.run_preflight)
            setup_button = QtWidgets.QPushButton("Ubah Konfigurasi")
            setup_button.clicked.connect(self.rerun_setup)
            settings_card.layout().addWidget(self.settings_info)
            settings_card.layout().addWidget(setup_button, alignment=QtCore.Qt.AlignLeft)
            settings_card.layout().addWidget(reload_button, alignment=QtCore.Qt.AlignLeft)
            settings.addWidget(settings_card)
            settings.addStretch()
            self.pages.addWidget(self.settings_page)
            self.show_page(0)
            self._refresh_settings()

        def show_page(self, index: int):
            self.pages.setCurrentIndex(index)
            for current, button in enumerate(self.nav_buttons):
                button.setChecked(current == index)

        def _refresh_settings(self):
            try:
                config = load_config(config_path)
                source_info = {
                    "google_sheets": f"Google Sheets\nSpreadsheet: {config.sheets.spreadsheet_id}",
                    "excel": f"Excel Lokal\n{config.excel.workbook_path}",
                    "api": f"API\n{config.api.base_url}",
                }.get(config.data_source, config.data_source)
                self.settings_info.setText(
                    f"Sumber data\n{source_info}\n\n"
                    f"Frexor\n{config.frexor.executable_path}\n\n"
                    f"Folder PDF DISC\n{config.pdf.base_directory / config.pdf.module_directories['DISC']}\n\n"
                    f"Folder PDF VAK\n{config.pdf.base_directory / config.pdf.module_directories['VAK']}\n\n"
                    f"Folder PDF IQ\n{config.pdf.base_directory / config.pdf.module_directories['IQ']}\n\n"
                    f"Folder arsip hasil\n{config.pdf.output_directory}"
                )
            except Exception as exc:
                self.settings_info.setText(f"Konfigurasi belum lengkap.\n{exc}")

        def _show_previous_state(self):
            state = self.state_store.load()
            if state.lifecycle not in {"IDLE", "COMPLETED"}:
                self.previous_label.setText(
                    f"Proses sebelumnya: {state.lifecycle}\n"
                    f"Berhasil {state.success}, bermasalah {state.failed}.\n"
                    "Lakukan pemeriksaan sebelum melanjutkan."
                )
            elif state.lifecycle == "COMPLETED":
                self.previous_label.setText(
                    f"Selesai: {state.success} berhasil, {state.failed} perlu diperiksa."
                )

        def _restore_window_state(self):
            settings = QtCore.QSettings()
            geometry = settings.value("main/geometry")
            if geometry:
                self.restoreGeometry(geometry)
            last_page = int(settings.value("main/page", 0))
            self.show_page(max(0, min(last_page, self.pages.count() - 1)))

        def _launch_worker(self, mode: str):
            if self.thread and self.thread.isRunning():
                return
            self.thread = QtCore.QThread(self)
            self.worker = EngineWorker(mode)
            self.worker.moveToThread(self.thread)
            self.thread.started.connect(self.worker.run)
            self.worker.preflight_ready.connect(self.on_preflight)
            self.worker.progress.connect(self.on_progress)
            self.worker.batch_progress.connect(self.on_batch_progress)
            self.worker.completed.connect(self.on_completed)
            self.worker.failed.connect(self.on_failed)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            self.thread.finished.connect(self._thread_finished)
            self.thread.start()

        def _thread_finished(self):
            self.thread = None
            self.worker = None

        def run_preflight(self):
            self.start_button.setEnabled(False)
            self.recheck_button.setEnabled(False)
            self.check_label.setText("Memeriksa data peserta, Frexor, dan folder hasil...")
            self._set_system_status("Memeriksa sistem", "working")
            self._launch_worker("preflight")

        @QtCore.Slot(object)
        def on_preflight(self, payload):
            validations, self.participants = payload
            self.validation_errors = {r.participant_id: r.errors for r in validations if not r.valid}
            retryable_ids = {
                p.participant_id for p in self.participants if Status.ERROR in p.module_statuses.values()
            }
            for participant_id in retryable_ids:
                self.validation_errors.setdefault(participant_id, []).append(
                    "Assessment sebelumnya gagal dan memerlukan Coba Lagi."
                )
            ready = sum(
                1 for result in validations
                if result.valid and result.participant_id not in retryable_ids
            )
            invalid = len(self.validation_errors)
            retryable = len(retryable_ids)
            self.ready_count.setText(str(ready))
            if invalid:
                self.check_label.setText(
                    f"⚠ {invalid} peserta perlu diperiksa. Buka halaman Peserta untuk melihat detail."
                )
                self.check_label.setProperty("warning", True)
                self.start_button.setEnabled(False)
                self._set_system_status("Perlu diperiksa", "error")
            else:
                self.check_label.setText(
                    f"✓ Data peserta tersedia\n✓ {ready} peserta siap diproses\n"
                    "✓ Frexor tersedia\n✓ Folder hasil tersedia\n\nSemua siap."
                )
                self.check_label.setProperty("success", True)
                self.start_button.setEnabled(ready > 0)
                self._set_system_status("Sistem siap", "ready")
            self.retry_button.setEnabled(retryable > 0)
            self.check_label.style().unpolish(self.check_label)
            self.check_label.style().polish(self.check_label)
            self._fill_participants()
            self.recheck_button.setEnabled(True)

        def _fill_participants(self):
            self._apply_participant_filter()

        @staticmethod
        def _status_display(status: Status, has_error: bool = False):
            if has_error or status is Status.ERROR:
                return "! Periksa", "error"
            mapping = {
                Status.DONE: ("✓ Selesai", "success"),
                Status.READY: ("○ Siap", "ready"),
                Status.PARTIAL: ("◐ Sebagian", "working"),
                Status.PROCESSING: ("● Berjalan", "working"),
                Status.SKIPPED: ("— Dilewati", "ready"),
            }
            return mapping.get(status, (status.value.title(), "ready"))

        def _status_item(self, text: str, kind: str):
            colors = {
                "success": ("#dceee4", "#17633f"),
                "ready": ("#e7ece7", "#53615d"),
                "working": ("#fff0c9", "#7b5100"),
                "error": ("#f8dfdc", "#8c2f28"),
            }
            background, foreground = colors[kind]
            item = QtWidgets.QTableWidgetItem(text)
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            item.setBackground(QtGui.QColor(background))
            item.setForeground(QtGui.QColor(foreground))
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            return item

        def _apply_participant_filter(self):
            if not hasattr(self, "participant_table"):
                return
            query = self.participant_search.text().strip().casefold()
            selected_filter = self.participant_filter.currentText()
            self.filtered_participants = []
            for participant in self.participants:
                has_error = participant.participant_id in self.validation_errors
                if query and query not in participant.participant_id.casefold() and query not in participant.name.casefold():
                    continue
                if selected_filter == "Siap diproses" and participant.overall_status not in {Status.READY, Status.PARTIAL}:
                    continue
                if selected_filter == "Berjalan" and participant.overall_status is not Status.PROCESSING:
                    continue
                if selected_filter == "Selesai" and participant.overall_status is not Status.DONE:
                    continue
                if selected_filter == "Perlu diperiksa" and not has_error:
                    continue
                self.filtered_participants.append(participant)

            self.participant_table.setRowCount(len(self.filtered_participants))
            for row, participant in enumerate(self.filtered_participants):
                errors = self.validation_errors.get(participant.participant_id, [])
                id_item = QtWidgets.QTableWidgetItem(participant.participant_id)
                name_item = QtWidgets.QTableWidgetItem(participant.name)
                name_font = name_item.font()
                name_font.setBold(True)
                name_item.setFont(name_font)
                if errors:
                    tooltip = "\n".join(errors)
                    id_item.setToolTip(tooltip)
                    name_item.setToolTip(tooltip)
                self.participant_table.setItem(row, 0, id_item)
                self.participant_table.setItem(row, 1, name_item)

                for column, module in enumerate((Module.DISC, Module.VAK, Module.IQ), start=2):
                    text, kind = self._status_display(participant.module_statuses[module])
                    self.participant_table.setItem(row, column, self._status_item(text, kind))

                text, kind = self._status_display(
                    participant.overall_status,
                    participant.participant_id in self.validation_errors,
                )
                result_item = self._status_item(text, kind)
                if errors:
                    result_item.setToolTip("\n".join(errors))
                self.participant_table.setItem(row, 5, result_item)

        def show_participant_detail(self, row: int, column: int):
            participant_id = self.participant_table.item(row, 0).text()
            errors = self.validation_errors.get(participant_id)
            if not errors:
                QtWidgets.QMessageBox.information(
                    self, "Status peserta", "Tidak ada masalah validasi yang ditemukan."
                )
                return
            QtWidgets.QMessageBox.warning(
                self, "Peserta perlu diperiksa", "\n".join(f"• {error}" for error in errors)
            )

        def start_batch(self, mode: str):
            self.show_page(1)
            self.stop_button.setEnabled(True)
            self._set_system_status("Automation berjalan", "working")
            self.state_store.save(RunState(lifecycle="RUNNING"))
            self._launch_worker(mode)

        @QtCore.Slot(str, str, int, int)
        def on_progress(self, participant_id, module, current, total):
            self.current_label.setText(f"{participant_id} · {module}")
            self.stage_label.setText(f"Sedang mengisi {module}: soal {current} dari {total}")

        @QtCore.Slot(object)
        def on_batch_progress(self, payload):
            summary, participant_id = payload
            processed = summary.success + summary.failed
            self.batch_bar.setMaximum(max(summary.total, 1))
            self.batch_bar.setValue(processed + summary.skipped)
            remaining = max(summary.total - processed - summary.skipped, 0)
            self.batch_stats.setText(
                f"Berhasil {summary.success}   Bermasalah {summary.failed}   Tersisa {remaining}"
            )
            if participant_id:
                self.current_label.setText(f"Memproses peserta {participant_id}")
            self.state_store.save(RunState(
                lifecycle="RUNNING", current_participant_id=participant_id,
                total=summary.total, success=summary.success, failed=summary.failed,
                skipped=summary.skipped,
            ))

        def request_stop(self):
            answer = QtWidgets.QMessageBox.question(
                self, "Hentikan proses?",
                "Program akan menyelesaikan langkah aman yang sedang berjalan sebelum berhenti.",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            )
            if answer == QtWidgets.QMessageBox.Yes and self.worker:
                self.worker.request_stop()
                self.stop_button.setEnabled(False)
                self.stage_label.setText("Permintaan berhenti diterima. Menunggu titik aman...")

        @QtCore.Slot(object)
        def on_completed(self, summary):
            self.stop_button.setEnabled(False)
            self.result_title.setText(
                "Proses selesai" if summary.failed == 0 else "Proses selesai dengan peserta yang perlu diperiksa"
            )
            self.result_summary.setText(
                f"{summary.total} peserta\n{summary.success} berhasil\n"
                f"{summary.failed} perlu diperiksa\n{summary.skipped} dilewati"
            )
            self.state_store.save(RunState(
                lifecycle="COMPLETED" if summary.failed == 0 else "PAUSED_FOR_REVIEW",
                total=summary.total, success=summary.success, failed=summary.failed,
                skipped=summary.skipped,
            ))
            self._set_system_status(
                "Proses selesai" if summary.failed == 0 else "Selesai dengan masalah",
                "ready" if summary.failed == 0 else "error",
            )
            self.show_page(3)
            QtWidgets.QApplication.alert(self)

        @QtCore.Slot(str, str)
        def on_failed(self, code: str, technical: str):
            self.stop_button.setEnabled(False)
            message = friendly_error(code, technical)
            dialog = QtWidgets.QMessageBox(self)
            dialog.setIcon(QtWidgets.QMessageBox.Warning)
            dialog.setWindowTitle(message.title)
            dialog.setText(message.description)
            dialog.setInformativeText(message.action)
            dialog.setDetailedText(technical)
            dialog.exec()
            self.check_label.setText(f"⚠ {message.title}\n{message.action}")
            self.state_store.save(RunState(lifecycle="PAUSED_FOR_REVIEW", last_error_code=code))
            self._set_system_status("Proses dihentikan", "error")
            self.show_page(0)
            self.recheck_button.setEnabled(True)

        def open_result_folder(self):
            try:
                directory = load_config(config_path).pdf.output_directory
                QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(directory)))
            except Exception as exc:
                QtWidgets.QMessageBox.warning(self, "Folder tidak dapat dibuka", str(exc))

        def rerun_setup(self):
            if SetupWizard.run(config_path):
                self._refresh_settings()
                self.run_preflight()

        def closeEvent(self, event):
            if self.thread and self.thread.isRunning():
                QtWidgets.QMessageBox.information(
                    self, "Proses masih berjalan",
                    "Hentikan proses dan tunggu sampai titik aman sebelum menutup aplikasi.",
                )
                event.ignore()
                return
            settings = QtCore.QSettings()
            settings.setValue("main/geometry", self.saveGeometry())
            settings.setValue("main/page", self.pages.currentIndex())
            settings.sync()
            event.accept()

    window = MainWindow()
    window.show()
    app.exec()
