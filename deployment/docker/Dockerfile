# MCP Claude Context Server - Docker Image
FROM python:3.11-slim

# Install system dependencies including Chrome for extension support
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Install Poetry for dependency management
RUN pip install --no-cache-dir poetry

# Copy dependency files first for better caching
COPY pyproject.toml poetry.lock ./

# Install Python dependencies (without the project itself)
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --only main --no-root

# Copy application code
COPY src/ ./src/
COPY extension/ ./extension/
COPY scripts/ ./scripts/

# Create directories for data persistence
RUN mkdir -p /app/extracted_messages /app/data/db /app/exports

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV MCP_DB_PATH=/app/data/db/conversations.db
ENV MCP_EXPORT_DIR=/app/exports
ENV POETRY_VIRTUALENVS_CREATE=false
ENV POETRY_VIRTUALENVS_IN_PROJECT=false

# Expose ports
# 8000: MCP Server
# 9222: Bridge Server for Chrome Extension
EXPOSE 8000 9222

# Volume mounts for persistent data
VOLUME ["/app/extracted_messages", "/app/data", "/app/exports"]

# Health check - check if the process is running
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD pgrep -f "python -m src.direct_api_server" || exit 1

# Start the MCP server
CMD ["poetry", "run", "python", "-m", "src.direct_api_server"]
