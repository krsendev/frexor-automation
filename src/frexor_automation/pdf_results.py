from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import time
from uuid import uuid4

from .config import PdfConfig
from .domain import Module, Participant, frexor_identity
from .errors import PdfAssociationError, PdfInvalidError, PdfMergeError, PdfTimeoutError


@dataclass(frozen=True)
class FileState:
    size: int
    modified_ns: int


Snapshot = dict[Path, FileState]


class PdfResultManager:
    def __init__(self, config: PdfConfig):
        self.config = config

    def check_environment(self) -> None:
        if not self.config.base_directory.exists():
            raise PdfInvalidError(f"PDF base directory not found: {self.config.base_directory}")
        for module in Module:
            directory = self._watch_directory(module)
            if not directory.is_dir():
                raise PdfInvalidError(f"PDF directory for {module} not found: {directory}")
        self.config.output_directory.mkdir(parents=True, exist_ok=True)

    def snapshot(self, module: Module) -> Snapshot:
        result = {}
        for path in self._watch_directory(module).glob("*.pdf"):
            try:
                if path.is_file():
                    state = path.stat()
                    result[path.resolve()] = FileState(state.st_size, state.st_mtime_ns)
            except OSError:
                continue
        return result

    def existing_result(self, participant: Participant, module: Module) -> Path | None:
        destination = self._destination(participant, module)
        if not destination.exists():
            return None
        self._validate(destination)
        return destination.resolve()

    def merge_results(self, participant: Participant) -> Path:
        sources = [self._destination(participant, module) for module in Module]
        for source in sources:
            if not source.exists():
                raise PdfMergeError(f"PDF source for merge not found: {source}")
            try:
                self._validate(source)
            except PdfInvalidError as exc:
                raise PdfMergeError(f"Invalid PDF source for merge: {source}") from exc

        destination = self._merged_destination(participant)
        if destination.exists():
            try:
                self._validate_merged(destination, sources)
            except (PdfInvalidError, PdfMergeError) as exc:
                raise PdfMergeError(f"Existing merged PDF is invalid: {destination}") from exc
            return destination.resolve()

        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError as exc:
            raise PdfMergeError("Install worker dependencies to merge PDF results") from exc

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(
            f".{destination.stem}.{uuid4().hex}.tmp.pdf"
        )
        writer = PdfWriter()
        try:
            for source in sources:
                reader = PdfReader(source)
                if reader.is_encrypted:
                    raise PdfMergeError(f"Encrypted PDF cannot be merged: {source}")
                if not reader.pages:
                    raise PdfMergeError(f"PDF has no pages: {source}")
                writer.append(source, import_outline=False)
            writer.write(temporary)
            self._validate_merged(temporary, sources)
            temporary.replace(destination)
            return destination.resolve()
        except PdfMergeError:
            raise
        except Exception as exc:
            raise PdfMergeError(f"Failed to merge PDF results: {exc}") from exc
        finally:
            writer.close()
            temporary.unlink(missing_ok=True)

    def wait_for_result(
        self, before: Snapshot, participant: Participant, module: Module
    ) -> Path:
        deadline = time.monotonic() + self.config.timeout_seconds
        stable_candidate: Path | None = None
        stable_state: FileState | None = None
        stable_since = 0.0
        while time.monotonic() < deadline:
            current = self.snapshot(module)
            changed = [path for path, state in current.items() if before.get(path) != state]
            if len(changed) > 1:
                raise PdfAssociationError(f"Multiple PDFs changed after {module} submit: {changed}")
            if len(changed) == 1:
                candidate = changed[0]
                state = current[candidate]
                if candidate != stable_candidate or state != stable_state:
                    stable_candidate = candidate
                    stable_state = state
                    stable_since = time.monotonic()
                elif time.monotonic() - stable_since >= self.config.stable_seconds:
                    self._validate(candidate)
                    self._validate_association(candidate, participant, module)
                    return self._archive(candidate, participant, module)
            time.sleep(self.config.poll_interval_seconds)
        raise PdfTimeoutError(f"No stable PDF detected for {participant.participant_id} {module}")

    def _validate(self, path: Path) -> None:
        if path.suffix.lower() != ".pdf":
            raise PdfInvalidError(f"Unexpected result extension: {path}")
        if path.stat().st_size < self.config.minimum_size_bytes:
            raise PdfInvalidError(f"PDF is too small: {path}")
        try:
            with path.open("rb") as handle:
                header = handle.read(5)
                handle.seek(-min(path.stat().st_size, 1024), 2)
                trailer = handle.read()
        except OSError as exc:
            raise PdfInvalidError(f"PDF is not readable: {path}") from exc
        if header != b"%PDF-" or b"%%EOF" not in trailer:
            raise PdfInvalidError(f"Invalid PDF structure: {path}")

    def _archive(self, source: Path, participant: Participant, module: Module) -> Path:
        destination = self._destination(participant, module)
        participant_dir = destination.parent
        participant_dir.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            raise PdfAssociationError(f"Result already exists and will not be overwritten: {destination}")
        shutil.copy2(source, destination)
        self._validate(destination)
        return destination.resolve()

    def _watch_directory(self, module: Module) -> Path:
        folder = self.config.module_directories.get(module.value)
        if not folder:
            raise PdfInvalidError(f"PDF directory mapping is missing for {module}")
        return self.config.base_directory / folder

    def _validate_association(self, path: Path, participant: Participant, module: Module) -> None:
        if participant.test_date is None:
            raise PdfAssociationError(
                f"Participant test_date is missing for {participant.participant_id}"
            )
        expected = self._normalized(
            f"Hasil {module.value} {participant.test_date.isoformat()} "
            f"{frexor_identity(participant.position)} {frexor_identity(participant.name)}"
        )
        actual = self._normalized(path.stem)
        if actual != expected:
            raise PdfAssociationError(
                f"Unexpected PDF filename for {participant.participant_id} {module}: {path.name}"
            )

    def _destination(self, participant: Participant, module: Module) -> Path:
        participant_dir = self.config.output_directory / self._safe_name(
            f"{participant.participant_id}_{participant.name}"
        )
        return participant_dir / f"{module.value}.pdf"

    def _merged_destination(self, participant: Participant) -> Path:
        if participant.test_date is None:
            raise PdfMergeError(
                f"Participant test_date is missing for {participant.participant_id}"
            )
        filename = (
            f"Hasil Psikotes {participant.test_date.strftime('%d-%m-%Y')} "
            f"{frexor_identity(participant.position)} {frexor_identity(participant.name)}.pdf"
        )
        return self._destination(participant, Module.DISC).parent / filename

    def _validate_merged(self, path: Path, sources: list[Path]) -> None:
        self._validate(path)
        try:
            from pypdf import PdfReader

            expected_pages = sum(len(PdfReader(source).pages) for source in sources)
            actual_pages = len(PdfReader(path).pages)
        except Exception as exc:
            raise PdfMergeError(f"Merged PDF cannot be read: {path}") from exc
        if expected_pages <= 0 or actual_pages != expected_pages:
            raise PdfMergeError(
                f"Merged PDF page count mismatch: expected {expected_pages}, found {actual_pages}"
            )

    @staticmethod
    def _safe_name(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
        return cleaned.strip("._") or "participant"

    @staticmethod
    def _normalized(value: str) -> str:
        return " ".join(value.split()).casefold()


class MockPdfResultManager:
    def __init__(self):
        self.actions: list[str] = []

    def check_environment(self) -> None:
        self.actions.append("check_environment")

    def snapshot(self, module: Module) -> Snapshot:
        self.actions.append("snapshot")
        return {}

    def wait_for_result(self, before: Snapshot, participant: Participant, module: Module) -> Path:
        self.actions.append(f"result:{participant.participant_id}:{module}")
        return Path(f"/mock/{participant.participant_id}/{module.value}.pdf")

    def existing_result(self, participant: Participant, module: Module) -> Path | None:
        self.actions.append(f"existing:{participant.participant_id}:{module}")
        return None

    def merge_results(self, participant: Participant) -> Path:
        self.actions.append(f"merge:{participant.participant_id}")
        test_date = participant.test_date.strftime("%d-%m-%Y") if participant.test_date else "unknown-date"
        filename = (
            f"Hasil Psikotes {test_date} "
            f"{frexor_identity(participant.position)} {frexor_identity(participant.name)}.pdf"
        )
        return Path(f"/mock/{participant.participant_id}/{filename}")
