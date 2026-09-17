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
  69 passed, 0 failed, 1 gated-live skipped, 2 dependency deprecation warnings, exit 0.
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
- One Jev POST per analysis (httpx retries disabled; stream read with response cap).
  Invalid/partial provider JSON is a 502; nothing is fabricated, ever.
- Review uses six full-document questions; a posting adds two alignment questions.
  The four provider options are exactly the contract keys, never remapped.
  Optional summary maps not_applicable, never a penalty.
- rating and cost_usd are always null; probabilities/confidence are provider-reported or
  null; usage only from provider metrics; duration_ms measured around the gateway call.
- Deterministic rubric explanations only (kind rubric, template_ref v1.<id>.<answer>).

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
