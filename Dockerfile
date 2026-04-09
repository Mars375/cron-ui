# Dockerfile for cron-ui
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chmod +x /usr/local/bin/docker-entrypoint.sh && \
    chown -R app:app /app

# Expose port
EXPOSE 8906

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8906/health || exit 1

# Run the application
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8906"]
