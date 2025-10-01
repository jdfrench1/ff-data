from __future__ import annotations

from sqlalchemy import text

from nfldb.etl.schedule import load_games, load_seasons_and_weeks
from nfldb.etl.stats import load_weekly_stats

from .conftest import AWAY_TEAM, GAME_KEY, HOME_TEAM, SEASON


def test_load_seasons_weeks_and_teams(database, write_schedule):
    write_schedule()
    load_seasons_and_weeks(SEASON, SEASON)

    with database.begin() as conn:
        seasons = conn.execute(text("SELECT year FROM seasons"))
        assert seasons.fetchall() == [(SEASON,)]

        weeks = conn.execute(
            text(
                "SELECT week_number, start_date, end_date FROM weeks ORDER BY week_number"
            )
        ).fetchall()
        assert weeks == [(1, "2023-09-10", "2023-09-10")]

        teams = conn.execute(
            text("SELECT team_code FROM teams ORDER BY team_code")
        ).fetchall()
        assert teams == [(AWAY_TEAM,), (HOME_TEAM,)]


def test_load_games_upsert(database, write_schedule):
    write_schedule(home_points=24, away_points=17)
    load_seasons_and_weeks(SEASON, SEASON)
    load_games(SEASON, SEASON)

    with database.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT g.home_points, g.away_points, g.nflfast_game_id
                FROM games AS g
                JOIN weeks AS w ON g.week_id = w.week_id
                JOIN seasons AS s ON w.season_id = s.season_id
                WHERE s.year = :season
                """
            ),
            {"season": SEASON},
        ).one()

    assert row.home_points == 24
    assert row.away_points == 17
    assert row.nflfast_game_id == GAME_KEY

    write_schedule(home_points=31, away_points=28)
    load_games(SEASON, SEASON)

    with database.begin() as conn:
        updated = conn.execute(
            text(
                "SELECT home_points, away_points FROM games WHERE nflfast_game_id = :key"
            ),
            {"key": GAME_KEY},
        ).one()

    assert updated.home_points == 31
    assert updated.away_points == 28


def test_load_weekly_stats_transforms(database, write_schedule, write_weekly):
    write_schedule()
    write_weekly()
    load_seasons_and_weeks(SEASON, SEASON)
    load_games(SEASON, SEASON)
    load_weekly_stats(SEASON, SEASON)

    with database.begin() as conn:
        team_stats_rows = conn.execute(
            text(
                """
                SELECT t.team_code, stats.pass_yards, stats.sacks_allowed, stats.sacks_made,
                       stats.turnovers
                FROM team_game_stats AS stats
                JOIN teams AS t ON stats.team_id = t.team_id
                ORDER BY t.team_code
                """
            )
        ).fetchall()

        player_stats_rows = conn.execute(
            text(
                """
                SELECT p.gsis_id, pg.pass_att, pg.pass_yds, pg.sacks, pg.fantasy_ppr
                FROM player_game_stats AS pg
                JOIN players AS p ON pg.player_id = p.player_id
                ORDER BY p.gsis_id
                """
            )
        ).fetchall()

    team_stats = {row.team_code: row for row in team_stats_rows}
    player_stats = {row.gsis_id: row for row in player_stats_rows}

    home_stats = team_stats[HOME_TEAM]
    away_stats = team_stats[AWAY_TEAM]

    assert home_stats.pass_yards == 280
    assert home_stats.sacks_allowed == 2
    assert home_stats.sacks_made == 2
    assert home_stats.turnovers == 1

    assert away_stats.pass_yards == 245
    assert away_stats.sacks_allowed == 3
    assert away_stats.sacks_made == 2
    assert away_stats.turnovers == 0

    qb_one = player_stats["QB1"]
    assert qb_one.pass_att == 35
    assert qb_one.pass_yds == 280
    assert qb_one.sacks == 2
    assert qb_one.fantasy_ppr == 24.5

    qb_two = player_stats["QB2"]
    assert qb_two.pass_att == 30
    assert qb_two.pass_yds == 245
    assert qb_two.sacks == 3
