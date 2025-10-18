# Frontend (Vue + TypeScript)

This directory contains the Vue 3 application that surfaces NFL player timelines with live team-change highlights. The project uses Vite for tooling, Vue single-file components for UI structure, and Vue TSC for type-safe builds.

## Getting Started

```bash
npm install
npm run dev
```

The dev server defaults to http://localhost:5173. Use `npm run build` for production bundles and `npm run preview` to inspect the built output locally.

## Notable Paths

- `src/App.vue` - orchestrates player search, selection, and the timeline panel.
- `src/components/PlayerSearchPanel.vue` - debounced name search with result highlighting.
- `src/components/PlayerTimeline.vue` - renders fantasy trendlines, team changes, and weekly stats tables.
- `src/api.ts` - lightweight REST client for the FastAPI backend.
- `src/assets/main.css` - shared styles applied across the app.

## Linting & Types

Run `npm run lint` to execute ESLint with Vue + TypeScript rules. `npm run build` invokes `vue-tsc --noEmit -p tsconfig.app.json` to perform type checking alongside the Vite build.
