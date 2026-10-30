# JEV Resume Analyzer frontend

Local-only React + Vite + TypeScript demo. No backend, provider key, sign-in or saved history in this package. Do not put CVs or credentials in the source tree.

## Run

Requires Node 20.19+ or 22.12+ (verified on Node 24.18.0).

```sh
npm ci
npm run dev
```

Open http://127.0.0.1:5273. The `/api` proxy expects the backend on http://127.0.0.1:8017. Without it the UI displays a real error, never a fixture report. Ports avoid unrelated services on this host. Do not change them without checking ownership and availability.

`VITE_API_BASE_URL` overrides the API origin for a build. Empty means same origin, which is the dev proxy. A trailing slash is stripped. The deploy workflow sets it to the API preview URL for preview builds and to the production API for production builds. It is inlined at build time, so a change needs a new build.

## Verify

```sh
npm run build
npm run typecheck
npm test
npm audit
```

For browser tests start the dev server first. On this host reuse the existing Chromium:

```sh
CHROMIUM_PATH=/home/admin/.cache/ms-playwright/chromium_headless_shell-1208/chrome-headless-shell-linux64/chrome-headless-shell npx playwright test
```

The first browser test requires backend absence; the other two mock API responses at the browser boundary and label screenshots SYNTHETIC API FIXTURE TEST. Tests are not a live provider demonstration. Screenshots go to test-results/.

Contract, error semantics, privacy and integration limitations: `../docs/frontend-contract.md`.

Verified: build/typecheck passed; 30 Vitest tests; 3 Playwright tests, including 375px and 1280px axe WCAG A/AA checks with zero violations and no horizontal overflow; npm audit zero vulnerabilities. Browser fixture runs had no uncaught JS exceptions. Production bundle: JS 216.08 kB (64.44 kB gzip), CSS 25.87 kB (12.57 kB gzip), plus self-hosted fonts. Image-based screenshot review was unavailable due to a vision-tool authentication error. Independent reviewer must inspect visual output.

No deployment, PR, Git initialisation, backend changes or real provider calls performed.
