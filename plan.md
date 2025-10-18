# Monorepo Operations Plan

## Phase 1 - Workspace Realignment (Complete)
- [x] Consolidated backend, frontend, and analytics assets under `apps/`.
- [x] Updated tooling (`sitecustomize.py`, `pytest.ini`, scripts) to respect the new layout.
- [x] Refreshed root documentation (`README.md`, `todo.md`) so contributors land in the right project.

## Phase 2 - Documentation Alignment (Complete)
- [x] Replaced the root README with monorepo guidance and quick-start steps.
- [x] Rewrote this plan to outline the remaining operational workstreams.

## Phase 3 - Backfill & Weekly Pipeline Hardening (Complete)
- [x] Centralized weekly ETL helpers under `nfldb.ops.weekly` and exposed `update-current`.
- [x] Verified pytest coverage for both backfill and weekly loaders after the directory move.
- [x] Documented command pathways for historical backfills and incremental loads.

## Phase 4 - Scheduled Execution Enablement (Complete)
- [x] Added Windows Task Scheduler guidance that targets `python -m nfldb.cli update-current`.
- [x] Confirmed log/output paths (`apps/backend/logs` and `raw/`) in documentation for automated jobs.

## Phase 5 - Steady-State Operations (Complete)
- [x] Produced an operational checklist in `apps/backend/README.md` for backfill and weekly refreshes.
- [x] Documented monitoring hooks (log review, sanity snapshot CSV, Task Scheduler failure actions).

---

_Historic notes for the Vue migration live in `apps/analytics/depreciated/plan-archive-legacy.md`._
