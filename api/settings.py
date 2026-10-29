"""API configuration, read from environment variables only (documented in .env.example)."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class Settings(BaseSettings):
    """Runtime configuration of the API process."""

    model_config = SettingsConfigDict(frozen=True, extra="ignore")

    log_level: LogLevel = "INFO"
    otel_service_name: str = "proofpoint-api"
