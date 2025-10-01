from pathlib import Path


def test_schema_contains_core_tables():
    schema = Path("src/nfldb/schema.sql").read_text(encoding="utf-8")
    for table in ["seasons", "weeks", "teams", "players", "games"]:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema
