# Multi-stage hardened Dockerfile for Facebook Ads Intelligence MCP (Q29, §30)

# --- Stage 1: Build Dependencies ---
FROM ghcr.io/astral-sh/uv:latest AS uv_bin
FROM python:3.12-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy uv binary from official image
COPY --from=uv_bin /uv /uvx /bin/

# Install dependencies using frozen lockfile
COPY pyproject.toml uv.lock README.md /app/
RUN uv sync --frozen --no-dev --no-install-project

# --- Stage 2: Hardened Runtime Image ---
FROM python:3.12-slim AS runtime

# Install Chromium runtime dependencies for headless crawling (Q8, §30)
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgbm1 \
    libasound2t64 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create dedicated non-root user (UID 10001) (§30, §81)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

WORKDIR /app

# Copy virtualenv and application code
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --chown=appuser:appgroup app /app/app
COPY --chown=appuser:appgroup pyproject.toml /app/

# Environment configurations
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    HOME="/home/appuser" \
    PORT=8000 \
    HOST=0.0.0.0 \
    MCP_TRANSPORT=http

# Switch to non-root user
USER appuser

EXPOSE 8000

# Default entrypoint using ASGI uvicorn (Q34)
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
