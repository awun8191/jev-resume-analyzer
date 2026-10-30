# JEV backend implementation (card t_e4a2a14e)

Status: implemented and verified on this host. Not deployed, not in git (per card).

## Commands used (from backend/)

- `uv sync` - project-local virtualenv, Python 3.14.6, deps per pyproject.toml
- `uv run pytest -q` - full synthetic suite (live test skips without JEV_RUN_LIVE=1)
- `uv run pytest tests/live/test_live.py -s` - billable, requires JEV_RUN_LIVE=1 AND a
  running API on 127.0.0.1:8017
- `uv run uvicorn app.main:app --host 127.0.0.1 --port 8017 --no-access-log`
- `uv run ruff check app tests` and `uv run ruff format app tests`

## Current synthetic verification (cleanup card t_fdb62e42, 2026-09-17)

- From the project root, `env -u JEV_RUN_LIVE uv run --directory backend pytest -o addopts='' -q`:
  277 passed, 0 failed, 3 gated-live skipped, exit 0 (review wiring). The 69 test run
  below belongs to the earlier card.
  The warnings concern Starlette's httpx TestClient and AnyIO BlockingPortal alias.
- From backend/, `uv run ruff check .`: all checks passed, exit 0.
- Additional `uv run ruff format --check app tests`: exit 1; two existing files
  (`app/middleware.py`, `tests/integration/test_boundaries.py`) would be reformatted,
  27 already formatted. Left unchanged to keep this cleanup scoped.
- Removed obsolete `backend/scripts/check_parsers.py`: no repository callers found;
  it only printed parser output using synthetic fixture generators from
  `tests/integration/test_documents.py`. That module's `test_extraction` already
  asserts PDF/DOCX extraction through the API, including text and page counts.
- No billable live test was run during this cleanup. The live evidence below is historical,
  not a result of this synthetic verification run.

## Historical implementation results (card t_e4a2a14e)

- Original synthetic run: 61 tests passed, 0 failed, exit 0 (unit 9, integration 52 including
  limits/boundaries; live skipped when not gated). Superseded by the current count above.
- Original live run (one billable POST, authorized local resume): HTTP 200 through the running API,
  model reported by provider `jev-1.13.0`, 8 findings, measured duration_ms 433.8,
  usage input 4086 / output 421 tokens, cost_usd null, rating null, extraction 1 page /
  4,965 characters. Zod validation of actual responses against frontend schema: 4 checked,
  0 failures (health, synthetic DOCX extraction, authorized PDF extraction, report).
- PDF and DOCX verified: extraction, preview contract fields, error envelopes.
- Health and extraction exercised with gateway dependency overridden to fail loudly:
  no provider dependency is resolved, no unexpected provider calls.

## Contract decisions

- Error envelope covers FastAPI validation and every non-2xx including 404s.
  request_id is at the envelope root.
- 415 requires extension plus magic signature; 422 unreadable/scanned/encrypted; 413 for
  byte, decompressed-DOCX, extracted-character and serialized-provider budgets.
- Two Jev POSTs per analysis: one text call and one image call. A PDF longer than
  three pages adds a second image call, so a four to six page CV costs three calls.
  httpx retries stay disabled and every response is read with a cap. Invalid or
  partial provider JSON is a 502 for the text call and a null structure score with a
  `provider_error` reason for the image call; nothing is fabricated, ever.
- Review uses rubric v3.1: twenty full-document checks, including three alignment
  checks that the rubric marks not applicable when no posting exists. The four
  provider options are exactly the contract keys, never remapped.
- The report adds `scores`, `dimensions` and `structure_findings`. Total is
  `round(0.7 * content + 0.3 * structure)`; a missing structure score renormalises to
  content only and sets `mode` to `content_only`.
- rating and cost_usd are always null; probabilities/confidence are provider-reported or
  null; usage only from provider metrics; duration_ms measured around the gateway call.
- Deterministic rubric explanations only (kind rubric, template_ref v3.<id>.<answer>).

## Review wiring (feat/review-wiring)

- `POST /api/v1/analyses` accepts JSON, or multipart with a `request` part holding
  that JSON and an optional `file` part holding the PDF. Both shapes return one
  report. A malformed or partial multipart body is a 422 envelope.
- Content: the twenty v3.1 questions go in the single text call, state carries
  `cv_text` and optional `job_text`, and the answers go through
  `scoring_v3.score_report`. `not_applicable` and `unable_to_assess` are kept as
  answered and never score zero. A missing answer counts as `unable_to_assess`.
- Structure: pages are rasterised with `page_render`, sent as multipart with
  `TypeSafe-Danger-Zone-Images: true`, model pinned to `jev-1.14.0`, and scored with
  `structure_v1`. At most six pages, three per request, and answers merge into one
  document assessment per check using the worst page.
- A missing file, a DOCX or other non-PDF upload, a rasterisation failure and a
  provider failure each give a null structure score with a reason plus a
  `structure_unavailable` warning. A seventh page or later adds
  `structure_page_budget`. Zero is only ever a real scored zero.
- Metrics sum both calls' token counts. `duration_ms` covers both calls.
- The v1 and v2 rubric modules and `services/layout_checks.py` stay in the tree but
  the flow does not call them: the v3 rubric owns content and the image route owns
  layout, so the old "visual placement: not assessed, Jev is text-only" metadata row
  would now be false.

Live verification of the wiring, one billable analysis of the committed synthetic two
page fixture through a local API. Both calls ran. Model `jev-1.14.0`, content 90
(range 90 to 90, coverage 1.0, assessed 100), structure 94 (assessed 94, nine checks
passed, one major defect, one unassessable), total 91 combined, 18 dimension rows,
`duration_ms` 869.8, tokens summed from both calls 18,194 in and 2,253 out, cost null.
The structure score is 94 and not 100 because one check could not be verified and one
page lost points, which is the honest outcome for that fixture.

## Operations

- Parsing runs in a disposable subprocess with PATH-only env, 384MiB address-space and
  10s CPU rlimits; hard timeout converts to a safe 422. No temp files are used at all.
- Request boundary middleware caps request bytes before multipart spooling (10MiB+64KiB
  for uploads), times out slow uploads (408), admits at most two concurrent POSTs (429)
  and swallows unhandled exceptions into the safe envelope so exception text cannot leak.
- No logging of bodies, prompts or credentials; no CORS middleware; secrets stay in
  backend/.env read by pydantic-settings only (never printed, never exported).

## Known limitations

- DOCX headers, footers, footnotes and embedded objects are not extracted (warning shown).
- PDF page separators are form feeds; no OCR; scanned PDFs are a safe 422 with guidance.
- Provider token budget is approximated conservatively (28,000 serialized UTF-8 bytes)
  because live docs describe an approximate 32,000-token shared budget, not an exact API.
- Provider retries are disabled by design; 429/529 surface as 429/503 for manual retry.
- The live PDF in /home/admin/Downloads has a space in its filename; the card text wrote
  it with hyphens. The gated test uses the actual file, never copies it into the repo.
