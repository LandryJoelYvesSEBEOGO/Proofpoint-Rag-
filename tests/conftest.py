"""Shared fixtures: a fresh API application and an in-process HTTP client per test."""

import logging
from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
from fastapi import FastAPI

from api.app import create_app
from api.settings import Settings


@pytest.fixture
def app() -> FastAPI:
    return create_app(Settings())


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    # raise_app_exceptions=False lets tests observe the 500 response instead of the exception.
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def restore_root_logger() -> Iterator[None]:
    """Undo process-wide logging changes made by the code under test."""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    root.handlers[:] = handlers
    root.setLevel(level)
