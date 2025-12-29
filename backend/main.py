#!/usr/bin/env python
import subprocess
import os
import asyncio
from pathlib import Path
import sys

# Linux-only deployment, no Windows-specific event loop policy needed

os.chdir(Path(__file__).parent)

if __name__ == "__main__":
    workers = os.getenv("WORKERS", "4")
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", "8000")
    
    print(f"Starting VibeSDLC Production Server (workers={workers})...")
    print(f"Server: http://{host}:{port}\n")

    cmd = [
        sys.executable, "-m", "gunicorn",
        "app.main:app",
        "-w", workers,
        "-k", "uvicorn.workers.UvicornWorker",
        "-b", f"{host}:{port}",
        "--access-logfile", "-",
        "--error-logfile", "-",
        "--capture-output",
        "--timeout", "120",
        "--graceful-timeout", "30",
        "--keep-alive", "5",
    ]

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)
    except FileNotFoundError:
        print("gunicorn not found, falling back to uvicorn...")
        cmd = [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", host,
            "--port", port,
            "--workers", workers,
            "--log-level", "warning",
        ]
        try:
            subprocess.run(cmd, check=True)
        except KeyboardInterrupt:
            print("\nShutting down...")
            sys.exit(0)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)
