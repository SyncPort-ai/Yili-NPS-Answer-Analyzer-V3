# NPS V3 Analysis System - Production Dockerfile
# Multi-stage Docker build optimized for Chinese enterprise environment

# Build stage
FROM yldc-docker.pkg.coding.yili.com/python-llmydy-3.11:v1.0.0 AS builder

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    pkg-config \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt requirements-deployment.txt ./

# Install Python dependencies with Chinese PyPI mirror
RUN pip install --no-cache-dir \
    --index-url https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com \
    -r requirements.txt \
    -r requirements-deployment.txt

# Production stage
FROM yldc-docker.pkg.coding.yili.com/python-llmydy-3.11:v1.0.0 AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    NPS_V3_ENV=production \
    NPS_V3_LOG_LEVEL=INFO \
    NPS_V3_WORKERS=4 \
    NPS_V3_PORT=8000 \
    NPS_V3_HOST=0.0.0.0

# Create app user for security
RUN groupadd -r npsuser && useradd -r -g npsuser npsuser

# Set working directory
WORKDIR /app

# Copy Python dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p \
    /app/logs \
    /app/outputs/results \
    /app/outputs/reports \
    /app/outputs/monitoring \
    /app/data/temp \
    /app/data/cache

# Set proper permissions
RUN chown -R npsuser:npsuser /app && \
    chmod +x /app/deployment/scripts/*.sh

# Install application in development mode
RUN pip install -e .

# Create health check script
COPY deployment/scripts/health_check.sh /usr/local/bin/health_check.sh
RUN chmod +x /usr/local/bin/health_check.sh

# Switch to non-root user
USER npsuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=40s --retries=3 \
    CMD /usr/local/bin/health_check.sh

# Default command
CMD ["python", "-m", "nps_report_v3.api", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Labels for container metadata
LABEL \
    org.opencontainers.image.title="NPS V3 Analysis System" \
    org.opencontainers.image.description="Multi-agent NPS analysis system for Yili Group" \
    org.opencontainers.image.version="3.0.0" \
    org.opencontainers.image.vendor="Yili Group" \
    org.opencontainers.image.authors="NPS V3 Development Team" \
    org.opencontainers.image.source="https://e.coding.yili.com/yldc/ai-algorithm/nps-answer-analyzer" \
    maintainer="NPS V3 Development Team"