from pathlib import Path
from typing import Optional

import typer
from sqlalchemy import text

from .db import get_engine
from .etl.schedule import load_seasons_and_weeks, load_games
from .etl.stats import load_weekly_stats

app = typer.Typer(help="NFL database management CLI")


def _default_schema_path() -> Path:
    return Path(__file__).resolve().parent / "schema.sql"


@app.command("init-db")
def init_db(schema_path: Optional[Path] = typer.Option(None, help="Path to schema.sql")) -> None:
    """Apply the SQL schema to the configured Postgres database."""
    target_path = schema_path or _default_schema_path()
    sql = target_path.read_text(encoding="utf-8")
    engine = get_engine()
    with engine.begin() as conn:
        for statement in filter(None, (chunk.strip() for chunk in sql.split(";"))):
            conn.execute(text(statement))
    typer.echo("Database schema applied.")


@app.command()
def backfill(
    season_start: int = typer.Option(..., min=1999, help="First season to include."),
    season_end: int = typer.Option(..., min=1999, help="Last season to include."),
    force_refresh: bool = typer.Option(False, help="Refetch even if raw cache exists."),
) -> None:
    """Backfill seasons, weeks, teams, games, and stats using nfl_data_py datasets."""
    load_seasons_and_weeks(season_start, season_end, force_refresh=force_refresh)
    load_games(season_start, season_end, force_refresh=force_refresh)
    load_weekly_stats(season_start, season_end, force_refresh=force_refresh)
    typer.echo(f"Backfill complete for seasons {season_start}-{season_end}.")


@app.command("update-week")
def update_week(
    season: int = typer.Option(..., help="Season to update."),
    week: int = typer.Option(..., min=1, max=22, help="Week to update."),
    force_refresh: bool = typer.Option(False, help="Refetch even if raw cache exists."),
) -> None:
    """Load or refresh a single week of games and stats."""
    load_seasons_and_weeks(season, season, force_refresh=force_refresh)
    load_games(season, season, target_weeks=[week], force_refresh=force_refresh)
    load_weekly_stats(season, season, target_weeks=[week], force_refresh=force_refresh)
    typer.echo(f"Week {week} of {season} refreshed.")


if __name__ == "__main__":
    app()
