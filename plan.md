# Project Plan (Local Workflow)

## 0. Project Audit

- [x] Review repository contents; identify scratch notebooks, legacy scripts, or assets no longer needed.
- [x] Move anything that should be retained for reference into a `depreciated/` directory (create if missing).
- [x] Update documentation or ignore rules if the new folder should be excluded from tools/tests.


## 1. Data Quality & API Enhancements

- [x] Filter `/api/seasons` to hide seasons without any finished games (prevents future seasons appearing until stats exist).
- [x] Add basic error handling / 404s to the FastAPI app and version the routes (e.g., `/api/v1/...`).
- [x] Introduce richer read endpoints:
  - `/api/weeks?season=YYYY`
  - `/api/games/{game_id}`
  - `/api/team-stats?season=YYYY`
- [x] Create pytest fixtures for cached parquet files and add tests covering:
  - Season/week/team insertion logic
  - Game upsert constraints
  - Player/team stat transformations
  - API responses (FastAPI `TestClient`)

## 2. Frontend Improvements

- [x] Display API errors in the UI (status banner with retry).
- [x] Highlight completed vs scheduled games (e.g., "Final" badge when scores exist).
- [x] Add filters/search (by week, by team, sort by kickoff time).
- [x] Provide `.env.local.example` documenting `VITE_API_BASE` for custom ports.
- [x] Update frontend API client to call `/api/v1` endpoints after backend versioning.
- [x] Verify frontend build via `npm run build` after API client updates.

## 3. Automation & Tooling (Local + GitHub Actions)

- [x] Configure pytest pythonpath so src package loads during tests.
- [x] **GitHub Actions - Continuous Integration**
  - Trigger: `push` / `pull_request`
  - Steps: checkout -> setup Python -> install deps -> run `pytest`
  - Optional: cache `pip` downloads
- [x] **GitHub Actions - Frontend Build**
  - Trigger: `push` / PR touching `frontend/`
  - Steps: setup Node -> `npm ci` -> `npm run build` -> upload artifact (optional)
- [x] **Local Scheduled Refresh (optional)**
  - `scripts/update-week.ps1` sets `PYTHONPATH`, prefers `.venv`, writes logs under `logs/`
  - Documented Task Scheduler usage for weekly runs
- [x] Document how to manually run backfill/update-week, and where cached data lives (`raw/`).

## 4. Local Ops & Monitoring

- [x] Add simple data sanity checks:
  - Script that verifies latest season/week counts and prints summary (python -m nfldb.cli sanity-check)
  - Optional: write CSV snapshot of row counts (--output-csv)
- [x] Maintain a `CHANGELOG.md` / notes file for manual runs (data ranges loaded, issues found).
- [x] Consider light-weight visualization (e.g., notebook) for inspecting recent loads.

## 5. Future Enhancements (Optional)

- [ ] Extend ETL with rosters/coaches (`import_seasonal_rosters`).
- [ ] Incorporate snap counts and advanced metrics (EPA/success rate).

## 6. Cleanup Backlog (2025-10-02)

- [x] Remove root `run-weekly.ps1` stub; rely on `scripts/run-weekly.ps1` for scheduling.
- [x] Delete `temp_view.yml`; workflow is superseded by `.github/workflows/load-weekly-data.yml`.
- [x] Stop tracking `nfl_weekly_stats.csv`; treat it as a generated artifact (move under `raw/` or ignore).
- [x] Purge cached state directories (`.pytest_cache`, `src/nfldb/__pycache__`, `tests/__pycache__`) and add ignores to prevent reappearance.
- [x] Verify pytest suite passes after cleanup (2025-10-02).

## 7. Logging Improvements (2025-10-04)

- [x] Introduce logging configuration for weekly loader and uploader scripts (quiet console + optional file handlers).
- [x] Document scheduler usage to leverage new logging options.


- [x] Resolve PowerShell verbose parameter conflict in run-weekly scheduler script.


\r\n## 8. Weekly ETL Integration (2025-10-04)\r\n\r\n- [x] Extend run-weekly.ps1 to run nfldb CLI update-week after upload (CSV week inference, SkipETL flag).\r\n- [x] Update documentation and scheduling notes for ETL integration.\r\n

\n## 9. ETL Data Source Resilience (2025-10-04)\n\n- [x] Prefer nflreadpy in ETL weekly loader with nfl_data_py and release fallbacks to avoid 404s.\n
