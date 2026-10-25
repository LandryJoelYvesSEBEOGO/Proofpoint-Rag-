"""ASGI entry point for uvicorn: configures process-wide logging, then builds the application."""

from api.app import create_app
from api.log_config import configure_logging
from api.settings import Settings

settings = Settings()
configure_logging(settings.log_level)
app = create_app(settings)
