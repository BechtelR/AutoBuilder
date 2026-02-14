# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

# Copy uv from official image (pinned for reproducibility)
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files and README (required by hatchling)
COPY pyproject.toml uv.lock README.md ./

# Copy app directory (required for editable install)
COPY app/ app/

# Install production dependencies into .venv
RUN uv sync --frozen --no-dev

# Stage 2: Runtime
FROM python:3.12-slim

# Non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --no-create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application files
COPY alembic.ini ./
COPY app/ app/

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"

# Run as non-root
USER appuser

# Expose gateway port
EXPOSE 8000

# Default: run gateway
# Override for worker: docker run autobuilder arq app.workers.settings.WorkerSettings
CMD ["uvicorn", "app.gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
