from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import csv
from sqlalchemy import text
from sqlalchemy.orm import Session

_TABLES_FOR_COUNTS: Tuple[str, ...] = (
    "seasons",
    "weeks",
    "teams",
    "games",
    "team_game_stats",
    "player_game_stats",
)


@dataclass(frozen=True)
class WeekSummary:
    """Aggregated status for an individual week of games."""

    week_number: int
    total_games: int
    completed_games: int

    @property
    def is_complete(self) -> bool:
        """Return True when all tracked games have final scores."""
        return self.total_games > 0 and self.total_games == self.completed_games


@dataclass(frozen=True)
class DataHealthSummary:
    """High-level overview of the latest loaded season."""

    latest_season: Optional[int]
    week_summaries: Sequence[WeekSummary]
    total_games: int
    total_completed_games: int

    @property
    def latest_completed_week(self) -> Optional[int]:
        """Return the most recent week that has at least one finalized game."""
        for summary in reversed(self.week_summaries):
            if summary.completed_games > 0:
                return summary.week_number
        return None

    @property
    def issues(self) -> List[str]:
        """Return a list of warnings discovered during the aggregate check."""
        issues: List[str] = []
        if self.latest_season is None:
            issues.append("No seasons present in database.")
            return issues
        if self.total_games == 0:
            issues.append(f"No games recorded for season {self.latest_season}.")
        else:
            incomplete_weeks = [
                summary.week_number
                for summary in self.week_summaries
                if summary.total_games > 0 and not summary.is_complete
            ]
            if incomplete_weeks:
                joined = ", ".join(str(week) for week in incomplete_weeks)
                issues.append(f"Weeks with unfinalized games: {joined}.")
        return issues


def build_data_health_summary(session: Session) -> DataHealthSummary:
    """Build a season summary highlighting potential data gaps."""
    latest_season = session.execute(
        text("SELECT year FROM seasons ORDER BY year DESC LIMIT 1")
    ).scalar()
    if latest_season is None:
        return DataHealthSummary(None, (), 0, 0)

    rows = session.execute(
        text(
            """
            SELECT
                w.week_number AS week_number,
                COUNT(g.game_id) AS total_games,
                COALESCE(
                    SUM(
                        CASE
                            WHEN g.home_points IS NOT NULL AND g.away_points IS NOT NULL
                                THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS completed_games
            FROM weeks AS w
            JOIN seasons AS s ON s.season_id = w.season_id
            LEFT JOIN games AS g ON g.week_id = w.week_id
            WHERE s.year = :season
            GROUP BY w.week_number
            ORDER BY w.week_number
            """
        ),
        {"season": latest_season},
    ).all()

    week_summaries = tuple(
        WeekSummary(
            week_number=row.week_number,
            total_games=row.total_games,
            completed_games=row.completed_games,
        )
        for row in rows
    )
    total_games = sum(summary.total_games for summary in week_summaries)
    total_completed_games = sum(summary.completed_games for summary in week_summaries)

    return DataHealthSummary(
        latest_season=latest_season,
        week_summaries=week_summaries,
        total_games=total_games,
        total_completed_games=total_completed_games,
    )


def collect_row_counts(
    session: Session, tables: Optional[Sequence[str]] = None
) -> List[Tuple[str, int]]:
    """Return row counts for critical tables."""
    target_tables = tables or _TABLES_FOR_COUNTS
    counts: List[Tuple[str, int]] = []
    for table in target_tables:
        count = session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        counts.append((table, int(count)))
    return counts


def write_counts_snapshot(
    destination: Path,
    counts: Iterable[Tuple[str, int]],
    generated_at: Optional[datetime] = None,
) -> Path:
    """Persist a CSV snapshot of row counts for later auditing."""
    timestamp = (generated_at or datetime.utcnow()).isoformat(timespec="seconds")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=("table_name", "row_count", "generated_at")
        )
        writer.writeheader()
        for table_name, row_count in counts:
            writer.writerow(
                {
                    "table_name": table_name,
                    "row_count": row_count,
                    "generated_at": timestamp,
                }
            )
    return destination
