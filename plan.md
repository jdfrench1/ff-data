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

# Shared Venv Alignment

## Phase 1 - Analysis (Complete)
- [x] Cataloged Python entry points (root `ffscraper.py` plus scripts under `scripts/`) and noted they each embed their own `sys.path`/env handling.
- [x] Verified backend modules (`src/nfldb/*`) expect `DATABASE_URL` at import time and rely on the active interpreter's installed packages.
- [x] Identified need for a shared bootstrap that (a) re-executes with `.venv`'s interpreter when necessary, (b) ensures `src/` is on `sys.path`, and (c) optionally loads `.env` for local runs.

## Phase 2 - Implementation (Pending)
## Phase 2 - Implementation (Complete)
- [x] Added `src/nfldb/runtime.py` plus `scripts/_bootstrap.py` to re-exec into `.venv`, inject `src/`, and load `.env` defaults.
- [x] Updated `ffscraper.py` and all task scripts to call the bootstrapper before importing third-party modules, ensuring consistent dependency versions.

## Phase 3 - Validation & Docs (Complete)
- [x] Smoked scripts via the shared helper (dry-run for weekly updater/loader/uploader, help check for uploader/credentials, and ffscraper run) and reran pytest for full coverage.
- [x] Documented Task Scheduler usage now that the Python entry points bootstrap into the shared virtualenv.

# README Bootstrap Alignment

## Phase 1 - Analysis (Complete)
- [x] Reviewed `README.md`, `src/nfldb/runtime.py`, `scripts/_bootstrap.py`, and related entry points to capture the shared bootstrapper behavior.

## Phase 2 - Rewrite (Complete)
- [x] Redrafted `README.md` to focus on bootstrapper usage, environment expectations, and end-to-end workflows.

## Phase 3 - Proofing (Complete)
- [x] Proofread the updated README, normalized formatting to ASCII-friendly punctuation, and prepared artifacts for final review.

# Weekly Stats Schema Regression

## Phase 1 - Analysis (Complete)
- [x] Reproduced the failure by examining `raw/weekly_2025_2025.parquet` to understand the ingested schema.
- [x] Confirmed the new data source omits `recent_team` and `interceptions`, supplying `team`, `passing_interceptions`, `sacks_suffered`, and `def_sacks` instead.
- [x] Determined we need a normalization layer so the ETL accepts both the legacy `nfl_data_py` columns and the new `nflreadpy`-style names.

## Phase 2 - Implementation (Complete)
- [x] Normalized weekly ETL inputs to tolerate feeds lacking `recent_team`, `interceptions`, and `sacks`, deriving those fields from `team`, `passing_interceptions`, `sacks_suffered`, and `def_sacks`.
- [x] Added an alternate-schema weekly fixture and regression test to exercise the updated pipeline.

## Phase 3 - Validation (Complete)
- [x] Ran `pytest tests/test_etl.py -q` to cover both schema variants of the weekly ETL.
- [x] Executed `scripts/update_current_week.py --dry-run` with logging to confirm successful week resolution without hitting the ETL.

# Remove PFR Scraper

## Phase 1 - Analysis (Complete)
- [x] Confirmed `ffscraper.py`, its container assets, and CSV artefacts are the only production code paths scraping Pro-Football-Reference.
- [x] Cataloged dependent references across `Dockerfile`, `docker-compose.yml`, `README.md`, `AGENTS.md`, and repository outputs (`nfl_player_stats.csv`).
- [x] Identified `beautifulsoup4` and `lxml` in `requirements.txt` as scraper-only dependencies safe to remove with the refactor.
- [x] Verified the maintained ETL stack (`src/nfldb/*`) already relies on `nflreadpy`/`nfl_data_py`, providing the replacement data sources.

## Phase 2 - Implementation (Pending)
- [ ] Remove the Pro-Football-Reference scraper entry point, replace container orchestration, and align runtime/configuration with the surviving ETL tooling.
- [ ] Drop scraper-only requirements and clean up generated CSV outputs tracked in the repo.

## Phase 3 - Validation & Docs (Pending)
- [ ] Run the project test suite and targeted smoke checks against the updated workflow.
- [ ] Refresh README/AGENTS guidance to reflect the new data ingestion path and validate deployment notes.
