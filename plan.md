# Work Plan - Weekly Update Script

## Phase 1 - Analysis (Complete)
- [x] Reviewed `src/nfldb/cli.py` commands to understand shared loaders (`load_seasons_and_weeks`, `load_games`, `load_weekly_stats`).
- [x] Explored supporting ETL modules to confirm available arguments and confirm reuse for a single-week refresh.
- [x] Chose to derive the current season/week from `nfl_data_py.import_schedules`, filtering to regular/postseason games and selecting the latest week with a kickoff on or before the run date.

## Phase 2 - Implementation (Complete)
- [x] Added `scripts/update_current_week.py`, a Python entry point for Task Scheduler that resolves the latest completed week and executes the CLI-equivalent ETL loaders.
- [x] Created unit tests for the week resolver using a stubbed `nfl_data_py.import_schedules` to avoid live network calls.

## Phase 3 - Documentation & Validation (Pending)
- [ ] Document how to schedule the new script (example Task Scheduler command, environment expectations).
- [ ] Run or outline validation steps (pytest focus) once implementation is complete.
