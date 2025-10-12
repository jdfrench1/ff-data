# Frontend Vue Migration Plan

## Phase 1 - Planning & Tooling (Complete)
- [x] Confirmed API requirements for player search, weekly stats timelines, and roster transitions to feed the Vue UI.
- [x] Selected Vue 3 with Vite, ESLint (flat config), and Vue TSC as the foundation for the new frontend stack.

## Phase 2 - Vue Scaffold (Complete)
- [x] Replaced the React app with a Vue 3 + TypeScript project scaffolded via Vite and refreshed npm scripts.
- [x] Configured linting, formatting, and build tooling with ESLint, vue-tsc, and bundler-aware TypeScript settings.
- [x] Verified the production build pipeline via `npm run build` to ensure parity with previous automation hooks.

## Phase 3 - Player Timeline Feature (Complete)
- [x] Implemented FastAPI endpoints for player search and weekly timelines with derived team-change events.
- [x] Built the Vue player selection experience, including sparkline trends, team change callouts, and weekly stat tables.
- [x] Added pytest coverage for the new endpoints plus lint/build automation for the Vue app.

## Phase 4 - Player Search Diagnostics (Complete)
- [x] Reviewed the `/api/v1/players` query and identified the Postgres failure caused by `COALESCE(g.kickoff_ts, '')`, which mixes timestamp and text types within the `ROW_NUMBER` sort.
- [x] Confirmed the failure mode explains missing search results in the frontend due to the backend raising an error when hitting Postgres.

## Phase 5 - Player Search Fix (Complete)
- [x] Replaced the unsafe `COALESCE` usage with a cross-database safe ordering strategy for `ROW_NUMBER` so latest-team selection works on Postgres.
- [x] Added regression coverage ensuring player searches succeed against fixture data without raising errors.

## Phase 6 - Validation & Wrap-up (Complete)
- [x] Ran `pytest -q` to verify regression coverage; all suites pass.
- [x] Prepared to summarize backend fix, merge validation branch, and note deployment follow-ups.

## Phase 7 - API Redeploy (Complete)
- [x] Relaunched the FastAPI service via `uvicorn`, verified the `/health` endpoint on port 8100, and confirmed new code is active.

## Phase 8 - Frontend Smoke Test (Complete)
- [x] Launched the API against a freshly seeded `smoke.db` SQLite snapshot and issued `fetch` calls mimicking the Vue client; verified player search and timeline payloads return successfully for \"Patrick\" queries.
