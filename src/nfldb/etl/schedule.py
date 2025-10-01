from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence

import nfl_data_py as nfl
import pandas as pd
from sqlalchemy import text

from .common import RAW_DIR, cache_path
from ..db import get_engine







@dataclass
class ScheduleData:
    seasons: List[int]
    frame: pd.DataFrame


def _cache_path(kind: str, season_start: int, season_end: int) -> Path:
    return cache_path(kind, season_start, season_end)


def _load_schedule_df(
    season_start: int,
    season_end: int,
    force_refresh: bool = False,
) -> ScheduleData:
    seasons = list(range(season_start, season_end + 1))
    cache_file = _cache_path("schedule", season_start, season_end)
    if cache_file.exists() and not force_refresh:
        frame = pd.read_parquet(cache_file)
        return ScheduleData(seasons=seasons, frame=frame)

    frame = nfl.import_schedules(seasons)
    frame.to_parquet(cache_file, index=False)
    return ScheduleData(seasons=seasons, frame=frame)


def _load_team_meta(force_refresh: bool = False) -> pd.DataFrame:
    cache_file = RAW_DIR / "team_desc.parquet"
    if cache_file.exists() and not force_refresh:
        return pd.read_parquet(cache_file)
    frame = nfl.import_team_desc()
    frame.to_parquet(cache_file, index=False)
    return frame


def load_seasons_and_weeks(
    season_start: int,
    season_end: int,
    *,
    force_refresh: bool = False,
) -> None:
    """Ensure seasons, weeks, and teams exist for the requested range."""
    schedule = _load_schedule_df(season_start, season_end, force_refresh=force_refresh)
    team_meta = _load_team_meta(force_refresh=force_refresh)

    df = schedule.frame.copy()
    df["gameday"] = pd.to_datetime(df["gameday"], errors="coerce")
    df = df[df["week"].astype(str).str.isdigit()].copy()
    df["week"] = df["week"].astype(int)

    engine = get_engine()
    seasons_records = [{"year": year} for year in schedule.seasons]
    week_records = (
        df.groupby(["season", "week"])  # type: ignore[call-arg]
        .agg(start_date=("gameday", "min"), end_date=("gameday", "max"))
        .reset_index()
    )

    # Teams
    team_codes: set[str] = set(df["home_team"]).union(set(df["away_team"]))
    team_meta = team_meta[team_meta["team_abbr"].isin(team_codes)].copy()
    team_meta = team_meta.drop_duplicates(subset=["team_abbr"])
    team_records = [
        {
            "team_code": row.team_abbr,
            "team_name": row.team_name,
            "conference": getattr(row, 'team_conf', getattr(row, 'conference', None)),
            "division": getattr(row, 'team_division', getattr(row, 'division', None)),
        }
        for row in team_meta.itertuples(index=False)
    ]

    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO seasons (year) VALUES (:year) "
                "ON CONFLICT (year) DO NOTHING"
            ),
            seasons_records,
        )

        conn.execute(
            text(
                "INSERT INTO teams (team_code, team_name, conference, division) "
                "VALUES (:team_code, :team_name, :conference, :division) "
                "ON CONFLICT (team_code) DO UPDATE SET "
                "team_name = EXCLUDED.team_name, "
                "conference = EXCLUDED.conference, "
                "division = EXCLUDED.division"
            ),
            team_records,
        )

        week_payload = [
            {
                "season": int(row.season),
                "week_number": int(row.week),
                "start_date": row.start_date.date() if isinstance(row.start_date, pd.Timestamp) else None,
                "end_date": row.end_date.date() if isinstance(row.end_date, pd.Timestamp) else None,
            }
            for row in week_records.itertuples(index=False)
        ]

        conn.execute(
            text(
                "INSERT INTO weeks (season_id, week_number, start_date, end_date) "
                "SELECT seasons.season_id, :week_number, :start_date, :end_date "
                "FROM seasons WHERE seasons.year = :season "
                "ON CONFLICT (season_id, week_number) DO UPDATE SET "
                "start_date = EXCLUDED.start_date, "
                "end_date = EXCLUDED.end_date"
            ),
            week_payload,
        )


def _favorite_team_code(row: pd.Series) -> Optional[str]:
    spread = row.get("spread_line")
    if pd.isna(spread):
        return None
    try:
        spread_value = float(spread)
    except (TypeError, ValueError):
        return None
    if spread_value < 0:
        return row["home_team"]
    if spread_value > 0:
        return row["away_team"]
    return None


def load_games(
    season_start: int,
    season_end: int,
    *,
    target_weeks: Optional[Sequence[int]] = None,
    force_refresh: bool = False,
) -> None:
    """Load games for the given seasons into Postgres."""
    schedule = _load_schedule_df(season_start, season_end, force_refresh=force_refresh)
    df = schedule.frame.copy()
    df = df[df["week"].astype(str).str.isdigit()].copy()
    df["week"] = df["week"].astype(int)
    if target_weeks is not None:
        mask = df["week"].isin(list(target_weeks))
        df = df[mask]

    df["favorite_team"] = df.apply(_favorite_team_code, axis=1)
    df["winner"] = df.apply(
        lambda r: r.home_team
        if pd.notna(r.home_score)
        and pd.notna(r.away_score)
        and r.home_score > r.away_score
        else (
            r.away_team
            if pd.notna(r.home_score)
            and pd.notna(r.away_score)
            and r.away_score > r.home_score
            else None
        ),
        axis=1,
    )

    df["kickoff_ts"] = pd.to_datetime(
        df["gameday"].astype(str) + " " + df["gametime"].astype(str),
        errors="coerce",
    )

    payload = []
    for row in df.itertuples(index=False):
        payload.append(
            {
                "game_id": row.game_id,
                "season": int(row.season),
                "week_number": int(row.week),
                "home_team": row.home_team,
                "away_team": row.away_team,
                "venue": row.stadium,
                "kickoff_ts": row.kickoff_ts.to_pydatetime() if isinstance(row.kickoff_ts, pd.Timestamp) else None,
                "roof": row.roof,
                "surface": row.surface,
                "favorite_team": row.favorite_team,
                "spread": float(row.spread_line) if pd.notna(row.spread_line) else None,
                "total": float(row.total_line) if pd.notna(row.total_line) else None,
                "home_points": int(row.home_score) if pd.notna(row.home_score) else None,
                "away_points": int(row.away_score) if pd.notna(row.away_score) else None,
                "winner": row.winner,
            }
        )

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO games (nflfast_game_id, week_id, home_team_id, away_team_id, venue, "
                "kickoff_ts, roof, surface, vegas_favorite_team_id, spread, total, home_points, "
                "away_points, winner_team_id) "
                "SELECT :game_id, weeks.week_id, home.team_id, away.team_id, :venue, :kickoff_ts, "
                ":roof, :surface, fav.team_id, :spread, :total, :home_points, :away_points, win.team_id "
                "FROM weeks "
                "JOIN seasons ON seasons.season_id = weeks.season_id AND seasons.year = :season "
                "JOIN teams AS home ON home.team_code = :home_team "
                "JOIN teams AS away ON away.team_code = :away_team "
                "LEFT JOIN teams AS fav ON fav.team_code = :favorite_team "
                "LEFT JOIN teams AS win ON win.team_code = :winner "
                "WHERE weeks.week_number = :week_number "
                "ON CONFLICT (week_id, home_team_id, away_team_id) DO UPDATE SET "
                "nflfast_game_id = EXCLUDED.nflfast_game_id, "
                "venue = EXCLUDED.venue, "
                "kickoff_ts = EXCLUDED.kickoff_ts, "
                "roof = EXCLUDED.roof, "
                "surface = EXCLUDED.surface, "
                "vegas_favorite_team_id = EXCLUDED.vegas_favorite_team_id, "
                "spread = EXCLUDED.spread, "
                "total = EXCLUDED.total, "
                "home_points = EXCLUDED.home_points, "
                "away_points = EXCLUDED.away_points, "
                "winner_team_id = EXCLUDED.winner_team_id"
            ),
            payload,
        )

