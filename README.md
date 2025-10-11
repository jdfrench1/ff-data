# NFL Database Runtime

This repository powers a Postgres-backed NFL analytics stack. Every entry point
invokes a shared bootstrapper so scripts, schedulers, and ad-hoc shells all run
inside the same Python environment with consistent configuration.

The bootstrapper is split across two helpers:

- `src/nfldb/runtime.py::bootstrap()` - core logic that re-executes inside
  `.venv`, prepends `src/` to `sys.path`, and loads `.env` values.
- `scripts/_bootstrap.py::activate()` - thin wrapper used by standalone
  scripts (PowerShell or Python) to trigger the same behavior.

Callers import one of these helpers before loading third-party packages or any
module that depends on environment variables. Once the helper runs, code can
assume:

- The interpreter is `.venv\Scripts\python.exe` (Windows) or `.venv/bin/python`
  (macOS/Linux).
- `src/` is on `sys.path`, so `import nfldb.*` succeeds without `PYTHONPATH`
  tweaks.
- `.env` is parsed when present, exposing `DATABASE_URL` and related settings.
- The guard variable `NFLDB_RUNTIME_ACTIVE` prevents infinite re-exec loops.

---

## Install Once, Bootstrap Everywhere

1. **Create the project virtual environment**
   ```bash
   python -m venv .venv
   ```
2. **Install dependencies**
   ```bash
   .venv\Scripts\activate      # source .venv/bin/activate on macOS/Linux
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```
3. **Configure secrets**
   ```bash
   copy .env.example .env      # use cp on macOS/Linux
   # edit DATABASE_URL and any task-specific overrides
   ```
4. **(Optional) Initialize Postgres**
   ```bash
   python -m nfldb.cli init-db
   python -m nfldb.cli backfill --season-start 1999 --season-end 2023
   ```

After these steps you do *not* need to activate `.venv` before running scripts;
the bootstrapper does it on demand.

---

## Running Project Tools

| Use Case | Command | Bootstrap Notes |
| -------- | ------- | --------------- |
| Inspect CLI commands | `python -m nfldb.cli --help` | Direct module execution inside `.venv`. |
| Full ETL backfill | `py -3 -m nfldb.cli backfill --season-start 2010 --season-end 2024` | Using `py` is safe; bootstrapper re-executes into `.venv`. |
| Weekly database refresh | `py scripts/update_current_week.py --log-file logs/update.log` | `scripts/_bootstrap.py` runs first, so Task Scheduler and cron both work. |
| CSV scrape only | `py ffscraper.py` | `ffscraper.py` calls `bootstrap()` before importing requests/pandas. |
| PowerShell orchestration | `powershell.exe -File scripts/run-weekly.ps1 -Season 2024` | Script shells into Python with `_bootstrap.activate()` and inherits `.env`. |

Prefer the `py` launcher (Windows) or system `python` command when wiring up
schedulers; the bootstrapper will hop into `.venv` automatically. If you run
inside `.venv` already, the helper becomes a no-op.

---

## Automation Patterns

- **Windows Task Scheduler**  
  Point scheduled tasks at `py` or `powershell.exe`. Confirm `.venv` is created
  ahead of time and the scheduled account can read `.env` plus write log files.

- **Docker / Compose**  
  Images install dependencies into `/app/.venv`; the bootstrapper sees that it is
  already in the correct interpreter and simply loads `.env`.

- **CI pipelines**  
  Scripts called via `python`, `py`, or PowerShell behave the same locally and in
  automation because each entry point imports the bootstrapper before doing work.

---

## Testing & Quality Gates

- Run unit tests before pushing:
  ```bash
  pytest -q
  ```
- Tests mock HTTP calls and cached datasets; extend fixtures when selectors or
  schema assumptions change.
- Format touched Python files (especially `ffscraper.py`) with:
  ```bash
  python -m black ffscraper.py
  ```

---

## Dependency Management

- Install new libraries into `.venv`, then refresh the lockfile:
  ```bash
  pip install <package>==<version>
  pip freeze > requirements.txt
  ```
- Capture development-only tooling in `requirements-dev.txt`.

---

## Project Layout

- `ffscraper.py` - Pro-Football-Reference passer scrape that writes
  `nfl_player_stats.csv`, bootstrapped before importing requests/pandas.
- `src/nfldb/` - Application package housing the CLI, ETL modules, and
  `runtime.py`.
- `scripts/` - Automation helpers (`_bootstrap.py`, weekly updater, PowerShell
  orchestrator) that import the bootstrapper first.
- `raw/` - Cached CSV/Parquet sources (gitignored).
- `tests/` - Pytest suites mirroring `src/`.
- `notebooks/` - Exploratory analysis kept outside production paths.
- `docker-compose.yml`, `Dockerfile` - Container orchestration that respects
  the same bootstrap logic.

---

## Troubleshooting

- **Script still uses system Python**  
  Verify `.venv` exists and contains `Scripts/python.exe` (Windows) or
  `bin/python`. The bootstrapper skips re-exec if the interpreter is missing.

- **Environment variables missing**  
  Ensure `python-dotenv` is installed (bundled in `requirements.txt`) and `.env`
  lives at the repository root.

- **Unexpected re-exec loops**  
  The helper sets `NFLDB_RUNTIME_ACTIVE` after a successful hop. If tests mutate
  `os.environ`, preserve that flag or call `bootstrap()` once at module import.

With the bootstrapper in place, every workflow - from the CSV scrape to the
weekly ETL - shares the same runtime contract and avoids the classic "works on
my machine" surprises across local development, CI, and scheduled jobs.
