"""Structured JSON logging for the AutoBuilder application."""

import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects.

    Output schema:
        {"timestamp": "ISO8601", "level": "...", "logger": "...", "message": "...", ...extras}
    """

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge user-supplied extras (skip standard LogRecord attributes)
        standard_keys = {
            "name",
            "msg",
            "args",
            "created",
            "relativeCreated",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "pathname",
            "filename",
            "module",
            "thread",
            "threadName",
            "process",
            "processName",
            "levelname",
            "levelno",
            "msecs",
            "message",
            "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in standard_keys and not key.startswith("_"):
                entry[key] = value

        if record.exc_info and record.exc_info[1] is not None:
            entry["exception"] = self.formatException(record.exc_info)

        if record.stack_info:
            entry["stack_info"] = record.stack_info

        return json.dumps(entry, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configure the root ``app`` logger with JSON output.

    Clears any existing handlers on the ``app`` logger and attaches a single
    :class:`StreamHandler` using :class:`JsonFormatter`.

    Args:
        level: Log level name (e.g. ``"INFO"``, ``"DEBUG"``).
    """
    logger = logging.getLogger("app")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicate output on repeated calls
    logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    # Prevent propagation to the root logger
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the ``app.*`` hierarchy.

    Example:
        ``get_logger("gateway")`` returns the logger named ``app.gateway``.
    """
    return logging.getLogger(f"app.{name}")
