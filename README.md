# NFL Database Project

This project defines a Postgres-backed pipeline that loads historical and weekly NFL data using the `nfl_data_py` Python package.

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
3. Initialize the schema and run a backfill once the CLI is implemented:
   ```bash
   python -m nfldb.cli init-db
   python -m nfldb.cli backfill --season-start 1999 --season-end 2023
   ```

## Layout

- `src/nfldb/`: application package
  - `config.py`: environment loading helpers
  - `db.py`: SQLAlchemy engine/session helpers
  - `cli.py`: Typer-based command-line interface
  - `etl/`: modules for loading seasons, weeks, teams, games, and stats
  - `schema.sql`: canonical Postgres DDL
- `migrations/`: Alembic migrations (empty scaffold for now)
- `raw/`: cached datasets (gitignored)
- `tests/`: pytest test suite (WIP)

## Data Pipeline
- `backfill` now ingests seasons, weeks, games, team stats, and player stats via cached `nfl_data_py` schedules/weekly datasets.
- Weekly updates reuse cached files unless `--force-refresh` is provided and map stats into `team_game_stats` and `player_game_stats`.

## API & Frontend
### Run the API server
1. Activate the virtualenv and ensure dependencies are installed (`pip install -r requirements.txt`).
2. Launch the FastAPI service:
   ```bash
   set PYTHONPATH=src  # on PowerShell: $env:PYTHONPATH="src"
   uvicorn nfldb.api.main:app --reload --host 0.0.0.0 --port 8000
   ```
3. The API exposes `/api/seasons` and `/api/games?season=YYYY` and enables CORS for `http://localhost:5173`.
### Run the React client
1. `cd frontend`
2. Install once: `npm install`
3. Start Vite dev server: `npm run dev` (defaults to http://localhost:5173)
4. The client reads `VITE_API_BASE` (defaults to `http://localhost:8000`) from environment files such as `.env.local` if provided.


## Next Steps
- Extend ETL with weekly roster/coaching assignments and player identifiers from seasonal rosters.
- Add data validation tests and fixtures to exercise the ETL without hitting live endpoints.
- Wire automated runs (GitHub Actions or cron) for backfill and weekly refresh workflows.
