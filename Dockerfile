# Dockerfile for Fronius HA Dual MPPT
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r lerebel103 && useradd -r -g lerebel103 lerebel103

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY src/ ./src/

# Create config directory and set permissions
RUN mkdir -p /etc/fronius-ha-dual-mppt && \
    chown -R lerebel103:lerebel103 /app /etc/fronius-ha-dual-mppt

# Switch to non-root user
USER lerebel103

# Set Python path to include src directory
ENV PYTHONPATH=/app/src

# Default command - run with config from mounted volume
CMD ["python", "-m", "fronius_modbus", "--config", "/etc/fronius-ha-dual-mppt/config.yaml"]

# Expose no ports (this is an MQTT client, not a server)
# Health check could be added later if needed

# Labels for metadata
LABEL maintainer="lerebel103"
LABEL description="Fronius HA Dual MPPT bridge for Home Assistant"
LABEL version="1.0.0"