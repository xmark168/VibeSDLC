#!/usr/bin/env python
"""Development server runner with proper logging and reload settings."""

import subprocess
import sys
import os
from pathlib import Path

# Ensure we're in the backend directory
os.chdir(Path(__file__).parent)

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Starting VibeSDLC Development Server")
    print("=" * 70)
    print()
    print("📁 Working directory:", os.getcwd())
    print("🔍 Watching for changes in: app/")
    print("🚫 Excluded from reload: logs/, .venv/, __pycache__, alembic/")
    print()
    print("📝 Logs:")
    print("   - Console: All requests + application logs")
    print("   - File: backend/logs/app.log")
    print()
    print("🌐 Server: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print()
    print("=" * 70)
    print()

    # Run uvicorn with comprehensive settings
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--reload",
        "--reload-dir", "app",  # Only watch app directory
        "--host", "0.0.0.0",  # Listen on all interfaces
        "--port", "8000",
        "--log-level", "info",  # Uvicorn log level
        "--use-colors",  # Colored output
    ]

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Server crashed with error code {e.returncode}")
        sys.exit(e.returncode)
