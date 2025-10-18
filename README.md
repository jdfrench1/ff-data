# ff-data Monorepo

This repository groups three related projects under the `apps/` directory:

- **Backend** (`apps/backend`) - FastAPI services, ETL workflows, and database utilities.
- **Frontend** (`apps/frontend`) - The Vue 3 client delivered via Vite.
- **Analytics** (`apps/analytics`) - Exploratory notebooks and archived research scripts.

Each project keeps its own dependencies, tooling, and documentation. Start with the
README inside the project you are touching (most backend tasks begin in
`apps/backend/README.md` for environment setup and ETL orchestration details).

## Quick Start

- Backend: `cd apps/backend` and follow that directory's README. Compose assets
  (`docker-compose.yml`, `Dockerfile`) and Python automation scripts now live there.
- Frontend: `cd apps/frontend` then use the existing npm scripts (`npm install`,
  `npm run dev`, etc.).
- Analytics: open notebooks from `apps/analytics/notebooks/` in Jupyter or VS Code.

Global helpers such as `sitecustomize.py`, `pytest.ini`, and `todo.md` stay in the
repository root so CI and task tracking remain centralized.

## Roadmap & Status

- Long-form milestones live in `plan.md`, which now covers the monorepo rollout and
  upcoming database automation efforts.
- Day-to-day todos remain in `todo.md`; the checklist mirrors active phases from
  `plan.md` so status stays in sync across documents.
