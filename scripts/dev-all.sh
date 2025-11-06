#!/usr/bin/env bash

# Start all services for local development
# Usage: bash scripts/dev-all.sh

echo "🚀 Starting VibeSDLC Development Environment"
echo ""

# Function to run command in new terminal based on OS
run_in_terminal() {
    local title="$1"
    local command="$2"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        osascript -e "tell app \"Terminal\" to do script \"cd '$(pwd)' && $command\""
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows (Git Bash / WSL)
        cmd.exe /c start "$title" bash -c "$command; exec bash"
    else
        # Linux
        x-terminal-emulator -e bash -c "$command; exec bash" &
    fi
}

# Start Management Service
echo "📦 Starting Management Service (Port 8000)..."
run_in_terminal "Management Service" "bash scripts/dev-management.sh"
sleep 2

# Start AI Agent Service
echo "🤖 Starting AI Agent Service (Port 8001)..."
run_in_terminal "AI Agent Service" "bash scripts/dev-ai-agent.sh"
sleep 2

# Start Frontend
echo "🎨 Starting Frontend (Port 5173)..."
run_in_terminal "Frontend" "cd frontend && npm run dev"

echo ""
echo "✅ All services starting..."
echo ""
echo "📍 Management Service: http://localhost:8000"
echo "📍 AI Agent Service:   http://localhost:8001"
echo "📍 Frontend:           http://localhost:5173"
echo ""
echo "💡 Each service runs in a separate terminal window"
