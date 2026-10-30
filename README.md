# JEV Resume Analyzer

Review a CV with fast, structured AI judgments, optionally against a job posting. Upload a PDF or DOCX, check the extracted text, and get a traceable report: every assessment shows the exact question, criteria, answer, and probability distribution behind it.

Built on [TypeSafe](https://typesafe.ai) (System One model, `jev-latest`): structured judgments composed in code, not prompt-and-parse text generation.

## What it does

- **Content score**: twenty typed judgments over the whole document, grouped into seven dimensions (impact, scope, ownership, relevance, clarity, completeness, skills) and weighted to 100.
- **Structure score**: eleven checks over the page images (margins, hierarchy, spacing, density, columns, tables and more), weighted to 100.
- **One total**: 70 percent content and 30 percent structure. A missing structure score renormalises to content only and says so; it never becomes zero.
- **Optional job alignment**: paste a posting; three document-level questions assess how the CV evidences relevant responsibilities and qualifications, and whether that evidence is consistent across entries.
- **One workspace**: after upload the document pane sits on the left and the text or report on the right. Findings can draw a hairline box on their page, and selecting either side selects the other.
- **Honest uncertainty**: four answer outcomes (`present`, `absent`, `not_applicable`, `unable_to_assess`) with real probability distributions. "No summary" is not a defect; "unable to assess" is not a zero.
- **Traceable findings**: expand any finding to see the evaluated question, its criteria, the answer, and per-option probabilities. Explanations are predefined rubric text, clearly labelled: never generated advice.
- **Local demo**: no accounts, no database, no localStorage. CV text and any report live in this tab's sessionStorage and are cleared when the tab closes or on reset. Two Jev requests per analysis, one for text and one for page images; failed requests never produce fabricated reports.

## Stack

| Layer | Tech |
| --- | --- |
| Frontend | React 18, Vite, TypeScript, Zod-validated API contract |
| Backend | FastAPI, Pydantic, pypdf, defusedxml (DOCX XML traversal) |
| AI | TypeSafe System One API: `jev-latest` for text, `jev-1.14.0` for page images |

## Quick start

Requirements: Python 3.11+, Node 20.19+ or 22.12+, [uv](https://docs.astral.sh/uv/), a TypeSafe API key.

```bash
# Backend
cd backend
cp .env.example .env
# Edit .env and set TYPESAFE_API_KEY
uv sync
uv run uvicorn app.main:app --host 127.0.0.1 --port 8017

# Frontend (second terminal)
cd frontend
npm ci
npm run dev
# open http://127.0.0.1:5273
```

The Vite dev server proxies `/api` to the backend on `127.0.0.1:8017`.

## Tests

```bash
# Backend: 277 synthetic tests + lint (live tests are gated behind JEV_RUN_LIVE=1 and a running API)
cd backend && uv run pytest -q && uv run ruff check app tests

# Frontend: 50 tests, typecheck, build
cd frontend && npm test && npm run typecheck && npm run build

# Browser flows (needs Chromium; see docs/frontend-contract.md)
cd frontend && CHROMIUM_PATH=<chromium-binary> npx playwright test
```

## Design boundaries

- Full-document assessments only; no fabricated bullet-level findings.
- Two provider calls per analysis. The text call asks the rubric questions. The image call reviews at most the first six PDF pages in groups of three, pinned to `jev-1.14.0` because Box questions need it. A fourth to sixth page adds a second image call, so a long CV costs three calls.
- Structure is scored only from a PDF. A DOCX upload, a missing file or a page that cannot be rendered gives a null structure score with a reason and a warning, never zero.
- No overall rating is shown yet: scoring maps stay `null` until calibrated on reviewed examples.
- No hiring predictions, ATS scores, truthfulness verdicts, or generated rewrites.
- Localhost demo: CV text is sent to TypeSafe for analysis; retention terms should be verified before any public deployment.

## Docs

- `docs/architecture.md`: proposed architecture, API contracts, runtime flow
- `docs/frontend-contract.md`: binding frontend↔backend schema (implemented in `frontend/src/api/schema.ts`)
- `docs/backend-implementation.md`: backend verification evidence and contract decisions
- `docs/frontend-contract.md` and the rubric modules under `backend/app/rubrics/` define what every question means

## Status

Working end-to-end on localhost: upload → editable extraction preview → one text and one image request → traceable report with content, structure and total scores. Deferred: generated suggestions (phase 2), OCR, accounts, public deployment.
