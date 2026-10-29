"""Settings come from environment variables and reject invalid values."""

import pytest
from pydantic import ValidationError

from api.settings import Settings


def test_defaults_apply_when_variables_are_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("OTEL_SERVICE_NAME", raising=False)

    settings = Settings()

    assert settings.log_level == "INFO"
    assert settings.otel_service_name == "proofpoint-api"


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "proofpoint-api-staging")

    settings = Settings()

    assert settings.log_level == "DEBUG"
    assert settings.otel_service_name == "proofpoint-api-staging"


def test_invalid_log_level_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "VERBOSE")

    with pytest.raises(ValidationError):
        Settings()
