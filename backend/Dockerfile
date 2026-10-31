FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

# Couche de dépendances séparée : elle reste en cache tant que le lock ne change pas.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

RUN groupadd --gid 1000 app && useradd --uid 1000 --gid app --no-create-home app

COPY alembic.ini ./
COPY scripts ./scripts
# Le service doit pouvoir écrire ici pour `docker compose watch`.
COPY --chown=app:app app ./app

USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/utils/health-check')"]

# Un seul worker : la limitation de débit est gardée en mémoire par processus.
CMD ["fastapi", "run", "--port", "8000"]
