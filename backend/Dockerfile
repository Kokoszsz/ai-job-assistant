# ==============================================================================
# AI-Powered Job Search Assistant - Backend Dockerfile
# ==============================================================================
# Multi-stage build for development and production

# ------------------------------------------------------------------------------
# Base Stage: Common dependencies
# ------------------------------------------------------------------------------
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# ------------------------------------------------------------------------------
# Development Stage
# ------------------------------------------------------------------------------
FROM base as development

# Install development dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt -r requirements-dev.txt

# Copy source code (will be overridden by volume mount in dev)
COPY . .

# Expose port
EXPOSE 5000

# Set Flask environment
ENV FLASK_APP=src.app:create_app \
    FLASK_ENV=development \
    FLASK_DEBUG=1

# Default command for development
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000", "--reload"]

# ------------------------------------------------------------------------------
# Production Dependencies Stage
# ------------------------------------------------------------------------------
FROM base as production-deps

# Copy requirements
COPY requirements.txt ./

# Install only production dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ------------------------------------------------------------------------------
# Production Stage
# ------------------------------------------------------------------------------
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Create app directory
WORKDIR /app

# Copy Python packages from production-deps stage
COPY --from=production-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=production-deps /usr/local/bin /usr/local/bin

# Copy source code
COPY --chown=appuser:appgroup . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Set Flask environment
ENV FLASK_APP=src.app:create_app \
    FLASK_ENV=production \
    FLASK_DEBUG=0

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Production command using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--threads", "2", "src.app:create_app()"]
