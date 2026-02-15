# syntax=docker/dockerfile:1

# === Build stage ===
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --target=/app/deps -r requirements.txt

# === Runtime stage ===
FROM python:3.11-slim-bookworm

# Install iproute2 for virtual IP management (ip addr add)
# and curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/deps:/app/src

WORKDIR /app

# Copy installed dependencies from builder
COPY --from=builder /app/deps /app/deps

# Copy application code and config
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# BACnet/IP uses UDP 47808; FastAPI uses TCP 8099
EXPOSE 47808/udp
EXPOSE 8099/tcp

# Health check against FastAPI readiness endpoint
HEALTHCHECK --interval=5s --timeout=3s --start-period=15s --retries=5 \
    CMD curl -f http://localhost:8099/health/ready || exit 1

# Note: Container needs --cap-add=NET_ADMIN at runtime for multi-device
# virtual IP setup. The entrypoint runs as root to configure IPs,
# then the Python process handles everything.

ENTRYPOINT ["./entrypoint.sh"]
