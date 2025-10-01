from __future__ import annotations

from .conftest import AWAY_TEAM, HOME_TEAM, SEASON


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
