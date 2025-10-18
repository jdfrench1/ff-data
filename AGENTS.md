# Repository Guidelines

## Project Structure & Module Organization
All application code now lives under `apps/`:

- `apps/backend/` contains the ETL, FastAPI services, scripts, and container assets.
- `apps/frontend/` hosts the Vue 3 client scaffolded with Vite.
- `apps/analytics/` stores notebooks and research helpers; keep these artifacts outside production code.

Each project maintains its own README plus local tooling configuration. Mirror modules with tests under `apps/backend/tests/` and keep shared developer docs (like this file) at the repository root.

## Build, Test, and Development Commands
Backend tasks should be executed from `apps/backend/`:

- Create a virtual environment with `python -m venv .venv`, activate it, then install dependencies via `pip install -r requirements.txt`.
- Run ETL/CLI workflows with `python -m nfldb.cli ...` or the scripts in `scripts/`.
- Use `docker compose up --build scraper` (run from `apps/backend/`) to exercise the container pipeline; keep Postgres environment variables aligned with your target instance.
- Regenerate `requirements.txt` via `pip freeze > requirements.txt` whenever dependencies change.

Frontend work happens in `apps/frontend/` (`npm install`, `npm run dev`), while notebooks stay in `apps/analytics/notebooks/`.

## Coding Style & Naming Conventions
Follow PEP 8 across `apps/backend/src/`: four-space indentation, 88-character lines, and `snake_case` for functions and variables. Guard side effects with `if __name__ == "__main__":` and expose reusable logic through helper functions. Keep module names descriptive (`team_stats.py`) and constants uppercase at file scope. Run `python -m black` on touched backend modules before pushing; document extra tooling in `requirements-dev.txt`.

## Testing Guidelines
Adopt `pytest` and store specs under `apps/backend/tests/`, mirroring module names. Stub HTTP calls with fixtures so suites do not hit external services. Assert DataFrame shapes, column names, and CSV output pathways to catch selector drift. Execute `pytest -q` from `apps/backend/` before opening a pull request and expand fixtures when parsing logic changes.

## Commit & Pull Request Guidelines
Write commits in the imperative mood (`Add CSV schema validation`) and keep each focused on one concern. Reference related issues in the body when applicable and call out data source changes explicitly. Pull requests need a concise summary, test evidence (`pytest -q` output or compose logs), and screenshots or CSV diffs for schema-impacting updates. Flag Docker or compose changes so reviewers can plan rollout adjustments.

## Working with plan.md
When there are planned phases to do in the plan.md ask if I want a new branch created.
If I do:
    After each phase of the plan, stop and ask for further instrunction.
    Before each phase of the plan, create a repo branch.
    After each phase of the plan, commit the changes, and merge the branch.
After each phase of the plan, update the plan.md file.
