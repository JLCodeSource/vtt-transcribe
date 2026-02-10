# Multi-stage Dockerfile for vtt-transcribe
# Optimized for size and security with non-root user

# Build stage: Install dependencies and build
FROM python:3.13-slim AS builder

WORKDIR /app

# Install system dependencies required for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency installation
RUN pip install --no-cache-dir uv

# Copy only dependency files first (for better layer caching)
COPY pyproject.toml README.md ./

# Create virtual environment
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy source code
COPY vtt_transcribe ./vtt_transcribe

# Install base package with dependencies
RUN uv pip install "."

# Build stage for API - includes API extras
FROM builder AS builder-api
RUN uv pip install ".[api]"

# Runtime stage: Minimal image with only runtime dependencies
FROM python:3.13-slim AS base

# Configurable UID for non-root user (default 1000 for typical Linux desktops)
ARG USER_UID=1000

# Install only runtime system dependencies (including curl for healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u "$USER_UID" vttuser

# Copy virtual environment from builder (includes installed package)
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Ensure Python output is unbuffered
ENV PYTHONUNBUFFERED=1

# ============================================================================
# API Target - for FastAPI server
# ============================================================================
FROM base AS api

# Copy virtual environment with API extras from builder-api
COPY --from=builder-api /opt/venv /opt/venv

# Create directories for uploads and logs
RUN mkdir -p /app/uploads /app/logs && \
    chown -R vttuser:vttuser /app

WORKDIR /app

# Switch to non-root user
USER vttuser

# Expose API port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "vtt_transcribe.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================================================
# Worker Target - for background transcription jobs
# ============================================================================
FROM base AS worker

# Create directories for uploads and logs
RUN mkdir -p /app/uploads /app/logs && \
    chown -R vttuser:vttuser /app

WORKDIR /app

# Switch to non-root user
USER vttuser

# Worker runs background tasks
# TODO: Uncomment when worker module is implemented
# CMD ["python", "-m", "vtt_transcribe.worker"]
CMD ["echo", "Worker module not yet implemented. Use profiles to skip this service."]

# ============================================================================
# CLI Target (default) - for standalone transcription
# ============================================================================
FROM base AS cli

# Set working directory for user files
WORKDIR /workspace

# Switch to non-root user
USER vttuser

# Set entrypoint (no CMD - let stdin detection or user args determine behavior)
ENTRYPOINT ["vtt"]
