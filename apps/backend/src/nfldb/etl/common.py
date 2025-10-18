from pathlib import Path

RAW_DIR = Path(__file__).resolve().parents[3] / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)


def cache_path(kind: str, season_start: int, season_end: int, extension: str = "parquet") -> Path:
    """Return a cache file path inside the raw directory."""
    return RAW_DIR / f"{kind}_{season_start}_{season_end}.{extension}"
