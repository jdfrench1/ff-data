from __future__ import annotations

from sqlalchemy import text

from nfldb.db import session_scope

from .conftest import AWAY_TEAM, HOME_TEAM, SEASON, START_WEEK


def test_api_endpoints(client, run_full_pipeline):
    run_full_pipeline

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    seasons = client.get("/api/v1/seasons")
    assert seasons.status_code == 200
    season_payload = seasons.json()
    assert len(season_payload) == 1
    assert season_payload[0]["year"] == SEASON

    weeks = client.get(f"/api/v1/weeks?season={SEASON}")
    assert weeks.status_code == 200
    week_payload = weeks.json()
    assert len(week_payload) == 1
    assert week_payload[0]["week_number"] == 1
    assert week_payload[0]["start_date"] == "2023-09-10"

    games = client.get(f"/api/v1/games?season={SEASON}")
    assert games.status_code == 200
    game_payload = games.json()
    assert len(game_payload) == 1
    game = game_payload[0]
    assert game["season"] == SEASON
    assert game["home_team"] == HOME_TEAM
    assert game["away_team"] == AWAY_TEAM

    game_detail = client.get(f"/api/v1/games/{game['game_id']}")
    assert game_detail.status_code == 200
    assert game_detail.json()["game_id"] == game["game_id"]

    team_stats = client.get(f"/api/v1/team-stats?season={SEASON}")
    assert team_stats.status_code == 200
    stats_payload = team_stats.json()
    assert {row["team_code"] for row in stats_payload} == {HOME_TEAM, AWAY_TEAM}

    missing = client.get("/api/v1/games/9999")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Game not found"


def test_player_search_and_timeline(client, run_full_pipeline):
    run_full_pipeline

    search = client.get("/api/v1/players", params={"search": "Quarter"})
    assert search.status_code == 200
    players = search.json()
    assert len(players) >= 1
    qb = players[0]
    assert "Quarterback" in qb["full_name"]
    assert qb["team_code"] == HOME_TEAM

    timeline = client.get(f"/api/v1/players/{qb['player_id']}/timeline")
    assert timeline.status_code == 200
    payload = timeline.json()
    assert payload["player_id"] == qb["player_id"]
    assert payload["timeline"]
    first_week = payload["timeline"][0]
    assert first_week["season"] == SEASON
    assert first_week["week"] == START_WEEK
    assert first_week["team_code"] == HOME_TEAM
    assert first_week["games_played"] == 1
    assert payload["team_events"][0]["team_code"] == HOME_TEAM

    filtered = client.get(
        f"/api/v1/players/{qb['player_id']}/timeline", params={"season": SEASON}
    )
    assert filtered.status_code == 200
    assert filtered.json()["timeline"] == payload["timeline"]


def test_player_timeline_not_found(client, run_full_pipeline):
    run_full_pipeline
    missing = client.get("/api/v1/players/9999/timeline")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Player not found"


def test_player_search_handles_missing_kickoff(client, run_full_pipeline):
    run_full_pipeline

    with session_scope() as session:
        session.execute(text("UPDATE games SET kickoff_ts = NULL"))

    search = client.get("/api/v1/players", params={"search": "Quarter"})
    assert search.status_code == 200
    payload = search.json()
    assert any(player["full_name"] == "Quarterback One" for player in payload)
