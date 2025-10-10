from __future__ import annotations

import sys
from pathlib import Path


def activate(*, load_dotenv: bool = True) -> None:
    """
    Prepare the Python runtime for standalone scripts.

    Ensures `src/` is importable, re-executes into the project virtualenv when
    available, and loads `.env` values so downstream modules can rely on
    `DATABASE_URL` and similar configuration.
    """
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    src_dir = repo_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from nfldb.runtime import bootstrap

    bootstrap(load_dotenv=load_dotenv, add_src=False)
