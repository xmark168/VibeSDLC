#!/usr/bin/env bash

# Start AI Agent Service for local development
# Usage: bash scripts/dev-ai-agent.sh

cd "$(dirname "$0")/../services/ai-agent-service" || exit 1

echo "🚀 Starting AI Agent Service (Development Mode)"
echo "📍 Port: 8001"
echo "📝 Logs: Errors only (no HTTP access logs)"
echo ""

uv run uvicorn app.main:app \
  --reload \
  --port 8001 \
  --no-access-log \
  --log-level info
