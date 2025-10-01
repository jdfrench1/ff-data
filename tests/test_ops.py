from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from nfldb.db import session_scope
from nfldb.ops.sanity import (
    build_data_health_summary,
    collect_row_counts,
    write_counts_snapshot,
)


def test_build_data_health_summary_handles_empty_database(database) -> None:
    with session_scope() as session:
        summary = build_data_health_summary(session)
    assert summary.latest_season is None
    assert summary.total_games == 0
    assert summary.total_completed_games == 0
    assert summary.latest_completed_week is None
    assert summary.issues == ["No seasons present in database."]


def test_build_data_health_summary_reports_latest_week(
    database, run_full_pipeline
) -> None:
    with session_scope() as session:
        summary = build_data_health_summary(session)
        counts = collect_row_counts(session)

    assert summary.latest_season == 2023
    assert summary.total_games == 1
    assert summary.total_completed_games == 1
    assert summary.latest_completed_week == 1
    assert summary.issues == []
    counts_dict = dict(counts)
    assert counts_dict["weeks"] == 1
    assert counts_dict["games"] == 1


def test_write_counts_snapshot_persists_csv(tmp_path: Path) -> None:
    destination = tmp_path / "snapshot.csv"
    rows = [("games", 1), ("team_game_stats", 2)]
    write_counts_snapshot(
        destination, rows, generated_at=datetime(2024, 1, 1, 12, 0, 0)
    )

    output = pd.read_csv(destination)
    assert list(output["table_name"]) == ["games", "team_game_stats"]
    assert list(output["row_count"]) == [1, 2]
    assert all(output["generated_at"] == "2024-01-01T12:00:00")
