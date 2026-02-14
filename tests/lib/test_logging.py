"""Tests for structured logging setup."""

import json
import logging
import re
import sys

from app.lib import JsonFormatter, get_logger, setup_logging


class TestSetupLogging:
    def test_configures_app_logger(self) -> None:
        setup_logging("DEBUG")
        app_logger = logging.getLogger("app")
        assert app_logger.level == logging.DEBUG
        assert len(app_logger.handlers) > 0

    def test_sets_info_level_by_default(self) -> None:
        setup_logging()
        app_logger = logging.getLogger("app")
        assert app_logger.level == logging.INFO

    def test_clears_existing_handlers(self) -> None:
        setup_logging("INFO")
        setup_logging("DEBUG")
        app_logger = logging.getLogger("app")
        # Should have exactly one handler after repeated calls
        assert len(app_logger.handlers) == 1

    def test_disables_propagation(self) -> None:
        setup_logging("INFO")
        app_logger = logging.getLogger("app")
        assert app_logger.propagate is False


class TestGetLogger:
    def test_returns_child_of_app(self) -> None:
        logger = get_logger("gateway")
        assert logger.name == "app.gateway"

    def test_nested_name(self) -> None:
        logger = get_logger("gateway.routes")
        assert logger.name == "app.gateway.routes"

    def test_returns_logging_logger(self) -> None:
        logger = get_logger("test")
        assert isinstance(logger, logging.Logger)


class TestJsonFormatter:
    def test_formats_json_output(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test message",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["logger"] == "app.test"
        assert data["message"] == "test message"
        assert "timestamp" in data

    def test_includes_extras(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test",
            args=None,
            exc_info=None,
        )
        record.method = "GET"  # type: ignore[attr-defined]
        record.path = "/health"  # type: ignore[attr-defined]
        output = formatter.format(record)
        data = json.loads(output)
        assert data["method"] == "GET"
        assert data["path"] == "/health"

    def test_excludes_standard_keys(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="test",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        # Standard LogRecord attributes should not appear as top-level keys
        assert "pathname" not in data
        assert "lineno" not in data
        assert "funcName" not in data

    def test_output_is_valid_json(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="app.test",
            level=logging.WARNING,
            pathname="",
            lineno=0,
            msg="warning message",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        # Should not raise
        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_timestamp_is_iso8601_utc(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        ts = data["timestamp"]
        # Must be ISO 8601 with UTC offset +00:00
        assert re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", ts)
        assert ts.endswith("+00:00")

    def test_includes_exception_info(self) -> None:
        formatter = JsonFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            exc_info = sys.exc_info()
        record = logging.LogRecord(
            name="app.test",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="error occurred",
            args=None,
            exc_info=exc_info,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert "exception" in data
        assert "ValueError" in data["exception"]
        assert "boom" in data["exception"]

    def test_includes_stack_info(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test",
            args=None,
            exc_info=None,
        )
        record.stack_info = "Stack (most recent call last):\n  File test.py"
        output = formatter.format(record)
        data = json.loads(output)
        assert data["stack_info"] == "Stack (most recent call last):\n  File test.py"

    def test_handles_non_serializable_extras(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test",
            args=None,
            exc_info=None,
        )
        record.my_obj = object()  # type: ignore[attr-defined]
        # Should not raise -- default=str handles non-serializable values
        output = formatter.format(record)
        data = json.loads(output)
        assert "my_obj" in data

    def test_multiline_message_preserved(self) -> None:
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="app.test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="line1\nline2\nline3",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        data = json.loads(output)
        assert data["message"] == "line1\nline2\nline3"
