# Research backend image: FastAPI app over the append-only event store.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH"

# Dependencies first (cached layer), exactly as pinned in uv.lock.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project

COPY src ./src
RUN uv sync --locked

RUN useradd --system --uid 10001 ntip
USER ntip

EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --retries=20 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready')"
CMD ["uvicorn", "ntip.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
