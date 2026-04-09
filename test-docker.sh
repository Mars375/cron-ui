#!/bin/bash

# Test script for cron-ui Docker setup
set -euo pipefail

cleanup() {
  docker compose down >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "🐳 Testing cron-ui Docker setup..."

# Build the Docker image
# Keeps a direct image build path validated in addition to compose.
echo "Building Docker image..."
docker build -t cron-ui:test .

# Create test data directory
mkdir -p data

# Run container in background with a fresh compose build
echo "Starting cron-ui container..."
docker compose up -d --build

# Wait for container to start
echo "Waiting for container to start..."
sleep 10

# Check if container is running
if docker compose ps --status running | grep -q cron-ui; then
    echo "✅ Container is running"
else
    echo "❌ Container failed to start"
    docker compose logs
    exit 1
fi

# Check health endpoint
echo "Testing health endpoint..."
if curl -f http://localhost:8906/health > /dev/null 2>&1; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    docker compose logs
    exit 1
fi

# Test main dashboard
echo "Testing dashboard..."
if curl -f http://localhost:8906/ > /dev/null 2>&1; then
    echo "✅ Dashboard is accessible"
else
    echo "❌ Dashboard failed"
    exit 1
fi

echo "🎉 All tests passed! Docker setup is working correctly."
