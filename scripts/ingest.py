#!/usr/bin/env python3
"""Thin wrapper so README's `python scripts/ingest.py` works from the repo root."""

import subprocess
import sys
from pathlib import Path

backend = Path(__file__).resolve().parents[1] / "backend"
raise SystemExit(
    subprocess.call([sys.executable, "-m", "app.ingestion", *sys.argv[1:]], cwd=backend)
)
