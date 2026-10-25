"""The health endpoint and the trace id returned on every response."""

import re

import httpx

TRACE_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
INVALID_TRACE_ID = "0" * 32


async def test_health_reports_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_every_response_carries_a_valid_trace_id(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")

    trace_id = response.headers["x-trace-id"]
    assert TRACE_ID_PATTERN.match(trace_id)
    assert trace_id != INVALID_TRACE_ID


async def test_each_request_gets_its_own_trace_id(client: httpx.AsyncClient) -> None:
    first = await client.get("/health")
    second = await client.get("/health")

    assert first.headers["x-trace-id"] != second.headers["x-trace-id"]


async def test_incoming_traceparent_is_continued(client: httpx.AsyncClient) -> None:
    caller_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"

    response = await client.get(
        "/health", headers={"traceparent": f"00-{caller_trace_id}-00f067aa0ba902b7-01"}
    )

    assert response.headers["x-trace-id"] == caller_trace_id


async def test_openapi_schema_is_published(client: httpx.AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]
