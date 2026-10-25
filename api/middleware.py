"""ASGI middleware returning the trace id on every response and logging one line per request."""

import logging
import time

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from api.tracing import TRACE_ID_HEADER, current_trace_id

logger = logging.getLogger("api.request")


class RequestTelemetryMiddleware:
    """Add the `x-trace-id` header and log method, route, status and duration of each request.

    The route template (e.g. `/v1/corpora/{corpus_id}`) is logged rather than the raw path, and
    neither query strings nor bodies are logged. Requests without a template (unknown paths, the
    built-in docs pages) are logged as `untemplated`.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        trace_id = current_trace_id()
        started_at = time.perf_counter()
        # Stays 500 when the application raises before sending a response.
        status_code = 500

        async def send_with_trace_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[TRACE_ID_HEADER] = trace_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_trace_id)
        finally:
            route = scope.get("route")
            logger.info(
                "request",
                extra={
                    "method": scope["method"],
                    "route": getattr(route, "path", "untemplated"),
                    "status_code": status_code,
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 1),
                    "trace_id": trace_id,
                },
            )
