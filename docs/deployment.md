# Deployment on Vercel

Two Vercel projects deploy from this one repository. The API is a Python
function. The web app is a static Vite build. They promote and roll back
independently, and the deploy workflow is the only path to production.

## Architecture

```
                      GitHub main
                          |
              .github/workflows/deploy.yml
                  /                    \
      backend/  (root dir)        frontend/  (root dir)
      Vercel project "jev-api"    Vercel project "jev-web"
      app.main:app                dist/ static assets
      /api/v1/*                   / and /assets/*
              ^                          |
              |   fetch, cross origin    |
              +--------------------------+
                 CORS: ALLOWED_ORIGINS

  Preview URL (immutable)  --vercel promote-->  production domain
        smoke test                                   smoke test
```

Why two projects:

- The Python bundle and the static asset cache have nothing in common.
- The web preview can point at the API preview, so a pull request tests the
  real pair before either is promoted.
- A failed API deploy never takes the web down, and a rollback is per project.

The repository has no database. All state is per tab in `sessionStorage`, so
any instance can serve any request. There is no session affinity requirement.

## Files that define the deployment

| File | Purpose |
| --- | --- |
| `backend/pyproject.toml` | `[tool.vercel] entrypoint = "app.main:app"` |
| `backend/.python-version` | `3.12` |
| `backend/vercel.json` | function `maxDuration` 60, `memory` 1024, `excludeFiles` |
| `backend/.vercelignore` | keeps tests, caches, virtualenv and logs out of the bundle |
| `frontend/vercel.json` | Vite build, `dist` output, SPA rewrite, asset cache headers |
| `.github/workflows/ci.yml` | tests and lint on every push and pull request |
| `.github/workflows/deploy.yml` | preview, smoke, promote, production smoke |
| `.github/workflows/rollback.yml` | manual rollback for api, web or both |

## First-time setup

Nothing here is automated yet. Run it once, from the repository root, with the
Vercel CLI logged in to the Hobby account.

1. Create the two projects. Use the dashboard or the CLI, and do not connect
   either project to GitHub. The workflow deploys with the CLI, so a Git
   connection would create a second, untested production path.

   ```bash
   cd backend  && vercel link --project jev-api
   cd ../frontend && vercel link --project jev-web
   ```

   Set the root directory to `backend` and `frontend` respectively. The web
   project uses the Vite preset. The API project needs no build command;
   `[tool.vercel]` in `pyproject.toml` supplies the entrypoint.

2. Record the two project ids and the team id. They become GitHub secrets.

   ```bash
   cat backend/.vercel/project.json frontend/.vercel/project.json
   # orgId, projectId
   ```

3. Set environment variables in the Vercel dashboard, per project. See the
   table below. `TYPESAFE_API_KEY` is a secret: paste it in the dashboard,
   never in a file in this repository.

4. Add the GitHub repository secrets. Settings -> Secrets and variables ->
   Actions.

   | Secret | Value |
   | --- | --- |
   | `VERCEL_TOKEN` | account token from Vercel account settings |
   | `VERCEL_ORG_ID` | team id from `.vercel/project.json` |
   | `VERCEL_PROJECT_ID_API` | project id of `jev-api` |
   | `VERCEL_PROJECT_ID_WEB` | project id of `jev-web` |

   No other secret is needed. The provider key stays in Vercel.

5. Optional repository variables. The production smoke test resolves each
   project's production alias through the Vercel API. Set these when you use
   custom domains, or when alias discovery picks the wrong host.

   | Variable | Example |
   | --- | --- |
   | `PROD_API_URL` | `https://api.example.com` |
   | `PROD_WEB_URL` | `https://example.com` |

6. Domains. Attach the web domain to `jev-web` and an API subdomain to
   `jev-api`. Then set `ALLOWED_ORIGINS` on the API to the exact web origins,
   scheme included and no trailing slash:

   ```
   ALLOWED_ORIGINS=https://example.com,https://www.example.com
   ```

   The web build needs `VITE_API_BASE_URL=https://api.example.com`. It is read
   at build time, so changing it requires a new deployment.

7. Disable automatic production deployments on both projects if a Git
   connection exists. Settings -> Git. The workflow is the source of truth.

## Environment variables

| Variable | Project | Environments | Required | Default | Notes |
| --- | --- | --- | --- | --- | --- |
| `TYPESAFE_API_KEY` | api | Production, Preview | yes | empty | Provider key. Rotate on any suspicion of exposure. |
| `TYPESAFE_MODEL` | api | Production, Preview | no | `jev-latest` | Only `jev-latest` is accepted. |
| `TYPESAFE_TIMEOUT_SECONDS` | api | Production, Preview | yes on Vercel | `90` | Must stay below the function `maxDuration`. Set 45 on Vercel. |
| `ALLOWED_ORIGINS` | api | Production | yes | `http://127.0.0.1:5273,http://localhost:5273` | Comma separated. No trailing slash. Only GET and POST are allowed. |
| `MAX_UPLOAD_BYTES` | api | Production, Preview | no | `4000000` | Values above 4000000 are rejected at startup. |
| `MAX_DOCUMENT_PAGES` | api | Production, Preview | no | `40` | Page cap for extraction. |
| `MAX_EXTRACTED_CHARS` | api | Production, Preview | no | `60000` | Text cap for extraction. |
| `MAX_ANALYSIS_CHARS` | api | Production, Preview | no | `40000` | Text cap sent to the provider. |
| `VITE_API_BASE_URL` | web | Production | yes | empty | Build time. Empty means same origin, which is the dev proxy. No trailing slash needed, one is stripped. |

`TYPESAFE_TIMEOUT_SECONDS=45` matters. The default of 90 is longer than the
60 second function limit, so a stalled provider call would be killed by the
platform with a bare 504 instead of the app's own error envelope.

Preview builds get `VITE_API_BASE_URL` from the workflow, pointing at the API
preview of the same run. A preview created by hand needs a Preview value set
in the dashboard or the app will call its own origin.

## CI and CD flow

CI (`.github/workflows/ci.yml`) runs on every push and pull request to `main`:

- backend: `astral-sh/setup-uv`, `uv sync --frozen`, `uv run pytest -q`,
  `uv run ruff check app tests`.
- frontend: Node 22, `npm ci`, `npm test`, `npm run typecheck`,
  `npm run build`.

No secrets are required, so pull requests from forks still run.

Deploy (`.github/workflows/deploy.yml`) runs on push to `main` and by hand:

1. Check all four secrets are present.
2. `vercel deploy` in `backend/`, preview only.
3. Smoke test `https://<api-preview>/api/v1/health` until the body says
   `"status":"ok"`, six attempts, ten seconds apart.
4. `npm ci` and `vercel deploy` in `frontend/` with
   `VITE_API_BASE_URL=https://<api-preview>`.
5. Smoke test the web preview: HTTP 200 and the title `JEV Resume Analyzer`.
6. `vercel promote <preview-url> --yes` for the API, then for the web.
7. Smoke test production: API health body, web HTTP 200 and title.
8. On any failure, print the rollback commands in the job summary.

Any failed smoke test fails the job. Nothing is promoted until both previews
pass. The API promotes before the web, so a new web build never talks to an
older API.

`concurrency: deploy-production` with `cancel-in-progress: false` serialises
production deploys and rollbacks. A queued run waits; it is never cancelled
halfway through a promote.

Production URLs are taken from the `PROD_API_URL` and `PROD_WEB_URL`
repository variables when set. Otherwise `.github/scripts/prod_url.py` asks
the Vercel API for the deployment's production alias and takes the shortest
`.vercel.app` alias that is not a `-git-` branch alias.

## Blue-green on Hobby

Each deploy is an immutable deployment with its own URL. Production points at
one of them. That is the whole model:

- Preview deploy. Nothing user facing changes. Old production keeps serving.
- Promote. `vercel promote <url>` points the production domains at the new
  deployment. The switch is atomic per project.
- Rollback. `vercel rollback` points production back at the previous
  deployment. It takes seconds and needs no rebuild.

What Hobby does not have:

- No traffic split. A promote sends 100 percent of traffic to the new
  deployment. There is no 10 percent canary.
- No rolling releases. That feature is a Pro and Enterprise feature.
- No cross-project atomic switch. The API and web promote one after the
  other, so a few seconds of mixed versions are possible.

Because of that last point, keep API changes additive for one release. A new
web build should work against the previous API. Remove the old field or route
in a later deploy.

## Switching on rolling releases after a Pro upgrade

Rolling Releases and Skew Protection need a paid plan. Once the account is on
Pro, the API project can stage traffic:

```bash
# 1. Define the stages. Manual approval between 10, 50 and 100 percent.
vercel rolling-release configure \
  --cfg '{"enabled":true,"advancementType":"manual-approval","stages":[{"targetPercentage":10},{"targetPercentage":50},{"targetPercentage":100}]}'

# 2. Deploy production, or reuse a promoted deployment.
vercel deploy --prod

# 3. Start the release on a specific deployment.
vercel rolling-release start --dpl https://jev-api-abc123.vercel.app

# 4. Watch it.
vercel rolling-release inspect
vercel logs --environment production --level error --since 5m

# 5. Move to the next stage after the checks pass.
vercel rolling-release approve --dpl https://jev-api-abc123.vercel.app --currentStageIndex 0

# 6. Finish, or abort back to the previous deployment.
vercel rolling-release complete --dpl https://jev-api-abc123.vercel.app
vercel rolling-release abort --dpl https://jev-api-abc123.vercel.app
```

Automatic advancement uses `"advancementType":"automatic"` with a `duration`
in minutes per stage, for example
`{"targetPercentage":10,"duration":5}`. To turn the feature off again:
`vercel rolling-release configure --cfg 'disable'`.

Change `.github/workflows/deploy.yml` at the same time. Replace the two
`vercel promote` steps with `vercel deploy --prod` plus
`vercel rolling-release start --dpl <url>`, and keep the smoke tests before
the start step. For the web project, roll out at 100 percent: static assets
are immutable and cached, so a percentage split buys nothing.

Enable Skew Protection for both projects in the dashboard: Project ->
Settings -> Skew Protection -> Enabled. It keeps in-flight browser sessions on
the deployment they loaded. Without it, a tab opened before a promote can call
a newer API than the one its bundle expects.

## Rollback runbook

Use this when a production smoke test fails, or when a user-visible defect
appears after a promote.

1. Roll back with the workflow. Actions -> Rollback -> Run workflow. Choose
   `api`, `web` or `both`. It calls `vercel rollback` for the selected
   project, which returns production to the previous deployment.

2. Or roll back from a terminal:

   ```bash
   VERCEL_ORG_ID=<org-id> VERCEL_PROJECT_ID=<api-project-id> \
     npx vercel@latest rollback --yes --token "$VERCEL_TOKEN"

   VERCEL_ORG_ID=<org-id> VERCEL_PROJECT_ID=<web-project-id> \
     npx vercel@latest rollback --yes --token "$VERCEL_TOKEN"
   ```

3. Or promote an older deployment by URL, which also works when the previous
   deployment was itself a rollback target:

   ```bash
   cd backend
   npx vercel@latest promote https://jev-api-<older-hash>.vercel.app --yes --token "$VERCEL_TOKEN"
   ```

4. Verify:

   ```bash
   curl -s https://<api-host>/api/v1/health          # {"status":"ok"}
   curl -sI https://<web-host>/ | head -n 1          # HTTP/2 200
   ```

5. Record the failed deployment URL, the rollback time and the smoke results
   on the pull request or incident note. Fix forward on a new branch. Never
   re-promote the failed deployment.

Rolling back only moves traffic. If the bad deploy changed environment
variables, revert those in the dashboard separately, then redeploy. A provider
key leaked in a bad build must be rotated, not just rolled back.

## Limits

| Limit | Value | What it means here |
| --- | --- | --- |
| Request body | 4.5 MB, platform | Vercel rejects a larger body before the function runs. The app caps uploads at 4 MB (`max_upload_bytes`) and the request boundary at 4,000,000 + 65,536 bytes, so users get a JSON 413 instead of a platform error page. |
| Function duration | 300 s maximum on Hobby | `backend/vercel.json` sets 60 s. A review is two provider calls, so keep `TYPESAFE_TIMEOUT_SECONDS` below 60. Raise `maxDuration` up to 300 if page rendering needs it. |
| Function memory | 2 GB maximum on Hobby | Set to 1024 MB. PDF rendering is the memory heavy step. |
| Python bundle | 500 MB | `excludeFiles` and `.vercelignore` keep tests, caches, `.venv` and PDF fixtures out. PDF and image wheels dominate the bundle. |
| Cold start | none free | A cold Python function adds a second or more before the handler runs. The first request after idle is slower. Upload timeout is 30 s and is not affected. |
| Concurrency | none per instance | The request boundary admits two POSTs per instance. Vercel runs as many instances as it likes, so that is not a global cap and it does not protect the provider budget. |
| State | none | No database and no shared cache. `sessionStorage` is per tab. A reload loses the report unless the tab survives. |
| Static assets | none | Hashed assets are cached for a year and immutable. `index.html` is served by the SPA rewrite. |

The in-process limit is a safety valve for one instance. It is not rate
limiting. Anything that needs real limits needs an external counter or
Vercel's own firewall and rate limiting, which are plan dependent.

## Security

- The API is public and billable. `POST /api/v1/analyses` spends provider
  money on every accepted call, and there is no authentication. Treat the host
  as public from the first deploy.
- Set a spend cap on the TypeSafe account before the first public deploy.
  A spend cap is the only hard stop on cost.
- Rotate `TYPESAFE_API_KEY` after any suspected leak, and after any deploy
  that logged request data by mistake. Rotate in TypeSafe first, then update
  the Vercel variable, then redeploy.
- Keep the key in Vercel environment variables only. It is never in the repo,
  never in the frontend bundle and never returned by the API. The frontend has
  no provider SDK and no key.
- CORS is not authentication. Only browsers enforce it, and `curl` ignores it.
  It stops a random page from calling the API with a user's browser, nothing
  more.
- No cookies and no credentials. `allow_credentials` is false, and the client
  sends `credentials: 'omit'`.
- Consider Vercel Deployment Protection so preview and production URLs are not
  open to the world. Check which options the current plan includes before
  relying on it. Protection changes what the smoke tests can reach, so test it
  on preview first.
- CV text leaves the platform and goes to TypeSafe for analysis. Verify the
  provider's retention terms before inviting real users, and say so on the
  page.
- No request bodies, prompts or keys are logged. The API returns a safe error
  envelope with a request id.

## Cost per review

Platform side. A review is one function invocation of about 2 to 5 seconds at
1024 MB, plus a static asset request. That is roughly 2 to 5 GB-seconds of
function time per review, or 0.0006 to 0.0014 GB-hours. Compared with the
provider spend below, the platform cost is noise. Hobby has no per-seat fee.
Pro is billed per seat per month, around 20 USD at the time of writing: check
the current price before budgeting.

Provider side. Measured on the live two page fixture: 18,194 input tokens and
2,253 output tokens for one review, both provider calls included, with a
`duration_ms` of 869.8. A CV of four to six pages adds a second image call, so
budget about 1.5 times that token count. Multiply the token counts by the
TypeSafe rate card to get the per review price.

Cheap guardrails:

- The 4 MB cap and the 40 page cap bound how much text one review can send.
- `TYPESAFE_TIMEOUT_SECONDS=45` stops a slow call from holding a function for
  the full limit.
- A provider spend cap is the real ceiling. Set it to a number you are willing
  to lose in a day.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Browser console shows a CORS error | The web origin is not in `ALLOWED_ORIGINS` | Add the exact origin, scheme included, no trailing slash, then redeploy the API. |
| The web app calls its own `/api` and gets 404 | `VITE_API_BASE_URL` was empty at build time | Set it for the environment and redeploy the web. It is inlined at build time. |
| `413` with an HTML page | The body was over 4.5 MB, so Vercel rejected it | The app cap is 4 MB. Check the client limit. |
| `504` after 60 s | Provider call outlived the function limit | Lower `TYPESAFE_TIMEOUT_SECONDS`, then inspect the provider latency. |
| Deploy succeeds but health returns `ok` from the old build | The promote step did not run | Check the workflow log for the promote step, then promote by hand. |
| Smoke test cannot resolve a production URL | No production alias, or a custom domain only | Set `PROD_API_URL` and `PROD_WEB_URL` repository variables. |
