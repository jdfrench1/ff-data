#!/usr/bin/env python
"""Refresh the current NFL week in Postgres using nfldb ETL helpers."""

from __future__ import annotations

try:
    from ._bootstrap import activate  # type: ignore
except ImportError:  # pragma: no cover - fallback for direct execution
    from _bootstrap import activate  # type: ignore

activate()

import argparse
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence, Tuple

import pandas as pd

try:
    import nfl_data_py as nfl
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "nfl_data_py is required for scripts/update_current_week.py"
    ) from exc

from nfldb.etl.schedule import load_games, load_seasons_and_weeks
from nfldb.etl.stats import load_weekly_stats

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"
LOGGER = logging.getLogger("update-current-week")

_PLAYOFF_WEEK_MAP = {
    "wildcard": 19,
    "wild card": 19,
    "divisional": 20,
    "division": 20,
    "conference championships": 21,
    "conference championship": 21,
    "conference": 21,
    "conference champ": 21,
    "championship": 21,
    "super bowl": 22,
}


@dataclass(frozen=True)
class WeekTarget:
    season: int
    week: int


def _normalize_week(value: object) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except ValueError:
        mapped = _PLAYOFF_WEEK_MAP.get(text.lower())
        return mapped


def _as_utc_naive(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment
    return moment.astimezone(timezone.utc).replace(tzinfo=None)


def _kickoff_timestamp(frame: pd.DataFrame) -> pd.Series:
    kickoff = pd.to_datetime(
        frame["gameday"].astype(str)
        + " "
        + frame.get("gametime", "").fillna("00:00:00").astype(str),
        errors="coerce",
    )
    fallback = pd.to_datetime(frame["gameday"], errors="coerce")
    series = kickoff.fillna(fallback)
    return series.dt.tz_localize(None)


def resolve_target_week(
    *, as_of: Optional[datetime] = None, seasons: Optional[Sequence[int]] = None
) -> WeekTarget:
    """Return the season/week that most recently kicked off before ``as_of``."""
    as_of = as_of or datetime.now(timezone.utc)
    as_of_naive = _as_utc_naive(as_of)

    candidate_seasons: Tuple[int, ...]
    if seasons:
        candidate_seasons = tuple(sorted(set(int(year) for year in seasons)))
    else:
        this_year = as_of.year
        candidate_seasons = (this_year - 1, this_year)

    frame = nfl.import_schedules(list(candidate_seasons))

    if frame.empty:
        raise RuntimeError("No schedule data available to resolve target week.")

    working = frame.copy()
    working["week"] = working["week"].apply(_normalize_week)
    working = working.dropna(subset=["week", "season"])
    working["week"] = working["week"].astype(int)
    working["season"] = working["season"].astype(int)
    working["kickoff_ts"] = _kickoff_timestamp(working)
    working = working.dropna(subset=["kickoff_ts"])
    working = working[working["kickoff_ts"] <= as_of_naive]

    if working.empty:
        raise RuntimeError(
            f"No completed games prior to {as_of.isoformat()} in seasons "
            f"{candidate_seasons}."
        )

    grouped = (
        working.groupby(["season", "week"])["kickoff_ts"]
        .max()
        .reset_index()
        .sort_values(["season", "week"])
    )
    latest = grouped.iloc[-1]
    return WeekTarget(season=int(latest["season"]), week=int(latest["week"]))


def refresh_week(target: WeekTarget, *, force_refresh: bool = False) -> None:
    LOGGER.info("Refreshing season=%s week=%s", target.season, target.week)
    load_seasons_and_weeks(target.season, target.season, force_refresh=force_refresh)
    load_games(
        target.season,
        target.season,
        target_weeks=[target.week],
        force_refresh=force_refresh,
    )
    load_weekly_stats(
        target.season,
        target.season,
        target_weeks=[target.week],
        force_refresh=force_refresh,
    )
    LOGGER.info("Season %s week %s refresh completed.", target.season, target.week)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve the most recent NFL week and run the nfldb ETL loaders for it."
        )
    )
    parser.add_argument("--season", type=int, help="Override the detected season.")
    parser.add_argument("--week", type=int, help="Override the detected week.")
    parser.add_argument(
        "--as-of",
        type=str,
        help="ISO timestamp for week resolution (default: now, UTC).",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Redownload source data even if cached parquet files exist.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Console log level.",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Optional path to append log entries.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve the target week but skip database updates.",
    )
    return parser.parse_args(argv)


def configure_logging(level: str, log_file: Optional[str]) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level))

    formatter = logging.Formatter(LOG_FORMAT)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def _parse_as_of(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid --as-of value '{value}': {exc}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    configure_logging(args.log_level, args.log_file)

    as_of = _parse_as_of(args.as_of)

    if args.season and args.week:
        target = WeekTarget(season=args.season, week=args.week)
        LOGGER.info(
            "Using provided season=%s and week=%s overrides.", args.season, args.week
        )
    else:
        target = resolve_target_week(as_of=as_of)
        if args.season and args.season != target.season:
            LOGGER.warning(
                "Resolved season %s differs from --season override %s. Using override.",
                target.season,
                args.season,
            )
            target = WeekTarget(season=args.season, week=target.week)
        if args.week and args.week != target.week:
            LOGGER.warning(
                "Resolved week %s differs from --week override %s. Using override.",
                target.week,
                args.week,
            )
            target = WeekTarget(season=target.season, week=args.week)
        LOGGER.info(
            "Resolved latest completed week: season=%s week=%s",
            target.season,
            target.week,
        )

    if args.dry_run:
        LOGGER.info("Dry-run enabled; skipping ETL execution.")
        return

    refresh_week(target, force_refresh=args.force_refresh)


if __name__ == "__main__":  # pragma: no cover
    main()
