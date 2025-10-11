from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

ScheduleWriter = Callable[[int, int], Path]
TeamMetaWriter = Callable[[], Path]
WeeklyWriter = Callable[[], Path]

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from nfldb.api.main import app
from nfldb.db import configure_engine, get_engine
import nfldb.etl.common as common
import nfldb.etl.schedule as schedule

SEASON = 2023
START_WEEK = 1
HOME_TEAM = "KAN"
AWAY_TEAM = "DET"
GAME_KEY = "2023_01_KAN_DET"


def _create_schema() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys = ON")
        conn.exec_driver_sql(
            """
            CREATE TABLE seasons (
                season_id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL UNIQUE
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE teams (
                team_id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_code TEXT NOT NULL UNIQUE,
                team_name TEXT,
                conference TEXT,
                division TEXT
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE weeks (
                week_id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER NOT NULL REFERENCES seasons(season_id) ON DELETE RESTRICT,
                week_number INTEGER NOT NULL,
                start_date TEXT,
                end_date TEXT,
                UNIQUE (season_id, week_number)
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE games (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                nflfast_game_id TEXT UNIQUE,
                week_id INTEGER NOT NULL REFERENCES weeks(week_id) ON DELETE RESTRICT,
                home_team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
                away_team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
                venue TEXT,
                kickoff_ts TEXT,
                roof TEXT,
                surface TEXT,
                vegas_favorite_team_id INTEGER REFERENCES teams(team_id) ON DELETE RESTRICT,
                spread REAL,
                total REAL,
                home_points INTEGER,
                away_points INTEGER,
                winner_team_id INTEGER REFERENCES teams(team_id) ON DELETE RESTRICT,
                UNIQUE (week_id, home_team_id, away_team_id)
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE players (
                player_id INTEGER PRIMARY KEY AUTOINCREMENT,
                gsis_id TEXT UNIQUE,
                pfr_id TEXT UNIQUE,
                full_name TEXT NOT NULL,
                position TEXT,
                birthdate TEXT
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE team_game_stats (
                team_game_stats_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
                team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
                points INTEGER,
                yards INTEGER,
                pass_yards INTEGER,
                rush_yards INTEGER,
                sacks_made INTEGER,
                sacks_allowed INTEGER,
                turnovers INTEGER,
                epa REAL,
                success_rate REAL,
                UNIQUE (game_id, team_id)
            )
            """
        )
        conn.exec_driver_sql(
            """
            CREATE TABLE player_game_stats (
                player_game_stats_id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL REFERENCES games(game_id) ON DELETE CASCADE,
                player_id INTEGER NOT NULL REFERENCES players(player_id) ON DELETE RESTRICT,
                team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE RESTRICT,
                week_id INTEGER NOT NULL REFERENCES weeks(week_id) ON DELETE RESTRICT,
                position TEXT,
                starter INTEGER,
                snaps_off INTEGER,
                snaps_def INTEGER,
                snaps_st INTEGER,
                pass_att INTEGER,
                pass_cmp INTEGER,
                pass_yds INTEGER,
                pass_td INTEGER,
                int_thrown INTEGER,
                rush_att INTEGER,
                rush_yds INTEGER,
                rush_td INTEGER,
                targets INTEGER,
                receptions INTEGER,
                rec_yds INTEGER,
                rec_td INTEGER,
                tackles INTEGER,
                sacks REAL,
                interceptions INTEGER,
                fumbles INTEGER,
                fantasy_ppr REAL,
                UNIQUE (game_id, player_id)
            )
            """
        )


@pytest.fixture()
def raw_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "RAW_DIR", tmp_path)
    monkeypatch.setattr(schedule, "RAW_DIR", tmp_path)
    return tmp_path


@pytest.fixture()
def database(tmp_path):
    db_path = tmp_path / "test.db"
    db_url = f"sqlite+pysqlite:///{db_path}"
    os.environ["DATABASE_URL"] = db_url
    configure_engine(db_url)
    _create_schema()
    return get_engine()


@pytest.fixture()
def write_team_meta(raw_dir: Path) -> TeamMetaWriter:
    def _writer() -> Path:
        team_df = pd.DataFrame(
            [
                {
                    "team_abbr": HOME_TEAM,
                    "team_name": "Kansas City Chiefs",
                    "team_conf": "AFC",
                    "team_division": "West",
                },
                {
                    "team_abbr": AWAY_TEAM,
                    "team_name": "Detroit Lions",
                    "team_conf": "NFC",
                    "team_division": "North",
                },
            ]
        )
        path = raw_dir / "team_desc.parquet"
        team_df.to_parquet(path, index=False)
        return path

    return _writer


@pytest.fixture()
def write_schedule(raw_dir: Path, write_team_meta: TeamMetaWriter) -> ScheduleWriter:
    write_team_meta()

    def _writer(home_points: int = 27, away_points: int = 21) -> Path:
        schedule_df = pd.DataFrame(
            [
                {
                    "season": SEASON,
                    "week": START_WEEK,
                    "game_id": GAME_KEY,
                    "gameday": "2023-09-10",
                    "gametime": "13:00",
                    "home_team": HOME_TEAM,
                    "away_team": AWAY_TEAM,
                    "stadium": "Arrowhead Stadium",
                    "roof": "outdoors",
                    "surface": "grass",
                    "spread_line": -4.5,
                    "total_line": 51.5,
                    "home_score": home_points,
                    "away_score": away_points,
                }
            ]
        )
        path = raw_dir / f"schedule_{SEASON}_{SEASON}.parquet"
        schedule_df.to_parquet(path, index=False)
        return path

    return _writer


@pytest.fixture()
def write_weekly(raw_dir: Path) -> WeeklyWriter:
    def _writer() -> Path:
        weekly_df = pd.DataFrame(
            [
                {
                    "player_id": "QB1",
                    "player_display_name": "Quarterback One",
                    "position": "QB",
                    "position_group": "QB",
                    "recent_team": HOME_TEAM,
                    "season": SEASON,
                    "week": START_WEEK,
                    "attempts": 35,
                    "completions": 24,
                    "passing_yards": 280,
                    "passing_tds": 3,
                    "interceptions": 1,
                    "carries": 4,
                    "rushing_yards": 32,
                    "rushing_tds": 0,
                    "targets": 0,
                    "receptions": 0,
                    "receiving_yards": 0,
                    "receiving_tds": 0,
                    "sacks": 2,
                    "fantasy_points_ppr": 24.5,
                    "rushing_fumbles_lost": 0,
                    "receiving_fumbles_lost": 0,
                    "sack_fumbles_lost": 0,
                },
                {
                    "player_id": "WR1",
                    "player_display_name": "Receiver One",
                    "position": "WR",
                    "position_group": "WR",
                    "recent_team": HOME_TEAM,
                    "season": SEASON,
                    "week": START_WEEK,
                    "attempts": 0,
                    "completions": 0,
                    "passing_yards": 0,
                    "passing_tds": 0,
                    "interceptions": 0,
                    "carries": 1,
                    "rushing_yards": 8,
                    "rushing_tds": 0,
                    "targets": 9,
                    "receptions": 6,
                    "receiving_yards": 84,
                    "receiving_tds": 1,
                    "sacks": 0,
                    "fantasy_points_ppr": 20.4,
                    "rushing_fumbles_lost": 0,
                    "receiving_fumbles_lost": 0,
                    "sack_fumbles_lost": 0,
                },
                {
                    "player_id": "EDGE1",
                    "player_display_name": "Edge Rusher",
                    "position": "LB",
                    "position_group": "DL",
                    "recent_team": HOME_TEAM,
                    "season": SEASON,
                    "week": START_WEEK,
                    "attempts": 0,
                    "completions": 0,
                    "passing_yards": 0,
                    "passing_tds": 0,
                    "interceptions": 0,
                    "carries": 0,
                    "rushing_yards": 0,
                    "rushing_tds": 0,
                    "targets": 0,
                    "receptions": 0,
                    "receiving_yards": 0,
                    "receiving_tds": 0,
                    "sacks": 1.5,
                    "fantasy_points_ppr": 0,
                    "rushing_fumbles_lost": 0,
                    "receiving_fumbles_lost": 0,
                    "sack_fumbles_lost": 0,
                },
                {
                    "player_id": "QB2",
                    "player_display_name": "Quarterback Two",
                    "position": "QB",
                    "position_group": "QB",
                    "recent_team": AWAY_TEAM,
                    "season": SEASON,
                    "week": START_WEEK,
                    "attempts": 30,
                    "completions": 19,
                    "passing_yards": 245,
                    "passing_tds": 2,
                    "interceptions": 0,
                    "carries": 3,
                    "rushing_yards": 12,
                    "rushing_tds": 0,
                    "targets": 0,
                    "receptions": 0,
                    "receiving_yards": 0,
                    "receiving_tds": 0,
                    "sacks": 3,
                    "fantasy_points_ppr": 21.1,
                    "rushing_fumbles_lost": 0,
                    "receiving_fumbles_lost": 0,
                    "sack_fumbles_lost": 0,
                },
                {
                    "player_id": "DL1",
                    "player_display_name": "Defender One",
                    "position": "DL",
                    "position_group": "DL",
                    "recent_team": AWAY_TEAM,
                    "season": SEASON,
                    "week": START_WEEK,
                    "attempts": 0,
                    "completions": 0,
                    "passing_yards": 0,
                    "passing_tds": 0,
                    "interceptions": 0,
                    "carries": 0,
                    "rushing_yards": 0,
                    "rushing_tds": 0,
                    "targets": 0,
                    "receptions": 0,
                    "receiving_yards": 0,
                    "receiving_tds": 0,
                    "sacks": 2,
                    "fantasy_points_ppr": 0,
                    "rushing_fumbles_lost": 0,
                    "receiving_fumbles_lost": 0,
                    "sack_fumbles_lost": 0,
                },
            ]
        )
        path = raw_dir / f"weekly_{SEASON}_{SEASON}.parquet"
        weekly_df.to_parquet(path, index=False)
        return path

    return _writer


@pytest.fixture()
def write_weekly_alt_schema(
    raw_dir: Path, write_weekly: WeeklyWriter
) -> WeeklyWriter:
    def _writer() -> Path:
        path = write_weekly()
        df = pd.read_parquet(path)
        qb_mask = df["position_group"] == "QB"
        df["team"] = df["recent_team"]
        df["passing_interceptions"] = df["interceptions"]
        df["sacks_suffered"] = df["sacks"].where(qb_mask, 0).fillna(0)
        df["def_sacks"] = df["sacks"].where(~qb_mask, 0).fillna(0)
        df = df.drop(columns=["recent_team", "interceptions", "sacks"])
        df.to_parquet(path, index=False)
        return path

    return _writer


@pytest.fixture()
def client(database):
    return TestClient(app)


@pytest.fixture()
def run_full_pipeline(
    database, write_schedule: ScheduleWriter, write_weekly: WeeklyWriter
):
    write_schedule()
    write_weekly()
    from nfldb.etl.schedule import load_games, load_seasons_and_weeks
    from nfldb.etl.stats import load_weekly_stats

    load_seasons_and_weeks(SEASON, SEASON)
    load_games(SEASON, SEASON)
    load_weekly_stats(SEASON, SEASON)
