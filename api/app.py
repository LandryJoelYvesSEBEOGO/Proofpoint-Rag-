"""Application factory: assembles routes, error handling, telemetry and tracing."""

from importlib.metadata import version

from fastapi import FastAPI

from api import health, v1
from api.errors import install_error_handlers
from api.middleware import RequestTelemetryMiddleware
from api.settings import Settings
from api.tracing import instrument


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the API application; settings are read from the environment unless given."""
    settings = settings or Settings()
    app = FastAPI(title="ProofPoint RAG API", version=version("proofpoint-rag"))
    app.include_router(health.router)
    app.include_router(v1.router)
    app.add_middleware(RequestTelemetryMiddleware)
    install_error_handlers(app)
    instrument(app, settings.otel_service_name)
    return app
