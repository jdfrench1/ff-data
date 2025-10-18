# Backend Services & ETL

This directory houses the Python backend for the `ff-data` monorepo. It contains
the FastAPI application, database/ETL utilities, and supporting automation
scripts. All commands below assume you are inside `apps/backend/`.

## Runtime Bootstrapper

- `src/nfldb/runtime.py::bootstrap()` re-executes the process inside `.venv`,
  prepends `src/` to `sys.path`, and loads `.env` variables.
- `scripts/_bootstrap.py::activate()` is a thin wrapper so PowerShell or other
  entry-point scripts can trigger the same behavior.
- `nfldb/__init__.py` and `sitecustomize.py` ensure `python -m nfldb.cli` works
  even when the package is not installed into site-packages.

Import one of these helpers before touching third-party packages or code that
expects environment variables.

## Environment Setup

From `apps/backend/`:

1. `python -m venv .venv`
2. Activate the environment:
   - PowerShell: `.venv\Scripts\Activate.ps1`
   - Bash/zsh: `source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. (Optional) `pip install -r requirements-dev.txt`
5. `copy .env.example .env` (use `cp` on macOS/Linux) and update connection
   strings or API keys.

Once `.venv` exists, the bootstrapper will re-use it automatically, so you do
not need to activate the environment for scheduled jobs or ad-hoc scripts.

## Running Project Tools

| Use Case | Command (run from `apps/backend/`) | Notes |
| -------- | ---------------------------------- | ----- |
| Inspect CLI commands | `python -m nfldb.cli --help` | Runs inside `.venv` via the bootstrapper. |
| Full ETL backfill | `py -3 -m nfldb.cli backfill --season-start 2010 --season-end 2024` | Safe to invoke with the Windows `py` launcher. |
| Auto-detect latest week | `py -3 -m nfldb.cli update-current --log-level INFO --log-file logs/update.log` | Resolves the most recent completed week and runs the ETL (use `--dry-run` to inspect without loading). |
| Manual weekly refresh | `py scripts/update_current_week.py --log-file logs/update.log` | Script form of the same workflow; accepts `--season/--week` overrides. |
| Load a specific week | `py scripts/load_weekly_data.py --season 2024 --week 1` | Writes intermediary files into `raw/` (gitignored). |
| Docker pipeline | `docker compose up --build scraper` | Uses `Dockerfile` and `docker-compose.yml` in this directory. |

## Automation Patterns

- **Windows Task Scheduler**  
  1. Create an action that runs `py` with arguments  
     `-3 -m nfldb.cli update-current --log-level INFO --log-file logs\\update.log`.  
  2. Set *Start in* to the full path of `apps/backend`.  
  3. Ensure the service account has read access to `.env`, write access to `logs/`,
     and permissions on any network locations referenced by `DATABASE_URL`.  
  4. Use the *Triggers* tab to schedule the weekly run (e.g., every Tuesday at 06:00).
- **Docker / Compose** - Images install dependencies into `/app/.venv`. The
- **Docker / Compose** - Images install dependencies into `/app/.venv`. The
  bootstrapper detects that interpreter and only loads `.env`.
- **CI pipelines** - Callers that execute `python`, `py`, or PowerShell behave
  identically because every entry point imports the bootstrapper first.

## Testing & Quality Gates

- Run unit tests before pushing: `pytest -q`
- Tests mock external services where needed; extend fixtures when parsing logic
  changes.
- Format touched modules with `python -m black src/nfldb`.

## Operational Checklists

- **Full backfill**
  1. Optional sanity check: `python -m nfldb.cli sanity-check`.
  2. Run `py -3 -m nfldb.cli backfill --season-start <first> --season-end <last>`.
  3. Inspect logs and rerun the sanity check to confirm row counts.
- **Weekly update**
  1. Run `py -3 -m nfldb.cli update-current --log-level INFO --log-file logs/update.log`.
  2. Review the log file for completion messages.
  3. (Optional) Spot-check with `python -m nfldb.cli sanity-check`.

## Monitoring & Alerting

- **Log inspection** – Weekly runs append to `logs/update.log`. Configure Task Scheduler's
  *History* view or your preferred log shipper to alert on `ERROR` entries.
- **Sanity snapshot** – Schedule `python -m nfldb.cli sanity-check --output-csv logs\\row_counts.csv`
  after the weekly refresh. Compare the latest CSV against previous snapshots to detect regressions.
- **Exit codes** – `nfldb.cli update-current` returns a non-zero exit code on failure. Use Task
  Scheduler's *Actions → On failure* trigger to send notifications or execute remediation scripts.
- **Database health** – Review the CSV produced by `write_counts_snapshot` (see `nfldb.ops.sanity`)
  alongside monitoring dashboards for your Postgres instance to ensure row counts grow as expected.

## Dependency Management

- Install new libraries inside `.venv`, then capture the lockfile with:
  ```bash
  pip freeze > requirements.txt
  ```
- Record development-only tooling in `requirements-dev.txt`.

## Project Layout

- `src/nfldb/` - Application package with API, ETL, and runtime helpers.
- `scripts/` - Automation helpers that import `_bootstrap.activate()` first.
- `tests/` - Pytest suites mirroring modules in `src/nfldb/`.
- `migrations/` - Database schema change scripts.
- `raw/` - Cached CSV/Parquet sources (ignored by git).
- `logs/` - Scheduler and script output (ignored by git).
- `nfldb/` - Import shim so `python -m nfldb.cli` resolves to `src/nfldb`.
- `sitecustomize.py` - Adds this directory to `sys.path` when running from the
  repository root.

## Troubleshooting

- **Script still uses system Python** - Confirm `.venv` exists and contains
  `Scripts/python.exe` (Windows) or `bin/python`. If missing, create the
  environment again and re-run the script.
- **Environment variables missing** - Ensure `python-dotenv` (bundled in
  `requirements.txt`) is installed and `.env` lives in this directory.
- **Unexpected re-exec loops** - The bootstrapper sets `NFLDB_RUNTIME_ACTIVE`
  after a successful hop into `.venv`. Preserve that flag if tests mutate
  `os.environ`.
