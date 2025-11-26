# ============================================================================
# AutifyME Agents - Cloud Run Dockerfile
# ============================================================================
# Multi-stage build using uv for fast, reproducible dependency installation
# Optimized for Google Cloud Run serverless deployment
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: Build stage with uv
# ----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency files first (layer caching optimization)
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
# Using --frozen ensures lockfile is respected exactly
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code
COPY agents/src/autifyme_agents ./agents/src/autifyme_agents

# Install the project itself
RUN uv sync --frozen --no-dev

# ----------------------------------------------------------------------------
# Stage 2: Production runtime
# ----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Security: Run as non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code (needed for module imports)
COPY --from=builder /app/agents/src/autifyme_agents /app/agents/src/autifyme_agents

# Ensure the virtual environment is used
ENV PATH="/app/.venv/bin:$PATH"

# Cloud Run provides PORT environment variable (default: 8080)
ENV PORT=8080

# Python optimizations for production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/agents/src

# Set ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Health check for Cloud Run (optional, Cloud Run has its own health probing)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

# Cloud Run sends SIGTERM for graceful shutdown
# Uvicorn handles this natively with proper worker cleanup
EXPOSE ${PORT}

# Start FastAPI with uvicorn
# - Workers: 1 (Cloud Run scales via instances, not workers)
# - Host: 0.0.0.0 (required for container networking)
# - Port: from PORT env var (Cloud Run requirement)
CMD ["sh", "-c", "uvicorn autifyme_agents.entrypoints.whatsapp_webhook:app --host 0.0.0.0 --port ${PORT}"]
