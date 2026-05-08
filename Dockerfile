# syntax=docker/dockerfile:1.7
# Single-stage Python runtime. The Next.js static export must be built on the
# host (run `npm run build` in frontend/) before this image is built; the
# start scripts handle that automatically. Building the frontend inside Docker
# was prohibitively slow (npm ci stalled inside Docker Desktop's network), so
# we ship the prebuilt artifact in.

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    FINALLY_DB_PATH=/app/db/finally.db

# uv is delivered as a single static binary from the official image.
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv

WORKDIR /app

# Install Python deps from the lockfile (no project install, no dev extras).
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Application source.
COPY backend/app ./app

# Prebuilt Next.js static export (contents of frontend/out/).
# /app/static/index.html and /app/static/_next/ must exist after this step.
COPY frontend/out ./static
RUN test -f /app/static/index.html && test -d /app/static/_next \
    || (echo "ERROR: frontend/out/ is missing or incomplete. Run 'npm run build' in frontend/ before docker build." >&2; exit 1)

# Volume mount target for the SQLite database; must exist for runtime writes.
RUN mkdir -p /app/db

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status==200 else 1)"

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
