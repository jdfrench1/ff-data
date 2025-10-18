#!/usr/bin/env python
"""Refresh the current NFL week in Postgres using nfldb ETL helpers."""

from __future__ import annotations

try:
    from ._bootstrap import activate  # type: ignore
except ImportError:  # pragma: no cover - fallback for direct execution
    from _bootstrap import activate  # type: ignore

activate()

import argparse
import logging
from datetime import datetime
from typing import Optional, Sequence

from nfldb.ops.weekly import WeekTarget, parse_as_of, refresh_week, resolve_target_week

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s - %(message)s"
LOGGER = logging.getLogger("update-current-week")

def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve the most recent NFL week and run the nfldb ETL loaders for it."
        )
    )
    parser.add_argument("--season", type=int, help="Override the detected season.")
    parser.add_argument("--week", type=int, help="Override the detected week.")
    parser.add_argument(
        "--as-of",
        type=str,
        help="ISO timestamp for week resolution (default: now, UTC).",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Redownload source data even if cached parquet files exist.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Console log level.",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        help="Optional path to append log entries.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve the target week but skip database updates.",
    )
    return parser.parse_args(argv)


def configure_logging(level: str, log_file: Optional[str]) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, level))

    formatter = logging.Formatter(LOG_FORMAT)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)


def _parse_as_of(value: Optional[str]) -> Optional[datetime]:
    try:
        return parse_as_of(value)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    configure_logging(args.log_level, args.log_file)

    as_of = _parse_as_of(args.as_of)

    if args.season and args.week:
        target = WeekTarget(season=args.season, week=args.week)
        LOGGER.info(
            "Using provided season=%s and week=%s overrides.", args.season, args.week
        )
    else:
        target = resolve_target_week(as_of=as_of)
        if args.season and args.season != target.season:
            LOGGER.warning(
                "Resolved season %s differs from --season override %s. Using override.",
                target.season,
                args.season,
            )
            target = WeekTarget(season=args.season, week=target.week)
        if args.week and args.week != target.week:
            LOGGER.warning(
                "Resolved week %s differs from --week override %s. Using override.",
                target.week,
                args.week,
            )
            target = WeekTarget(season=target.season, week=args.week)
        LOGGER.info(
            "Resolved latest completed week: season=%s week=%s",
            target.season,
            target.week,
        )

    if args.dry_run:
        LOGGER.info("Dry-run enabled; skipping ETL execution.")
        return

    refresh_week(target, force_refresh=args.force_refresh)


if __name__ == "__main__":  # pragma: no cover
    main()
