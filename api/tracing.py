"""OpenTelemetry tracing: each request runs in a server span whose trace id is sent to clients."""

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider

TRACE_ID_HEADER = "x-trace-id"


def instrument(app: FastAPI, service_name: str) -> TracerProvider:
    """Trace every request handled by `app`, honouring an incoming W3C `traceparent` header.

    No span exporter is configured yet, so tracing never depends on an external service and the
    API runs unchanged in air-gapped deployments.
    """
    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    FastAPIInstrumentor.instrument_app(
        app, tracer_provider=provider, exclude_spans=["receive", "send"]
    )
    return provider


def current_trace_id() -> str:
    """Return the trace id of the active span as 32 lowercase hex characters."""
    return trace.format_trace_id(trace.get_current_span().get_span_context().trace_id)
