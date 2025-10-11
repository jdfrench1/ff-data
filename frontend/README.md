# Frontend (Vue + TypeScript)

This directory contains the Vue 3 application that surfaces NFL player timelines. The project uses Vite for tooling, Vue single-file components for UI structure, and Vue TSC for type-safe builds.

## Getting Started

```bash
npm install
npm run dev
```

The dev server defaults to http://localhost:5173. Use `npm run build` for production bundles and `npm run preview` to inspect the built output locally.

## Notable Paths

- `src/App.vue` – shell layout hosting player search and the upcoming stats timeline.
- `src/components/` – Vue components (timeline, selectors) land here in future phases.
- `src/assets/main.css` – shared styles applied across the app.

## Linting & Types

Run `npm run lint` to execute ESLint with Vue + TypeScript rules. `npm run build` invokes `vue-tsc -b` to perform type checking alongside the Vite build.
