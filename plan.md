# Project Plan (Local Workflow)

## 0. Project Audit

- [x] Review repository contents; identify scratch notebooks, legacy scripts, or assets no longer needed.
- [x] Move anything that should be retained for reference into a `depreciated/` directory (create if missing).
- [x] Update documentation or ignore rules if the new folder should be excluded from tools/tests.


## 1. Data Quality & API Enhancements

- [ ] Filter `/api/seasons` to hide seasons without any finished games (prevents future seasons appearing until stats
exist).
- [ ] Add basic error handling / 404s to the FastAPI app and version the routes (e.g., `/api/v1/...`).
- [ ] Introduce richer read endpoints:
- `/api/weeks?season=YYYY`
- `/api/games/{game_id}`
- `/api/team-stats?season=YYYY`
- [ ] Create pytest fixtures for cached parquet files and add tests covering:
- Season/week/team insertion logic
- Game upsert constraints
- Player/team stat transformations
- API responses (FastAPI `TestClient`)

## 2. Frontend Improvements

- [ ] Display API errors in the UI (status banner with retry).
- [ ] Highlight completed vs scheduled games (e.g., “Final” badge when scores exist).
- [ ] Add filters/search (by week, by team, sort by kickoff time).
- [ ] Provide `.env.local.example` documenting `VITE_API_BASE` for custom ports.

## 3. Automation & Tooling (Local + GitHub Actions)

- [ ] **GitHub Actions – Continuous Integration**
- Trigger: `push` / `pull_request`
- Steps: checkout → setup Python → install deps → run `pytest`
- Optional: cache `pip` downloads
- [ ] **GitHub Actions – Frontend Build**
- Trigger: `push` / PR touching `frontend/`
- Steps: setup Node → `npm ci` → `npm run build` → upload artifact (optional)
- [ ] **Local Scheduled Refresh (optional)**
- PowerShell script that sets `PYTHONPATH` and runs `python -m nfldb.cli update-week`
- Task Scheduler entry (weekly) pointing to the script
- Log output to file for quick review
- [ ] Document how to manually run backfill/update-week, and where cached data lives (`raw/`).

## 4. Local Ops & Monitoring

- [ ] Add simple data sanity checks:
- Script that verifies latest season/week counts and prints summary
- Optional: write CSV snapshot of row counts
- [ ] Maintain a `CHANGELOG.md` / notes file for manual runs (data ranges loaded, issues found).
- [ ] Consider light-weight visualization (e.g., notebook) for inspecting recent loads.

## 5. Future Enhancements (Optional)

- [ ] Extend ETL with rosters/coaches (`import_seasonal_rosters`).
- [ ] Incorporate snap counts and advanced metrics (EPA/success rate).

