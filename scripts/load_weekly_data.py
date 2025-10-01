import os
import sys
from typing import Optional, Callable

import pandas as pd
import typer


def _resolve_weekly_loader() -> Callable[[int], pd.DataFrame]:
    # Prefer nflreadpy, fallback to nfl_data_py for compatibility
    try:
        import nflreadpy as nfr  # type: ignore

        # Try common function names across versions
        for name in ("import_weekly", "import_weekly_data", "load_weekly", "weekly"):
            func = getattr(nfr, name, None)
            if callable(func):
                def _load(season: int, _func=func):
                    # Many variants accept years=[...]
                    try:
                        return _func(years=[season])
                    except TypeError:
                        return _func(season)
                return _load
        raise ImportError("nflreadpy found but no weekly import function detected")
    except Exception:
        pass

    try:
        import nfl_data_py as ndp  # type: ignore

        def _load(season: int):
            return ndp.import_weekly_data(years=[season])

        return _load
    except Exception as exc:
        raise RuntimeError(
            "No data provider available. Install nflreadpy or nfl_data_py."
        ) from exc


def _resolve_schedule_loader() -> Callable[[int], pd.DataFrame]:
    # Prefer nflreadpy, fallback to nfl_data_py
    try:
        import nflreadpy as nfr  # type: ignore

        for name in ("import_schedules", "load_schedules", "schedules"):
            func = getattr(nfr, name, None)
            if callable(func):
                def _load(season: int, _func=func):
                    try:
                        return _func(years=[season])
                    except TypeError:
                        return _func(season)
                return _load
        raise ImportError("nflreadpy found but no schedule import function detected")
    except Exception:
        pass

    try:
        import nfl_data_py as ndp  # type: ignore

        def _load(season: int):
            return ndp.import_schedules([season])

        return _load
    except Exception as exc:
        raise RuntimeError(
            "No schedule provider available. Install nflreadpy or nfl_data_py."
        ) from exc


def load_weekly(season: int, week: Optional[int] = None) -> pd.DataFrame:
    load = _resolve_weekly_loader()
    df = load(season)
    # Ensure expected basic columns exist; nfl_data_py schema may evolve
    if week is not None:
        df = df[df["week"] == week]
    # Normalize column names (lower_snake)
    df.columns = [str(c).strip().replace(" ", "_").lower() for c in df.columns]
    return df.reset_index(drop=True)


def describe_availability(season: int) -> str:
    try:
        load_sched = _resolve_schedule_loader()
        sched = load_sched(season)
        if sched is None or len(sched) == 0:
            return f"No schedule available for season {season}."
        weeks = sorted(set(sched["week"].dropna().astype(int)))
        min_w, max_w = (min(weeks), max(weeks)) if weeks else (None, None)
        return (
            f"Season {season} schedule weeks: {weeks if weeks else 'unknown'}. "
            + (f"Min={min_w} Max={max_w}" if weeks else "")
        )
    except Exception as _:
        return f"Could not determine schedule for season {season}."


def main(
    season: Optional[int] = typer.Option(None, help="Season year, e.g., 2024"),
    week: Optional[int] = typer.Option(None, help="Week number (1-22) or omitted for all"),
    output: str = typer.Option("nfl_weekly_stats.csv", help="Output CSV path"),
    allow_empty: bool = typer.Option(
        False, help="Allow empty result without failing (writes empty CSV)"
    ),
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

    try:
        df = load_weekly(season, week)
    except Exception as exc:
        hint = describe_availability(season)
        msg = (
            f"Failed to load weekly data for season={season} week="
            f"{week if week is not None else 'all'}: {exc}. {hint}"
        )
        if allow_empty:
            pd.DataFrame().to_csv(output, index=False)
            print(msg + f" Wrote empty CSV to {output} due to --allow-empty.")
            raise typer.Exit(code=0)
        print(msg, file=sys.stderr)
        raise typer.Exit(code=3)

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
