"""Structured JSON logs and the per-request log line."""

import importlib
import json
import logging

import httpx
import pytest
from starlette.types import Message, Receive, Scope, Send

from api.log_config import JsonFormatter, configure_logging
from api.middleware import RequestTelemetryMiddleware


def _record(message: str, **extra: object) -> logging.LogRecord:
    record = logging.makeLogRecord({"name": "api.test", "levelname": "INFO", "msg": message})
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_emits_extra_fields_as_top_level_keys() -> None:
    line = JsonFormatter().format(_record("document indexed", document_id="doc-1", pages=12))

    payload = json.loads(line)
    assert payload["message"] == "document indexed"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "api.test"
    assert payload["document_id"] == "doc-1"
    assert payload["pages"] == 12
    assert "timestamp" in payload


def test_json_formatter_keeps_non_ascii_text_readable() -> None:
    line = JsonFormatter().format(_record("corpus créé", corpus_name="عربي"))

    assert "créé" in line
    assert "عربي" in line


def test_json_formatter_includes_the_exception() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        record = _record("failed")
        record.exc_info = logging.sys.exc_info()  # type: ignore[attr-defined]

    payload = json.loads(JsonFormatter().format(record))

    assert "ValueError: boom" in payload["exception"]


@pytest.mark.usefixtures("restore_root_logger")
def test_configure_logging_routes_records_through_the_json_formatter() -> None:
    configure_logging("WARNING")

    root = logging.getLogger()
    assert root.level == logging.WARNING
    [handler] = root.handlers
    assert isinstance(handler.formatter, JsonFormatter)


@pytest.mark.usefixtures("restore_root_logger")
def test_entry_point_builds_the_application() -> None:
    main = importlib.import_module("api.main")

    assert main.app.title == "ProofPoint RAG API"


async def test_each_request_is_logged_with_route_status_duration_and_trace_id(
    client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="api.request"):
        response = await client.get("/health?token=should-not-be-logged")

    [record] = [r for r in caplog.records if r.name == "api.request"]
    fields = vars(record)
    assert fields["method"] == "GET"
    assert fields["route"] == "/health"
    assert fields["status_code"] == 200
    assert fields["duration_ms"] >= 0
    assert fields["trace_id"] == response.headers["x-trace-id"]
    assert "should-not-be-logged" not in JsonFormatter().format(record)


async def test_non_http_scopes_pass_through_untouched() -> None:
    received: list[Scope] = []

    async def inner_app(scope: Scope, _receive: Receive, _send: Send) -> None:
        received.append(scope)

    async def receive() -> Message:
        return {"type": "lifespan.startup"}

    async def send(_message: Message) -> None:
        return None

    lifespan_scope: Scope = {"type": "lifespan"}
    await RequestTelemetryMiddleware(inner_app)(lifespan_scope, receive, send)

    assert received == [lifespan_scope]


async def test_unknown_path_is_logged_without_the_raw_path(
    client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO, logger="api.request"):
        await client.get("/v1/customer-name-in-path")

    [record] = [r for r in caplog.records if r.name == "api.request"]
    assert vars(record)["route"] == "untemplated"
    assert vars(record)["status_code"] == 404
