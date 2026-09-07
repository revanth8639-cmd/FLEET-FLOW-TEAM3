"""Build and run FleetFlow as one integrated web application."""

from pathlib import Path
import os
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from importlib.util import find_spec
from urllib.request import urlopen
import json


project_root = Path(__file__).resolve().parent
frontend_dir = project_root / "frontend"
backend_dir = project_root / "backend"
npm_command = shutil.which("npm.cmd") or shutil.which("npm")


def running_fleetflow_api() -> bool:
    """Avoid starting a second host server when Docker already serves FleetFlow."""
    try:
        with urlopen("http://127.0.0.1:8000/openapi.json", timeout=1) as response:
            payload = json.load(response)
        paths = payload.get("paths", {})
        return "/api/dashboard/summary" in paths and "/api/activity/" in paths
    except Exception:
        return False


if running_fleetflow_api():
    print("FleetFlow is already running at http://127.0.0.1:8000")
    raise SystemExit(0)

if not npm_command:
    raise SystemExit("Node.js/npm is required. Install Node.js, then run this command again.")

# Keep the one-command launcher usable on a fresh machine.  Only install when
# a required backend dependency is actually missing.
required_modules = ("fastapi", "sqlalchemy", "alembic", "uvicorn", "celery", "redis", "reportlab", "openpyxl")
try:
    bcrypt_is_compatible = int(version("bcrypt").split(".", maxsplit=1)[0]) < 5
except PackageNotFoundError:
    bcrypt_is_compatible = False

if any(find_spec(module) is None for module in required_modules) or not bcrypt_is_compatible:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(backend_dir / "requirements.txt")],
        check=True,
    )

subprocess.run([npm_command, "run", "build"], cwd=frontend_dir, check=True)
os.chdir(backend_dir)
# Alembic has no ``python -m alembic`` entry point.  Calling its public Python
# API works consistently on Windows, including installations where the
# ``alembic.exe`` script is not on PATH.
from alembic import command
from alembic.config import Config

alembic_config = Config(str(backend_dir / "alembic.ini"))
command.upgrade(alembic_config, "head")
try:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        check=True,
    )
except KeyboardInterrupt:
    # Ctrl+C is an expected way to stop the development server on Windows.
    print("\nFleetFlow server stopped.")
