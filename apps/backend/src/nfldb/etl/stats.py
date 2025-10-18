from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import logging

import io

try:
    import nflreadpy as nfr  # type: ignore
except ImportError:  # pragma: no cover
    nfr = None  # type: ignore

try:
    import nfl_data_py as ndp  # type: ignore
except ImportError:  # pragma: no cover
    ndp = None  # type: ignore

import pandas as pd
import requests
from sqlalchemy import inspect, text

from ..db import get_engine
from .common import cache_path
from .schedule import _load_schedule_df


@dataclass
class WeeklyData:
    seasons: List[int]
    frame: pd.DataFrame


logger = logging.getLogger(__name__)

STAGING_TABLE = "nfl_weekly_stats"
DEFAULT_CHUNK_SIZE = 1000
MAX_QUERY_PARAMS = 65535

_STAGING_COLUMN_RENAMES = {
    "recent_team": "team",
    "interceptions": "passing_interceptions",
    "sacks": "sacks_suffered",
    "sack_yards": "sack_yards_lost",
}


def _weekly_cache_path(season_start: int, season_end: int) -> Path:
    return cache_path("weekly", season_start, season_end)


def _load_weekly_nflreadpy(
    season: int, verbose: bool = False
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    if nfr is None:
        return None, "nflreadpy not installed"
    try:
        stats = nfr.load_player_stats(seasons=season, summary_level="week")
        df = stats.to_pandas()
        if verbose:
            print(
                f"nflreadpy.load_player_stats returned {len(df)} rows for season {season}"
            )
        return df, None
    except Exception as exc:  # pragma: no cover
        return None, f"nflreadpy.load_player_stats: {exc}"


def _load_weekly_nfl_data_py(
    season: int, verbose: bool = False
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    if ndp is None:
        return None, "nfl_data_py not installed"
    try:
        df = ndp.import_weekly_data(years=[season], downcast=False)
        if verbose:
            print(
                f"nfl_data_py.import_weekly_data returned {len(df)} rows for season {season}"
            )
        return df, None
    except Exception as exc:  # pragma: no cover
        return None, f"nfl_data_py.import_weekly_data: {exc}"


def _download_parquet(url: str, timeout: int = 60) -> pd.DataFrame:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return pd.read_parquet(io.BytesIO(response.content))


PLAYER_STATS_RELEASE = (
    "https://github.com/nflverse/nflverse-data/releases/download/player_stats/"
    "player_stats_{suffix}.parquet"
)


def _load_weekly_from_release(
    season: int, verbose: bool = False
) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
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


def _load_weekly_df(
    season_start: int,
    season_end: int,
    force_refresh: bool = False,
    verbose: bool = False,
) -> WeeklyData:
    seasons = list(range(season_start, season_end + 1))
    cache_file = _weekly_cache_path(season_start, season_end)
    if cache_file.exists() and not force_refresh:
        frame = pd.read_parquet(cache_file)
        return WeeklyData(seasons=seasons, frame=frame)

    errors: list[str] = []
    data_frames: list[pd.DataFrame] = []
    for season in seasons:
        df: Optional[pd.DataFrame] = None
        err: Optional[str]
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
            raise RuntimeError(
                "No weekly data sources succeeded for season="
                f"{season}: " + "; ".join(errors)
            )
        if "season" not in df.columns:
            df["season"] = season
        data_frames.append(df)

    combined = pd.concat(data_frames, ignore_index=True)
    combined.to_parquet(cache_file, index=False)
    return WeeklyData(seasons=seasons, frame=combined)


def _normalize_weekly_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()
    normalized.columns = [
        str(column).strip().replace(" ", "_").lower() for column in normalized.columns
    ]
    normalized = normalized.reset_index(drop=True)
    return normalized


def _resolve_chunk_size(column_count: int) -> int:
    if column_count <= 0:
        return DEFAULT_CHUNK_SIZE
    max_rows = MAX_QUERY_PARAMS // max(1, column_count)
    max_rows = max(1, max_rows)
    return min(DEFAULT_CHUNK_SIZE, max_rows)


def _delete_existing_rows(
    conn,
    seasons: Sequence[int],
    weeks: Optional[Sequence[int]],
) -> None:
    if not seasons:
        return
    if weeks:
        delete_stmt = text(
            "DELETE FROM nfl_weekly_stats WHERE season = :season AND week = :week"
        )
        for season in seasons:
            for week in weeks:
                conn.execute(delete_stmt, {"season": int(season), "week": int(week)})
    else:
        delete_stmt = text("DELETE FROM nfl_weekly_stats WHERE season = :season")
        for season in seasons:
            conn.execute(delete_stmt, {"season": int(season)})


def _stage_weekly_stats(
    df: pd.DataFrame,
    *,
    target_weeks: Optional[Sequence[int]] = None,
) -> None:
    if df.empty:
        logger.info("Weekly stats frame is empty; skipping staging upload.")
        return

    if "season" not in df.columns:
        logger.warning(
            "Weekly stats frame missing 'season' column; skipping staging upload."
        )
        return

    normalized = _normalize_weekly_columns(df)

    if "team" in normalized.columns and "recent_team" in normalized.columns:
        normalized = normalized.drop(columns=["team"])

    rename_map = {
        source: target
        for source, target in _STAGING_COLUMN_RENAMES.items()
        if source in normalized.columns and target not in normalized.columns
    }
    if rename_map:
        normalized = normalized.rename(columns=rename_map)
    seasons = sorted(
        {
            int(season)
            for season in normalized["season"].dropna().unique().tolist()  # type: ignore[arg-type]
        }
    )

    week_filter: Optional[List[int]] = None
    if target_weeks is not None:
        week_filter = sorted({int(week) for week in target_weeks})
        if "week" not in normalized.columns:
            logger.warning(
                "Weekly stats frame missing 'week' column; cannot apply week filter."
            )
            week_filter = None

    engine = get_engine()
    try:
        with engine.begin() as conn:
            staging_columns: Optional[List[str]] = None
            inspector = inspect(engine)
            if inspector.has_table(STAGING_TABLE):
                staging_columns = [
                    column["name"] for column in inspector.get_columns(STAGING_TABLE)
                ]
            if staging_columns:
                extra_columns = [
                    column for column in normalized.columns if column not in staging_columns
                ]
                if extra_columns:
                    logger.debug(
                        "Dropping columns not present in %s: %s",
                        STAGING_TABLE,
                        ", ".join(sorted(extra_columns)),
                    )
                normalized = normalized[
                    [column for column in staging_columns if column in normalized.columns]
                ]

            _delete_existing_rows(conn, seasons, week_filter)
            chunk_size = _resolve_chunk_size(len(normalized.columns))
            normalized.to_sql(
                STAGING_TABLE,
                conn,
                if_exists="append",
                index=False,
                chunksize=chunk_size,
                method="multi",
            )
    except Exception:
        logger.exception("Failed to stage weekly stats into %s", STAGING_TABLE)
        raise


def _prepare_schedule_lookup(schedule_df: pd.DataFrame) -> pd.DataFrame:
    records = []
    for row in schedule_df.itertuples(index=False):
        week = row.week
        if not str(week).isdigit():
            continue
        week_number = int(week)
        season = int(row.season)
        home_points = row.home_score if not pd.isna(row.home_score) else None
        away_points = row.away_score if not pd.isna(row.away_score) else None
        records.append(
            {
                "season": season,
                "week": week_number,
                "team_code": row.home_team,
                "game_id": row.game_id,
                "points": home_points,
            }
        )
        records.append(
            {
                "season": season,
                "week": week_number,
                "team_code": row.away_team,
                "game_id": row.game_id,
                "points": away_points,
            }
        )
    return pd.DataFrame.from_records(records)


def _clean_weekly_frame(
    frame: pd.DataFrame, target_weeks: Optional[Sequence[int]] = None
) -> pd.DataFrame:
    df = frame.copy()

    if "recent_team" not in df.columns:
        if "team" in df.columns:
            df["recent_team"] = df["team"]
        else:  # pragma: no cover - defensive guard for unexpected feeds
            raise KeyError(
                "weekly stats feed is missing both 'recent_team' and 'team' columns"
            )

    if "interceptions" not in df.columns:
        if "passing_interceptions" in df.columns:
            df["interceptions"] = df["passing_interceptions"]
        else:
            df["interceptions"] = 0

    qb_sacks_source: pd.Series
    if "sacks" in df.columns:
        qb_sacks_source = df["sacks"]
    elif "sacks_suffered" in df.columns:
        qb_sacks_source = df["sacks_suffered"]
    else:
        qb_sacks_source = pd.Series(0, index=df.index, dtype="float64")

    defender_sacks_source: pd.Series
    if "def_sacks" in df.columns:
        defender_sacks_source = df["def_sacks"]
    elif "sacks" in df.columns:
        defender_sacks_source = df["sacks"]
    else:
        defender_sacks_source = pd.Series(0, index=df.index, dtype="float64")

    position_group = df.get("position_group")
    if position_group is None:
        position_group = pd.Series("", index=df.index, dtype="object")
    position_group = position_group.fillna("")

    qb_mask = position_group == "QB"
    defender_mask = position_group.isin(["DL", "LB", "DB"])

    qb_sacks_values = qb_sacks_source.fillna(0)
    defender_sacks_values = defender_sacks_source.fillna(0)

    df["sacks"] = 0.0
    if qb_mask.any():
        df.loc[qb_mask, "sacks"] = qb_sacks_values[qb_mask]
    if defender_mask.any():
        df.loc[defender_mask, "sacks"] = defender_sacks_values[defender_mask]

    df = df[df["player_id"].notna()]
    df = df[df["player_id"] != ""]
    df = df[df["recent_team"].notna()]
    df = df[df["recent_team"] != "TOT"]
    df["player_id"] = df["player_id"].astype(str)
    df["recent_team"] = df["recent_team"].astype(str)
    df["season"] = df["season"].astype(int)
    df["week"] = df["week"].astype(int)
    if target_weeks is not None:
        df = df[df["week"].isin(list(target_weeks))]
    df = df.reset_index(drop=True)

    df["sacks_allowed"] = qb_sacks_values.where(qb_mask, 0.0)
    df["def_sacks"] = defender_sacks_values.where(defender_mask, 0.0)
    fumble_components = [
        df.get("rushing_fumbles_lost", pd.Series(0, index=df.index)).fillna(0),
        df.get("receiving_fumbles_lost", pd.Series(0, index=df.index)).fillna(0),
        df.get("sack_fumbles_lost", pd.Series(0, index=df.index)).fillna(0),
    ]
    df["fumbles_total"] = sum(fumble_components)
    df["turnovers"] = (
        df["interceptions"].fillna(0).where(df["position_group"] == "QB", 0.0)
        + df["fumbles_total"]
    )
    return df


def _upsert_players(df: pd.DataFrame) -> None:
    player_info = (
        df[["player_id", "player_display_name", "position"]]
        .drop_duplicates(subset=["player_id"])
        .rename(
            columns={
                "player_id": "gsis_id",
                "player_display_name": "full_name",
            }
        )
    )
    player_info["position"] = player_info["position"].replace({"": None})

    records = [
        {
            "gsis_id": row.gsis_id,
            "full_name": row.full_name,
            "position": row.position,
        }
        for row in player_info.itertuples(index=False)
        if row.gsis_id
    ]

    if not records:
        return

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO players (gsis_id, full_name, position) "
                "VALUES (:gsis_id, :full_name, :position) "
                "ON CONFLICT (gsis_id) DO UPDATE SET "
                "full_name = EXCLUDED.full_name, "
                "position = EXCLUDED.position"
            ),
            records,
        )


def _aggregate_team_stats(df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        df.groupby(["season", "week", "recent_team"], as_index=False)
        .agg(
            pass_yards=("passing_yards", "sum"),
            rush_yards=("rushing_yards", "sum"),
            sacks_allowed=("sacks_allowed", "sum"),
            sacks_made=("def_sacks", "sum"),
            turnovers=("turnovers", "sum"),
        )
        .rename(columns={"recent_team": "team_code"})
    )
    grouped["yards"] = grouped["pass_yards"] + grouped["rush_yards"]
    return grouped


def _nullable(value):
    return None if pd.isna(value) else value


def _to_int(value):
    if pd.isna(value):
        return None
    return int(round(float(value)))


def _upsert_team_stats(team_stats: pd.DataFrame, lookup: pd.DataFrame) -> None:
    merged = team_stats.merge(lookup, on=["season", "week", "team_code"], how="left")
    merged = merged[merged["game_id"].notna()]
    records = []
    for row in merged.itertuples(index=False):
        records.append(
            {
                "game_key": row.game_id,
                "team_code": row.team_code,
                "season": int(row.season),
                "week": int(row.week),
                "points": _to_int(row.points) if hasattr(row, "points") else None,
                "yards": _to_int(row.yards),
                "pass_yards": _to_int(row.pass_yards),
                "rush_yards": _to_int(row.rush_yards),
                "sacks_made": _to_int(row.sacks_made),
                "sacks_allowed": _to_int(row.sacks_allowed),
                "turnovers": _to_int(row.turnovers),
            }
        )

    if not records:
        return

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO team_game_stats (game_id, team_id, points, yards, pass_yards, "
                "rush_yards, sacks_made, sacks_allowed, turnovers) "
                "SELECT g.game_id, t.team_id, :points, :yards, :pass_yards, :rush_yards, "
                ":sacks_made, :sacks_allowed, :turnovers "
                "FROM games g "
                "JOIN teams t ON t.team_code = :team_code "
                "WHERE g.nflfast_game_id = :game_key "
                "ON CONFLICT (game_id, team_id) DO UPDATE SET "
                "points = EXCLUDED.points, "
                "yards = EXCLUDED.yards, "
                "pass_yards = EXCLUDED.pass_yards, "
                "rush_yards = EXCLUDED.rush_yards, "
                "sacks_made = EXCLUDED.sacks_made, "
                "sacks_allowed = EXCLUDED.sacks_allowed, "
                "turnovers = EXCLUDED.turnovers"
            ),
            records,
        )


def _prepare_player_payload(df: pd.DataFrame, lookup: pd.DataFrame) -> pd.DataFrame:
    merged = df.merge(
        lookup,
        left_on=["season", "week", "recent_team"],
        right_on=["season", "week", "team_code"],
        how="left",
    )
    merged = merged[merged["game_id"].notna()]
    merged["fumbles"] = merged["fumbles_total"].fillna(0)
    return merged


def _upsert_player_stats(player_df: pd.DataFrame) -> None:
    if player_df.empty:
        return

    records = []
    for row in player_df.itertuples(index=False):
        records.append(
            {
                "game_key": row.game_id,
                "season": int(row.season),
                "week": int(row.week),
                "team_code": row.recent_team,
                "player_gsis": row.player_id,
                "position": row.position if row.position else None,
                "pass_att": _nullable(row.attempts),
                "pass_cmp": _nullable(row.completions),
                "pass_yds": _nullable(row.passing_yards),
                "pass_td": _nullable(row.passing_tds),
                "int_thrown": _nullable(row.interceptions),
                "rush_att": _nullable(row.carries),
                "rush_yds": _nullable(row.rushing_yards),
                "rush_td": _nullable(row.rushing_tds),
                "targets": _nullable(row.targets),
                "receptions": _nullable(row.receptions),
                "rec_yds": _nullable(row.receiving_yards),
                "rec_td": _nullable(row.receiving_tds),
                "tackles": None,
                "sacks": _nullable(row.sacks),
                "interceptions": None,
                "fumbles": _nullable(row.fumbles),
                "fantasy_ppr": _nullable(row.fantasy_points_ppr),
            }
        )

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO player_game_stats (game_id, player_id, team_id, week_id, position, "
                "starter, snaps_off, snaps_def, snaps_st, pass_att, pass_cmp, pass_yds, pass_td, "
                "int_thrown, rush_att, rush_yds, rush_td, targets, receptions, rec_yds, rec_td, "
                "tackles, sacks, interceptions, fumbles, fantasy_ppr) "
                "SELECT g.game_id, p.player_id, t.team_id, w.week_id, :position, NULL, NULL, NULL, NULL, "
                ":pass_att, :pass_cmp, :pass_yds, :pass_td, :int_thrown, :rush_att, :rush_yds, :rush_td, "
                ":targets, :receptions, :rec_yds, :rec_td, :tackles, :sacks, :interceptions, :fumbles, :fantasy_ppr "
                "FROM games g "
                "JOIN teams t ON t.team_code = :team_code "
                "JOIN seasons s ON s.year = :season "
                "JOIN weeks w ON w.season_id = s.season_id AND w.week_number = :week "
                "JOIN players p ON p.gsis_id = :player_gsis "
                "WHERE g.nflfast_game_id = :game_key "
                "ON CONFLICT (game_id, player_id) DO UPDATE SET "
                "position = EXCLUDED.position, "
                "pass_att = EXCLUDED.pass_att, "
                "pass_cmp = EXCLUDED.pass_cmp, "
                "pass_yds = EXCLUDED.pass_yds, "
                "pass_td = EXCLUDED.pass_td, "
                "int_thrown = EXCLUDED.int_thrown, "
                "rush_att = EXCLUDED.rush_att, "
                "rush_yds = EXCLUDED.rush_yds, "
                "rush_td = EXCLUDED.rush_td, "
                "targets = EXCLUDED.targets, "
                "receptions = EXCLUDED.receptions, "
                "rec_yds = EXCLUDED.rec_yds, "
                "rec_td = EXCLUDED.rec_td, "
                "sacks = EXCLUDED.sacks, "
                "fumbles = EXCLUDED.fumbles, "
                "fantasy_ppr = EXCLUDED.fantasy_ppr"
            ),
            records,
        )


def load_weekly_stats(
    season_start: int,
    season_end: int,
    *,
    target_weeks: Optional[Sequence[int]] = None,
    force_refresh: bool = False,
    stage_raw: bool = False,
) -> None:
    schedule = _load_schedule_df(season_start, season_end, force_refresh=force_refresh)
    schedule_lookup = _prepare_schedule_lookup(schedule.frame)
    weekly = _load_weekly_df(season_start, season_end, force_refresh=force_refresh)
    weekly_df = _clean_weekly_frame(weekly.frame, target_weeks=target_weeks)

    if stage_raw:
        _stage_weekly_stats(weekly_df, target_weeks=target_weeks)

    _upsert_players(weekly_df)
    team_stats = _aggregate_team_stats(weekly_df)
    _upsert_team_stats(team_stats, schedule_lookup)

    player_payload = _prepare_player_payload(weekly_df, schedule_lookup)
    _upsert_player_stats(player_payload)
