"""Ensure local src/ package directory is on sys.path for CLI executions."""

from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent / "src"

if SRC_DIR.is_dir():
    sys.path.insert(0, str(SRC_DIR))
