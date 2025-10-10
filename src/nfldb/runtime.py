from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

_BOOTSTRAP_FLAG = "NFLDB_RUNTIME_ACTIVE"


def project_root() -> Path:
    """Return the repository root based on this module location."""
    return Path(__file__).resolve().parents[2]


def _venv_python(root: Path) -> Optional[Path]:
    venv_dir = root / ".venv"
    if not venv_dir.exists():
        return None
    if os.name == "nt":
        candidate = venv_dir / "Scripts" / "python.exe"
    else:
        candidate = venv_dir / "bin" / "python"
    return candidate if candidate.exists() else None


def _ensure_src_on_path(root: Path) -> None:
    src_dir = root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def _load_dotenv(root: Path) -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:  # pragma: no cover
        return
    dotenv_path = root / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path=dotenv_path, override=False)


def _same_executable(target: Path) -> bool:
    try:
        current = Path(sys.executable).resolve()
    except FileNotFoundError:  # pragma: no cover
        return False
    return current == target.resolve()


def _ensure_virtualenv(root: Path) -> None:
    target = _venv_python(root)
    if not target:
        return
    if os.environ.get(_BOOTSTRAP_FLAG):
        return
    if _same_executable(target):
        os.environ[_BOOTSTRAP_FLAG] = "1"
        return
    env = os.environ.copy()
    env[_BOOTSTRAP_FLAG] = "1"
    os.execv(str(target), [str(target), *sys.argv])


def bootstrap(*, load_dotenv: bool = True, add_src: bool = True) -> None:
    """
    Ensure scripts execute inside the project virtual environment.

    When the current interpreter differs from `.venv`, the process is replaced
    with the `.venv` interpreter while preserving arguments. On every invocation
    the repository `src/` directory is added to `sys.path`, and `.env` is loaded
    (if present) to supply connection details such as `DATABASE_URL`.
    """
    root = project_root()
    if add_src:
        _ensure_src_on_path(root)
    _ensure_virtualenv(root)
    if load_dotenv:
        _load_dotenv(root)
