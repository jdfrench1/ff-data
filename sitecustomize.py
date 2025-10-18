"""Expose backend src/ package when running Python from the repo root."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = ROOT / "apps" / "backend"
BACKEND_SRC = BACKEND_ROOT / "src"

for candidate in (BACKEND_SRC, BACKEND_ROOT):
    if candidate.is_dir():
        path_str = str(candidate)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
