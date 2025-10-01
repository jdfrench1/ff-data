import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(dotenv_path=Path('.') / '.env')


def get_database_url() -> str:
    """Return the Postgres connection string from env."""
    try:
        return os.environ["DATABASE_URL"]
    except KeyError as exc:
        raise RuntimeError("DATABASE_URL environment variable is required") from exc
