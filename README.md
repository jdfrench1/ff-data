# NFL Database Project

This project defines a Postgres-backed pipeline that loads historical and weekly NFL
data using the `nfl_data_py` Python package.

## Quickstart

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
2. Configure your database connection in `.env`:
   ```bash
   cp .env.example .env
   # update DATABASE_URL for your Postgres instance
   ```
3. Initialize the schema and seed historical data:
   ```bash
   python -m nfldb.cli init-db
   python -m nfldb.cli backfill --season-start 1999 --season-end 2023
   ```
4. Run the automated tests before pushing changes:
   ```bash
   pytest -q
   ```

## Layout

- `src/nfldb/`: application package
  - `config.py`: environment loading helpers
  - `db.py`: SQLAlchemy engine/session helpers
  - `cli.py`: Typer-based command-line interface
  - `etl/`: modules for loading seasons, weeks, teams, games, and stats
  - `schema.sql`: canonical Postgres DDL
- `scripts/`: PowerShell helpers for scheduled or ad-hoc refreshes
- `migrations/`: Alembic migrations (empty scaffold for now)
- `raw/`: cached datasets (gitignored)
- `depreciated/`: archived notebooks and exploratory scripts kept for reference
- `tests/`: pytest test suite (WIP)

## Data Pipeline

- `backfill` ingests seasons, weeks, games, team stats, and player stats via cached
  `nfl_data_py` schedules/weekly datasets stored under `raw/`.
- Weekly updates reuse cached files unless `--force-refresh` is provided and map
  stats into `team_game_stats` and `player_game_stats`.

## Manual Data Refresh

- Full backfill (reruns all seasons and weeks):
  ```bash
  python -m nfldb.cli backfill --season-start 2010 --season-end 2024 \
      --force-refresh  # optional: refetches raw data under raw/
  ```
- Single-week update (quick refresh during the season):
  ```bash
  python -m nfldb.cli update-week --season 2024 --week 6
  ```
  Add `--force-refresh` when upstream schedules changed or cached CSVs are stale.
- Cached source files live under `raw/` (ignored by git). Delete a season/week cache
  or pass `--force-refresh` to rebuild a specific slice.

### Local Ops Checks
- Run `python -m nfldb.cli sanity-check` after backfills or weekly refreshes to inspect the latest season/week counts.
- Add `--output-csv logs/snapshots/latest_counts.csv` (or another path) to persist row-count snapshots for auditing.
- Capture manual refresh context in `CHANGELOG.md` so future runs know what was loaded and why.
- For visual confirmation, open `notebooks/recent_load_health.ipynb` with `DATABASE_URL` set to your target instance to chart completed games by week.

### Windows Scheduled Refresh

1. Use `scripts/run-weekly.ps1` for scheduled loads; it invokes the weekly CSV loader and Postgres upload helpers from the repo root.
2. Create a Task Scheduler job (Action -> Start a program) with:
   ```text
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\path\to\repo\scripts\run-weekly.ps1" \
       -Season (Get-Date).Year -LogFile "C:\path\to\logs\weekly_$(Get-Date -Format yyyyMMdd_HHmmss).log"
   ```
3. Omit `-Week` to load every published week for the season, or pass `-Week` to upload a single week. Add `-SkipPostgres` if you only need the CSV.
4. The script creates the log directory, prefers `.venv\Scripts\python.exe`, forwards `--quiet`/`--log-file` to the Python scripts, and trims console noise to warnings/errors.
5. Confirm the task account can reach the Postgres target defined in `.env`, has write access to the log path, and adjust chunk size via `--chunk-size` if database parameter limits are hit.

## API & Frontend

### Run the API server
1. Activate the virtualenv and ensure dependencies are installed (`pip install -r
   requirements.txt`).
2. Launch the FastAPI service:
   ```bash
   set PYTHONPATH=src  # on PowerShell: $env:PYTHONPATH="src"
   uvicorn nfldb.api.main:app --reload --host 0.0.0.0 --port 8000
   ```
3. The API is versioned under `/api/v1` and exposes endpoints for seasons, weeks,
   games, game detail, and team stats while enabling CORS for
   `http://localhost:5173`.

### Run the React client
1. `cd frontend`
2. Install once: `npm install`
3. Start Vite dev server: `npm run dev` (defaults to http://localhost:5173)
4. The client reads `VITE_API_BASE` (defaults to `http://localhost:8000`) from
   environment files such as `.env.local` if provided.

## Next Steps

- Extend ETL with weekly roster/coaching assignments and player identifiers from
  seasonal rosters.
- Add data validation tests and fixtures to exercise the ETL without hitting live
  endpoints.
- Monitor the new GitHub Actions workflows and expand coverage with coverage
  uploads or integration smoke tests as the project grows.