"""Custom exception hierarchy for AutoBuilder."""

from app.models.enums import ErrorCode


class AutoBuilderError(Exception):
    """Base exception for all AutoBuilder application errors."""

    code: ErrorCode
    message: str
    details: dict[str, object]

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class NotFoundError(AutoBuilderError):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, code=ErrorCode.NOT_FOUND, details=details)


class ConflictError(AutoBuilderError):
    """Raised when an operation conflicts with the current state."""

    def __init__(
        self,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, code=ErrorCode.CONFLICT, details=details)


class ValidationError(AutoBuilderError):
    """Raised when input data fails validation."""

    def __init__(
        self,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, code=ErrorCode.VALIDATION_ERROR, details=details)


class ConfigurationError(AutoBuilderError):
    """Raised when configuration is missing or invalid."""

    def __init__(
        self,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, code=ErrorCode.CONFIGURATION_ERROR, details=details)


class WorkerError(AutoBuilderError):
    """Raised when a worker encounters an execution error."""

    def __init__(
        self,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        super().__init__(message, code=ErrorCode.WORKER_ERROR, details=details)
