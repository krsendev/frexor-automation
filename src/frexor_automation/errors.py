class AutomationError(Exception):
    """Base exception for controlled automation failures."""


class ConfigurationError(AutomationError):
    pass


class DataValidationError(AutomationError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


class FrexorError(AutomationError):
    code = "FREXOR_ERROR"


class UnsafeUiStateError(FrexorError):
    code = "UNSAFE_UI_STATE"


class LoginRequiredError(FrexorError):
    code = "LOGIN_REQUIRED"


class SubmissionNotVerifiedError(FrexorError):
    code = "SUBMISSION_NOT_VERIFIED"


class PdfError(AutomationError):
    code = "PDF_ERROR"


class PdfTimeoutError(PdfError):
    code = "PDF_TIMEOUT"


class PdfInvalidError(PdfError):
    code = "PDF_INVALID"


class PdfAssociationError(PdfError):
    code = "PDF_ASSOCIATION_FAILED"


class PdfMergeError(PdfError):
    code = "PDF_MERGE_FAILED"
