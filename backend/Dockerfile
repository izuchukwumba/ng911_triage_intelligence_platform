# Research backend image: the FastAPI app over the append-only event store,
# also used for the inference service. Build context: repository root.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    NTIP_B1_TRAINING_DATA=/app/data/eval/generated-1.0.0-seed42.jsonl

# Dependencies first (cached layer), exactly as pinned in uv.lock, including
# the "ml" extra so the inference service can serve B1.
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --locked --extra ml --no-install-project

COPY backend/src ./src
RUN uv sync --locked --extra ml

# B1 trains from this committed synthetic dataset when it is selected.
COPY data/eval/generated-1.0.0-seed42.jsonl ./data/eval/

RUN useradd --system --uid 10001 ntip
USER ntip

EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --retries=20 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready')"
CMD ["uvicorn", "ntip.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
