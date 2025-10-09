# Work Plan - Weekly Update Script

## Phase 1 - Analysis (Complete)
- [x] Reviewed `src/nfldb/cli.py` commands to understand shared loaders (`load_seasons_and_weeks`, `load_games`, `load_weekly_stats`).
- [x] Explored supporting ETL modules to confirm available arguments and confirm reuse for a single-week refresh.
- [x] Chose to derive the current season/week from `nfl_data_py.import_schedules`, filtering to regular/postseason games and selecting the latest week with a kickoff on or before the run date.

## Phase 2 - Implementation (Complete)
- [x] Added `scripts/update_current_week.py`, a Python entry point for Task Scheduler that resolves the latest completed week and executes the CLI-equivalent ETL loaders.
- [x] Created unit tests for the week resolver using a stubbed `nfl_data_py.import_schedules` to avoid live network calls.

## Phase 3 - Documentation & Validation (Complete)
- [x] Documented Task Scheduler usage for `scripts/update_current_week.py` alongside the existing PowerShell pipeline in `README.md`.
- [x] Ran `pytest -q` locally to confirm the suite (including new resolver tests) passes end-to-end.
