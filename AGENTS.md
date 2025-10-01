# Repository Guidelines

## Project Structure & Module Organization
The root holds the web scraping script `ffscraper.py`, which fetches Pro-Football-Reference passing data and writes `nfl_player_stats.csv`. `ffscraper.ipynb` is a scratch notebook for exploratory data checks; keep notebooks out of production paths. Container assets sit alongside the code: `Dockerfile` builds the scraper image around `ffscraper.py`, while `docker-compose.yml` orchestrates the scraper and a Postgres service. Grow the codebase by introducing a `src/` package and mirror modules with tests in `tests/`.

## Build, Test, and Development Commands
Create a virtual environment with `python -m venv .venv`, activate it, then install dependencies via `pip install -r requirements.txt`. Run the scraper locally with `python ffscraper.py` and confirm `nfl_player_stats.csv` updates. Use `docker compose up --build scraper` to exercise the container pipeline; keep the compose environment variables synchronized with your Postgres target. Regenerate `requirements.txt` with `pip freeze > requirements.txt` whenever dependencies shift.

## Coding Style & Naming Conventions
Follow PEP 8: four-space indentation, 88-character lines, and `snake_case` for functions and variables. Guard side effects with `if __name__ == "__main__":` and expose reusable logic through helper functions. Keep module names descriptive (`team_stats.py`) and constants uppercase at file scope. Run `python -m black ffscraper.py` before pushing; document any additional tooling in `requirements-dev.txt`.

## Testing Guidelines
Adopt `pytest` and store specs in `tests/`, mirroring module names (`tests/test_ffscraper.py`). Stub HTTP calls with fixtures so suites do not hit Pro-Football-Reference. Assert DataFrame shapes, column names, and CSV output pathways to catch selector drift. Execute `pytest -q` before opening a pull request and expand fixtures when changing HTML parsing.

## Commit & Pull Request Guidelines
Write commits in the imperative mood (`Add CSV schema validation`) and keep each focused on one concern. Reference related issues in the body when applicable and call out data source changes explicitly. Pull requests need a concise summary, test evidence (`pytest -q` output or compose logs), and screenshots or CSV diffs for schema-impacting updates. Flag Docker or compose changes so reviewers can plan rollout adjustments.

## Working with plan.md
After each phase of the plan, stop and ask for further instrunction.
Before each phase of the plan, create a repo branch.
After each phase of the plan, commit the changes, and merge the branch.
After each phase of the plan, update the plan.md file.