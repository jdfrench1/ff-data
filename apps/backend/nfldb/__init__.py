"""Package shim so `python -m nfldb.cli` works without installing the project."""

from __future__ import annotations

from pathlib import Path

_SRC_PKG = Path(__file__).resolve().parent.parent / "src" / "nfldb"

if not _SRC_PKG.is_dir():
    raise ImportError(f"Expected package directory at {_SRC_PKG}")

__path__ = [str(_SRC_PKG)]
