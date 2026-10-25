"""Structured logging: one JSON object per line, carrying IDs and metrics passed through `extra`."""

import json
import logging
import sys
from datetime import UTC, datetime

from api.settings import LogLevel

_STANDARD_RECORD_ATTRIBUTES = frozenset(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Render a log record as a single JSON line.

    Fields given via `extra=` are emitted as top-level keys. Callers must pass identifiers and
    metrics only, never document content, prompts or answers.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(
            {
                key: value
                for key, value in vars(record).items()
                if key not in _STANDARD_RECORD_ATTRIBUTES
            }
        )
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: LogLevel) -> None:
    """Send every log record of the process to stdout as JSON, replacing existing handlers."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
