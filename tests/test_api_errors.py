"""Every error has the typed shape, carries the trace id and leaks neither input nor internals."""

import logging

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from api.errors import ApiError


class _Payload(BaseModel):
    count: int


@pytest.fixture
def app_with_test_routes(app: FastAPI) -> FastAPI:
    @app.post("/v1/_test/validate")
    async def validate(payload: _Payload) -> _Payload:
        return payload

    @app.get("/v1/_test/api-error")
    async def raise_api_error() -> None:
        raise ApiError(409, "corpus_already_exists", "A corpus with this name already exists.")

    @app.get("/v1/_test/crash")
    async def crash() -> None:
        raise RuntimeError("internal detail that must not leak")

    @app.get("/v1/_test/structured-detail")
    async def structured_detail() -> None:
        raise HTTPException(status_code=403, detail={"reason": "internal structure"})

    @app.get("/v1/_test/non-standard-status")
    async def non_standard_status() -> None:
        raise HTTPException(status_code=599, detail="Upstream timed out.")

    return app


def _assert_error_shape(response: httpx.Response, status_code: int, code: str) -> dict[str, object]:
    assert response.status_code == status_code
    body: dict[str, object] = response.json()
    assert set(body) == {"error", "trace_id"}
    assert body["trace_id"] == response.headers["x-trace-id"]
    error = body["error"]
    assert isinstance(error, dict)
    assert error["code"] == code
    assert isinstance(error["message"], str)
    return error


async def test_unknown_route_returns_typed_not_found(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/does-not-exist")

    _assert_error_shape(response, 404, "not_found")


async def test_wrong_method_returns_typed_error_and_keeps_allow_header(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/health")

    _assert_error_shape(response, 405, "method_not_allowed")
    assert response.headers["allow"] == "GET"


@pytest.mark.usefixtures("app_with_test_routes")
async def test_validation_error_lists_fields_without_echoing_input(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post("/v1/_test/validate", json={"count": "confidential-value"})

    error = _assert_error_shape(response, 422, "validation_error")
    assert error["details"] == [
        {
            "location": ["body", "count"],
            "message": "Input should be a valid integer, unable to parse string as an integer",
            "type": "int_parsing",
        }
    ]
    assert "confidential-value" not in response.text


@pytest.mark.usefixtures("app_with_test_routes")
async def test_api_error_keeps_its_status_and_code(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/_test/api-error")

    error = _assert_error_shape(response, 409, "corpus_already_exists")
    assert error["message"] == "A corpus with this name already exists."


@pytest.mark.usefixtures("app_with_test_routes")
async def test_non_string_http_detail_is_replaced_by_the_reason_phrase(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/v1/_test/structured-detail")

    error = _assert_error_shape(response, 403, "forbidden")
    assert error["message"] == "Forbidden"
    assert "internal structure" not in response.text


@pytest.mark.usefixtures("app_with_test_routes")
async def test_non_standard_status_code_gets_a_generic_code(client: httpx.AsyncClient) -> None:
    response = await client.get("/v1/_test/non-standard-status")

    error = _assert_error_shape(response, 599, "http_error")
    assert error["message"] == "Upstream timed out."


@pytest.mark.usefixtures("app_with_test_routes")
async def test_unexpected_error_is_generic_for_the_client_and_logged_with_trace_id(
    client: httpx.AsyncClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR, logger="api.errors"):
        response = await client.get("/v1/_test/crash")

    error = _assert_error_shape(response, 500, "internal_error")
    assert error["message"] == "An unexpected error occurred."
    assert "internal detail" not in response.text
    [record] = [r for r in caplog.records if r.name == "api.errors"]
    assert getattr(record, "trace_id") == response.headers["x-trace-id"]  # noqa: B009
    assert getattr(record, "exception_type") == "RuntimeError"  # noqa: B009
