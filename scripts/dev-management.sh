#!/usr/bin/env bash

# Start Management Service for local development
# Usage: bash scripts/dev-management.sh

cd "$(dirname "$0")/../services/management-service" || exit 1

echo "🚀 Starting Management Service (Development Mode)"
echo "📍 Port: 8000"
echo "📝 Logs: Errors only (no HTTP access logs)"
echo ""

uvicorn app.main:app \
  --reload \
  --port 8000 \
  --no-access-log \
  --log-level info
