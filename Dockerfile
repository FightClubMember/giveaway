# Multi-stage lightweight Python Dockerfile
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create volume for persistent SQLite database if SQLite is used
VOLUME ["/app/data"]

# Run as non-privileged user for security
RUN useradd -u 1000 -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "bot.py"]
