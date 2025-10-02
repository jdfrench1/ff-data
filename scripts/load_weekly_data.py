import io
import os
import sys
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
import typer

try:  # Prefer nflreadpy to access current-season stats
    import nflreadpy as nfr
except ImportError:  # pragma: no cover
    nfr = None  # type: ignore

try:
    import nfl_data_py as ndp
except ImportError:  # pragma: no cover
    ndp = None  # type: ignore


PLAYER_STATS_RELEASE = (
    "https://github.com/nflverse/nflverse-data/releases/download/player_stats/"
    "player_stats_{suffix}.parquet"
)


def _download_parquet(url: str, timeout: int = 60) -> pd.DataFrame:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return pd.read_parquet(io.BytesIO(response.content))


def _load_weekly_nflreadpy(season: int, verbose: bool = False) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    if nfr is None:
        return None, "nflreadpy not installed"
    try:
        # nflreadpy returns a Polars DataFrame
        stats = nfr.load_player_stats(seasons=season, summary_level="week")
        df = stats.to_pandas()
        if verbose:
            print(
                "nflreadpy.load_player_stats returned",
                f"{len(df)} rows for season {season} with columns: {list(df.columns)[:6]}...",
            )
        return df, None
    except Exception as exc:  # pragma: no cover - handled gracefully
        return None, f"nflreadpy.load_player_stats: {exc}"


def _load_weekly_nfl_data_py(season: int, verbose: bool = False) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    if ndp is None:
        return None, "nfl_data_py not installed"
    try:
        df = ndp.import_weekly_data(years=[season], downcast=False)
        if verbose:
            print(
                "nfl_data_py.import_weekly_data returned",
                f"{len(df)} rows with columns: {list(df.columns)[:6]}...",
            )
        return df, None
    except Exception as exc:
        return None, f"nfl_data_py.import_weekly_data: {exc}"


def _load_weekly_from_release(season: int, verbose: bool = False) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    suffixes = [str(season)]
    current_year = datetime.utcnow().year
    if season >= current_year:
        suffixes.append("current")
    errors: list[str] = []

    for suffix in suffixes:
        url = PLAYER_STATS_RELEASE.format(suffix=suffix)
        try:
            df = _download_parquet(url)
            if verbose:
                print(f"Loaded {len(df)} rows from {url}")
            return df, None
        except Exception as exc:
            errors.append(f"{suffix}: {exc}")

    return None, "release fallback failed: " + "; ".join(errors)


def load_weekly(season: int, week: Optional[int], verbose: bool = False) -> pd.DataFrame:
    errors: list[str] = []

    df, err = _load_weekly_nflreadpy(season, verbose=verbose)
    if df is None and err:
        errors.append(err)

    if df is None:
        df, err = _load_weekly_nfl_data_py(season, verbose=verbose)
        if df is None and err:
            errors.append(err)

    if df is None:
        df, err = _load_weekly_from_release(season, verbose=verbose)
        if df is None and err:
            errors.append(err)

    if df is None:
        raise RuntimeError("No weekly data sources succeeded. " + "; ".join(errors))

    if "week" in df.columns:
        df["week"] = pd.to_numeric(df["week"], errors="coerce")
    if week is not None and "week" in df.columns:
        df = df[df["week"] == int(week)]

    df.columns = [str(c).strip().replace(" ", "_").lower() for c in df.columns]
    df = df.reset_index(drop=True)

    if verbose and errors:
        print("Warnings:", errors)

    return df


def describe_availability(season: int) -> str:
    if nfr is not None:
        try:
            sched = nfr.load_schedules(seasons=season)
            schedule_df = sched.to_pandas()
            weeks = sorted(
                set(pd.to_numeric(schedule_df["week"], errors="coerce").dropna().astype(int))
            )
            return (
                "Schedule via nflreadpy weeks="
                f"{weeks}; min={min(weeks)}; max={max(weeks)}"
            )
        except Exception as exc:
            return f"nflreadpy.load_schedules failed: {exc}"
    if ndp is not None:
        try:
            schedule = ndp.import_schedules([season])
            if schedule.empty:
                return f"Schedule empty for season {season}"
            weeks = sorted(
                set(pd.to_numeric(schedule["week"], errors="coerce").dropna().astype(int))
            )
            return (
                "Schedule via nfl_data_py weeks="
                f"{weeks}; min={min(weeks)}; max={max(weeks)}"
            )
        except Exception as exc:
            return f"nfl_data_py.import_schedules failed: {exc}"
    return "No schedule providers available"


def parse_season(option: Optional[int]) -> int:
    if option is not None:
        return option
    env = os.getenv("SEASON") or os.getenv("season")
    if env:
        if env.lower() == "current":
            return datetime.utcnow().year
        try:
            return int(env)
        except ValueError:
            raise typer.BadParameter(f"Invalid SEASON env value: {env}")
    return datetime.utcnow().year


def parse_week(option: Optional[int]) -> Optional[int]:
    if option is not None:
        return option
    env = os.getenv("WEEK") or os.getenv("week")
    if env:
        if env.lower() in {"", "all", "current"}:
            return None
        try:
            return int(env)
        except ValueError:
            raise typer.BadParameter(f"Invalid WEEK env value: {env}")
    return None


def main(
    season: Optional[int] = typer.Option(
        None, help="Season year (e.g., 2025 or 'current' via env variable)"
    ),
    week: Optional[int] = typer.Option(
        None, help="Week number (leave blank for all weeks)"
    ),
    output: str = typer.Option("nfl_weekly_stats.csv", help="Output CSV path"),
    allow_empty: bool = typer.Option(
        False, help="Allow empty result without failing (writes empty CSV)"
    ),
    verbose: bool = typer.Option(False, help="Enable verbose diagnostics"),
):
    try:
        resolved_season = parse_season(season)
        resolved_week = parse_week(week)
    except typer.BadParameter as exc:
        print(str(exc), file=sys.stderr)
        raise typer.Exit(code=2)

    try:
        df = load_weekly(resolved_season, resolved_week, verbose=verbose)
    except Exception as exc:
        hint = describe_availability(resolved_season)
        msg = (
            f"Failed to load weekly data for season={resolved_season} "
            f"week={resolved_week if resolved_week is not None else 'all'}: {exc}. {hint}"
        )
        if allow_empty:
            pd.DataFrame().to_csv(output, index=False)
            print(msg + f" Wrote empty CSV to {output} due to --allow-empty.")
            raise typer.Exit(code=0)
        print(msg, file=sys.stderr)
        raise typer.Exit(code=3)

    df.to_csv(output, index=False)
    print(
        f"Wrote {len(df)} rows to {output} for season={resolved_season} "
        f"week={resolved_week if resolved_week is not None else 'all'}"
    )


if __name__ == "__main__":
    try:
        typer.run(main)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
