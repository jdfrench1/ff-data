import os
import sys
from typing import Optional

import pandas as pd
import nfl_data_py as nfl
import typer


def load_weekly(season: int, week: Optional[int] = None) -> pd.DataFrame:
    df = nfl.import_weekly_data(years=[season])
    # Ensure expected basic columns exist; nfl_data_py schema may evolve
    if week is not None:
        df = df[df["week"] == week]
    # Normalize column names (lower_snake)
    df.columns = [str(c).strip().replace(" ", "_").lower() for c in df.columns]
    return df.reset_index(drop=True)


def main(
    season: Optional[int] = typer.Option(None, help="Season year, e.g., 2024"),
    week: Optional[int] = typer.Option(None, help="Week number (1-22) or omitted for all"),
    output: str = typer.Option("nfl_weekly_stats.csv", help="Output CSV path"),
):
    # Fallback to environment if CLI not provided
    if season is None:
        env = os.getenv("SEASON") or os.getenv("season")
        if env:
            try:
                season = int(env)
            except ValueError:
                print(f"Invalid SEASON value: {env}", file=sys.stderr)
                raise typer.Exit(code=2)
    if season is None:
        season = 2024

    if week is None:
        envw = os.getenv("WEEK") or os.getenv("week")
        if envw and str(envw).lower() not in {"", "current", "all"}:
            try:
                week = int(envw)
            except ValueError:
                print(f"Ignoring invalid WEEK value: {envw}", file=sys.stderr)
                week = None

    df = load_weekly(season, week)
    df.to_csv(output, index=False)
    print(
        f"Wrote {len(df)} rows to {output} for season={season} week={week if week is not None else 'all'}"
    )


if __name__ == "__main__":
    try:
        typer.run(main)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
