# JEV frontend contract v1

Status: implemented frontend contract, awaiting backend implementation. Binding definition: `frontend/src/api/schema.ts` (Zod runtime validation and inferred TypeScript types). This supersedes the proposed field details in architecture section 5, without changing that document. No actual provider output or live extraction has been verified. Synthetic fixtures live only under `frontend/tests/contract/fixtures`.

## Local runtime

- Frontend: React 18, Vite 8, TypeScript 5.6, Zod 3. Swiss layout: a 12 column grid, one grotesque family (self-hosted Inter), hairline rules, tabular numerals, one red accent. No CDN.
- From `frontend`: `npm ci`, `npm run dev`. Open `http://127.0.0.1:5273`.
- Browser requests relative `/api/v1/...`; Vite proxies `/api` to `http://127.0.0.1:8017`. Both are loopback-only. `strictPort` prevents silently changing the frontend port.
- Port choice is deliberate: this host has unrelated servers on 5173 through 5190, and workspace-mcp owns 8000. Do not kill them or send documents to them. The subsequent backend should listen on 127.0.0.1:8017. No backend application currently exists and none was started for this card.
- No VITE secrets, credentials, provider SDK, persistence, analytics or body logging in application code. Fetch uses `credentials: omit`.
- Production build is `npm run build`. `npm run preview` previews static output only; the `/api` proxy is a development configuration. Public deployment/reverse proxy is out of scope.

## Common conventions

JSON field names use snake_case. Required nullable fields must be present with `null`, not omitted. Arrays are present, possibly empty unless stated otherwise. Unknown response fields are stripped by Zod; unknown request fields are rejected. Numbers must be finite. Count fields are nonnegative integers. `text` below means nonempty string; user request text is trimmed and whitespace-only requests are rejected. The schema does not silently truncate inputs.

The backend is responsible for truthful rubric applicability, provider provenance, input limits and safe deterministic report assembly. The frontend cannot verify that a supplied rating was approved or a cost is trustworthy.

## GET /api/v1/health

200: `{ "status": "ok" }`.

Liveness only, no provider call. UI says Backend connected, not provider ready. Failed health check does not disable uploading. Timeout: 10 seconds. Two development GETs can occur under React StrictMode; POSTs are event-driven, not mount effects.

## POST /api/v1/documents/extract

Multipart input: exactly one field named `file`. Browser owns Content-Type and its boundary. Supports PDF and DOCX. Frontend limit is 10 MiB (10,485,760 bytes), one file, nonempty; case-insensitive extension check. Backend must independently enforce format signatures, limits, parsing safety and temporary-file cleanup. Client checks are not a security boundary.

200 fields:

| Field | Type | Meaning |
| --- | --- | --- |
| text | string | Complete extracted text, page separators preserved where practical |
| page_count | positive integer or null | Null when unknown |
| source_format | `pdf` or `docx` | Actual recognised format |
| warnings | array of `{code: text, message: text}` | Visible extraction limitations |

Example, synthetic test only:

```json
{"text":"SYNTHETIC TEST CV\nExample project.","page_count":1,"source_format":"pdf","warnings":[{"code":"partial_text","message":"SYNTHETIC warning: check reading order."}]}
```

Prefer 422 for empty/unreadable extraction. The UI defensively handles a successful empty `text`: editable preview stays visible and Analyse is disabled until meaningful text exists. OCR is not provided. Unknown warning codes are displayed, not discarded.

Timeout: 60 seconds, covering headers and body consumption. No automatic retries.

## POST /api/v1/analyses

JSON input:

```json
{"cv_text":"Confirmed full CV text","job_text":"Optional full posting","mode":"review"}
```

`cv_text`: required nonblank string. `job_text`: optional nonblank string, omitted when empty. `mode`: literal `review` only for this demo. `alignment_only` is deferred, not sent. Review includes job-alignment questions when a posting exists. CV/job text stays editable before submission, disabled during a request, and preserved after every error. Changing either requires a new explicit analysis request; no automatic billable calls.

200 response:

| Field | Type |
| --- | --- |
| analysis_id | nonempty request-scoped string, not a saved-record ID |
| rubric_version | nonempty version string |
| model | nonempty actual model identifier |
| findings | array of Finding below |
| overview | Overview below |
| warnings | array of `{code: text, message: text}` |
| metrics | Metrics below, or null |

### Finding

| Field | Type and semantics |
| --- | --- |
| question_id | nonempty string, unique within report |
| dimension | nonempty display label from backend |
| scope | `general_review` or `job_alignment` |
| assessment_level | literal `full_document`; no bullet-level findings |
| question | actual evaluated question, nonempty string |
| criteria | nonempty array of nonempty strings, actual answer criteria |
| answer | `present`, `absent`, `not_applicable`, or `unable_to_assess` |
| probabilities | null, or object containing all four answer keys with numbers 0..1 |
| confidence | provider-reported value 0..1, or null |
| rubric_explanation | null, or `{kind: "rubric", template_ref: text, text: text}` |
| page | 0-based page index, or null/omitted. Optional until the backend sends page geometry. |
| box | null/omitted, or `{top, bottom, left, right}` as fractions of page width and height. Bottom must sit below top, and right to the right of left. A box without a page is rejected. |
| severity | optional provider or rubric label. The vocabulary is not fixed yet, so the UI only echoes it as text in the finding detail. |

The overlay draws a rectangle only for a finding that carries both `page` and `box`. Nothing is placed by guesswork, and a finding without geometry still renders with a "No location" note. Page images are not part of this contract: no page image is uploaded, and the current branch has no rasteriser, so the document pane shows "No page preview" and lists the boxes instead.

Answer meanings: `present` = evidence meeting the question criteria is identifiable across the document; `absent` = that evidence is absent; `not_applicable` = rubric question does not apply; `unable_to_assess` = insufficiently reliable interpretation. The latter two are not treated as weak CV evidence or zero scores.

Probabilities must sum to 1 within 0.001 tolerance, otherwise reject the response. Never derive an answer distribution from a single confidence number. Missing provider distribution/confidence is null, not zero. The backend should map its actual provider answer into this categorical rubric; no model rationale or chain-of-thought is expected or displayed. Explanation is predefined rubric text, visibly labelled, not generated advice.

### Overview

`questions_total`, `questions_answered`, `questions_assessable`: nonnegative integers. Total is the prepared applicable question count, including questions whose answers were not returned. Answered equals `findings.length`, including not-applicable/unable-to-assess answers. Assessable equals number of findings with answer present or absent. Enforce assessable <= answered <= total.

UI displays counts, not a fabricated quality percentage. If answered < total, warnings MUST include code `partial_response` and a meaningful message. A zero-finding response is supported, with no invented findings.

`rating`: null until a scoring mapping is approved and enough evidence exists; otherwise `{value: number, scale_min: number, scale_max: number, label: text, basis: text}`. Scale min < max, value in range, at least one assessable finding. No fixed 1..5 scale is assumed. Rating measures communication quality, never hiring probability or ATS acceptance. Frontend never computes a rating or substitutes zero for null. Backend must enforce approval and sufficiency, not rely only on this structural check.

### Metrics

All fields required when metrics is not null:

- `duration_ms`: finite nonnegative measured number or null.
- `input_tokens`, `output_tokens`: nonnegative integer or null, provider-reported.
- `cost_usd`: finite nonnegative number or null. Supply only from verified pricing or trustworthy provider reporting. UI does not estimate cost.

Timeout: 120 seconds covering response headers and body. There are no automatic retries. Timeout can leave server-side processing running; UI warns a manual retry may incur another charge. No cancellation/deletion guarantee. Reset is disabled while a request is pending to prevent late responses repopulating cleared state.

## Error envelope

Every non-2xx, including FastAPI validation failures:

```json
{"error":{"code":"PROVIDER_UNAVAILABLE","message":"Provider is not configured.","retryable":true},"request_id":"request-scoped-id"}
```

`request_id` is at the envelope root and may be null. `error.code`, `error.message`: nonempty strings. `retryable`: boolean. Do not return provider secrets, exception traces, applicant text, or raw validation payloads. Frontend preserves this flag in ApiError; it never automatically retries, including when true. False does not prohibit a corrected manual submission.

Expected statuses: 413 limits, 415 unsupported format, 422 unreadable/invalid input, 429 capacity, 502 upstream/invalid response, 503 unconfigured provider, 504 timeout. Generic non-JSON errors yield safe HTTP-status copy, not raw server HTML. A malformed 2xx yields `RESPONSE_INVALID` and no report. Network failures yield `NETWORK_UNREACHABLE`. Client timeout yields `REQUEST_TIMEOUT`.

## UI state and storage

Upload -> extracting -> check text -> analysing -> report. After extraction the page becomes a two pane workspace: the document pane on the left, the editable text or the report on the right, with no page change between them. Below 900px the panes stack and the document pane collapses. Extraction failure returns to upload with an error; analysis failure returns to check text with the error and both edited inputs preserved. Native file input and keyboard-accessible disclosures are the baseline; drop is an enhancement. Focus moves to the stage heading on a stage change, errors and statuses are announced, actions have 44px minimum height, and reduced motion is respected. Results render server strings as React text, never HTML.

Session state lives in sessionStorage under one versioned key, `jev.state.v1`: stage, file name, extraction, CV text, job posting, report and the selected finding. The file bytes are never stored, so after a reload the text and report return and the document pane asks for the file again instead of showing an empty page. Writes are wrapped in try/catch: on a quota failure the app keeps working in memory and shows a short notice. Reset and a new upload clear every `jev.` key. No localStorage, IndexedDB, cookie or service worker cache is used, and there is no account or database.

Edit text from the report clears the report and returns to check text. Clear document and start over clears CV, extraction, job posting, filename, error, report, selected finding and stored keys. Clearing this tab does not imply provider deletion. Before submission the UI discloses TypeSafe transfer and unverified retention terms.

## Verification and integration gaps

- `npm run build`, `npm run typecheck`, `npm test` verify implementation and synthetic contracts.
- Browser tests: start `npm run dev`, then `CHROMIUM_PATH=<installed Chromium executable> npx playwright test`. Verified here with `/root/.cache/ms-playwright/chromium_headless_shell-1208/chrome-headless-shell-linux64/chrome-headless-shell`; the shell installs with `npx playwright install chromium-headless-shell`.
- Browser suite asserts title before flow actions; prevents accidentally testing another service. First test requires backend absent and checks the real Vite 502 error path using only a synthetic upload, tabbing from the skip link to the file input. Two further tests intercept APIs with explicitly labelled synthetic fixtures at 375 and 1280px, check the two pane workspace, box selection in both directions, provider-error text preservation, finding details, session storage, reset, no JS exceptions, no horizontal overflow, 44px targets and axe WCAG A/AA checks.
- Real PDF/DOCX parsing, provider output mapping, billing/retention, backend budgets, and real upload-to-TypeSafe-to-report integration remain untested because the backend does not exist yet. No test fixture claims to be live output.
- Screenshot files are under `frontend/test-results`. They are synthetic fixtures only. A visual review at 375 and 1280 was done against those files, with the document pane's overlay checked against a local harness; DOM geometry and axe checks are not a substitute for a real design review.
