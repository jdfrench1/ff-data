from pathlib import Path


def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_schema_contains_core_tables():
    schema_path = backend_root() / "src" / "nfldb" / "schema.sql"
    schema = schema_path.read_text(encoding="utf-8")
    for table in ["seasons", "weeks", "teams", "players", "games"]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema
