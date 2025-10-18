"""Helpers for resolving and refreshing weekly ETL targets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence, Tuple

import logging

import pandas as pd

try:
    import nfl_data_py as nfl
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("nfl_data_py is required for nfldb.ops.weekly") from exc

from nfldb.etl.schedule import load_games, load_seasons_and_weeks
from nfldb.etl.stats import load_weekly_stats

LOGGER = logging.getLogger(__name__)

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
    """Season/week pair to feed the ETL loaders."""

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
    """Run the ETL loaders for a specific season/week."""
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


def parse_as_of(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO timestamp string (defaulting to UTC when tzinfo missing)."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid --as-of value '{value}': {exc}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


__all__ = ["WeekTarget", "parse_as_of", "resolve_target_week", "refresh_week"]
