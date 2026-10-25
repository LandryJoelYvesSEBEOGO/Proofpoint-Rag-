"""Version 1 of the public REST API. Breaking changes go to a new version, never here."""

from fastapi import APIRouter

from api.errors import ErrorResponse

router = APIRouter(
    prefix="/v1",
    responses={
        422: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Unexpected error"},
    },
)
