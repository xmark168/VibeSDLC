#!/usr/bin/env python
import subprocess
import os
import asyncio
from pathlib import Path

# Linux-only deployment, no Windows-specific event loop policy needed

os.chdir(Path(__file__).parent)

if __name__ == "__main__":
    print("Starting VibeSDLC Development Server...")
    print(f"Server: http://localhost:8000 | Docs: http://localhost:8000/docs\n")

    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--reload",
        "--reload-dir", "app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--log-level", "info",
        "--use-colors",
    ]

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
