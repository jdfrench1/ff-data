# ff-data Monorepo

This repository now groups three related projects under `apps/`:

- **Backend** (`apps/backend`) – FastAPI services, ETL workflows, and database utilities.
- **Frontend** (`apps/frontend`) – The Vue 3 client delivered via Vite.
- **Analytics** (`apps/analytics`) – Exploratory notebooks and archived research scripts.

Each project keeps its own dependencies, tooling, and documentation. Start with the
README inside the project you are touching—particularly `apps/backend/README.md`
for Python environment setup and ETL orchestration details.

## Quick Start

- Backend: `cd apps/backend` and follow the local setup at the top of
  `README.md`. Compose assets (`docker-compose.yml`, `Dockerfile`) and
  Python scripts now live in this directory.
- Frontend: `cd apps/frontend` then use the existing npm scripts (`npm install`,
  `npm run dev`, etc.).
- Analytics: open notebooks from `apps/analytics/notebooks/` in Jupyter or VS Code.

Global helpers such as `sitecustomize.py`, `pytest.ini`, and `todo.md` stay in the
repository root so CI and task tracking remain centralized.
