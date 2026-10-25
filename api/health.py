"""Liveness endpoint for load balancers and orchestrators; outside /v1 and unauthenticated."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """The process is up and serving requests."""

    status: Literal["ok"] = "ok"


@router.get("/health")
async def health() -> HealthResponse:
    """Report that the API process is alive. Does not check downstream services."""
    return HealthResponse()
