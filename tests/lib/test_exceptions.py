"""Tests for custom exception hierarchy."""

from app.lib import (
    AutoBuilderError,
    ConfigurationError,
    ConflictError,
    NotFoundError,
    ValidationError,
    WorkerError,
)
from app.models.enums import ErrorCode


class TestAutoBuilderError:
    def test_base_error(self) -> None:
        err = AutoBuilderError("test error")
        assert err.code == ErrorCode.INTERNAL_ERROR
        assert err.message == "test error"
        assert err.details == {}
        assert str(err) == "test error"

    def test_with_details(self) -> None:
        err = AutoBuilderError("test", details={"key": "value"})
        assert err.details == {"key": "value"}

    def test_with_custom_code(self) -> None:
        err = AutoBuilderError("test", code=ErrorCode.NOT_FOUND)
        assert err.code == ErrorCode.NOT_FOUND

    def test_inherits_from_exception(self) -> None:
        err = AutoBuilderError("test")
        assert isinstance(err, Exception)


class TestNotFoundError:
    def test_code(self) -> None:
        err = NotFoundError("resource not found")
        assert err.code == ErrorCode.NOT_FOUND

    def test_inherits_from_base(self) -> None:
        err = NotFoundError("missing")
        assert isinstance(err, AutoBuilderError)

    def test_with_details(self) -> None:
        err = NotFoundError("missing", details={"id": "abc"})
        assert err.details == {"id": "abc"}


class TestConflictError:
    def test_code(self) -> None:
        err = ConflictError("already exists")
        assert err.code == ErrorCode.CONFLICT

    def test_inherits_from_base(self) -> None:
        assert isinstance(ConflictError("dup"), AutoBuilderError)


class TestValidationError:
    def test_code(self) -> None:
        err = ValidationError("invalid input")
        assert err.code == ErrorCode.VALIDATION_ERROR

    def test_inherits_from_base(self) -> None:
        assert isinstance(ValidationError("bad"), AutoBuilderError)


class TestConfigurationError:
    def test_code(self) -> None:
        err = ConfigurationError("missing config")
        assert err.code == ErrorCode.CONFIGURATION_ERROR

    def test_inherits_from_base(self) -> None:
        assert isinstance(ConfigurationError("bad"), AutoBuilderError)


class TestWorkerError:
    def test_code(self) -> None:
        err = WorkerError("worker failed")
        assert err.code == ErrorCode.WORKER_ERROR

    def test_inherits_from_base(self) -> None:
        assert isinstance(WorkerError("fail"), AutoBuilderError)


class TestAllSubclasses:
    def test_all_inherit_from_base(self) -> None:
        subclasses = [
            NotFoundError,
            ConflictError,
            ValidationError,
            ConfigurationError,
            WorkerError,
        ]
        for cls in subclasses:
            assert issubclass(cls, AutoBuilderError)

    def test_all_catchable_as_exception(self) -> None:
        subclasses = [
            NotFoundError,
            ConflictError,
            ValidationError,
            ConfigurationError,
            WorkerError,
        ]
        for cls in subclasses:
            assert issubclass(cls, Exception)
