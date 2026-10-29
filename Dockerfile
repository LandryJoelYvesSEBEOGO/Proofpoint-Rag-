FROM python:3.11-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock .python-version ./
COPY README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY api ./api
COPY workers ./workers
COPY retrieval ./retrieval
COPY generation ./generation
COPY connectors ./connectors
COPY eval ./eval
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.11-slim

WORKDIR /app

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=build /opt/venv /opt/venv

USER 65534:65534

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
