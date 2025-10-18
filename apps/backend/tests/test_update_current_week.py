from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import pytest

import nfldb.ops.weekly as weekly


def _stub_import_schedules(monkeypatch, frame: pd.DataFrame) -> None:
    def _fake_import_schedule(years):
        return frame

    monkeypatch.setattr(weekly.nfl, "import_schedules", _fake_import_schedule)


def test_resolve_target_week_regular_season(monkeypatch):
    schedule = pd.DataFrame(
        [
            {"season": 2023, "week": 18, "gameday": "2024-01-07", "gametime": "13:00"},
            {"season": 2024, "week": 4, "gameday": "2024-09-29", "gametime": "13:00"},
            {"season": 2024, "week": 4, "gameday": "2024-09-30", "gametime": "20:15"},
            {"season": 2024, "week": 5, "gameday": "2024-10-06", "gametime": "13:00"},
        ]
    )
    _stub_import_schedules(monkeypatch, schedule)

    target = weekly.resolve_target_week(
        as_of=datetime(2024, 10, 8, 12, tzinfo=timezone.utc)
    )

    assert target.season == 2024
    assert target.week == 5


def test_resolve_target_week_postseason(monkeypatch):
    schedule = pd.DataFrame(
        [
            {"season": 2024, "week": 18, "gameday": "2025-01-05", "gametime": "16:25"},
            {"season": 2024, "week": "Wildcard", "gameday": "2025-01-11", "gametime": "20:15"},
            {"season": 2024, "week": "Divisional", "gameday": "2025-01-19", "gametime": "15:00"},
            {"season": 2024, "week": "Conference Championships", "gameday": "2025-01-26", "gametime": "18:30"},
            {"season": 2024, "week": "Super Bowl", "gameday": "2025-02-09", "gametime": "18:30"},
        ]
    )
    _stub_import_schedules(monkeypatch, schedule)

    target = weekly.resolve_target_week(
        as_of=datetime(2025, 2, 10, tzinfo=timezone.utc)
    )

    assert target.season == 2024
    assert target.week == 22


def test_resolve_target_week_no_games_yet(monkeypatch):
    schedule = pd.DataFrame(
        [
            {"season": 2024, "week": 1, "gameday": "2024-09-08", "gametime": "13:00"},
        ]
    )
    _stub_import_schedules(monkeypatch, schedule)

    with pytest.raises(RuntimeError):
        weekly.resolve_target_week(as_of=datetime(2024, 8, 20, tzinfo=timezone.utc))
