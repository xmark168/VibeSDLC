#!/usr/bin/env python
"""Development server runner with optimized reload settings."""

import subprocess
import sys

if __name__ == "__main__":
    # Run uvicorn with reload only on app directory
    # This excludes logs, .venv, __pycache__ automatically
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--reload",
        "--reload-dir", "app",  # Only watch app directory
        "--host", "0.0.0.0",
        "--port", "8000",
    ]

    print("Starting development server...")
    print("Watching for changes in: app/")
    print("Excluded from reload: logs/, .venv/, __pycache__, alembic/")

    subprocess.run(cmd)
