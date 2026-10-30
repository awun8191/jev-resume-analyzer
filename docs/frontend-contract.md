# JEV frontend contract v1

Status: implemented frontend contract. The backend now returns `scores`, `dimensions` and `structure_findings`; rendering them is the pending frontend task. Binding definition: `frontend/src/api/schema.ts` (Zod runtime validation and inferred TypeScript types). This supersedes the proposed field details in architecture section 5, without changing that document. The score fields below are from a verified live analysis of the synthetic two page fixture; the frontend has not rendered them yet. Synthetic fixtures live only under `frontend/tests/contract/fixtures`.

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

Multipart input, the shape the workspace uses:

| Part | Content |
| --- | --- |
| `request` | The JSON body below, as a field or as an uploaded part named `request` |
| `file` | Optional. The uploaded PDF. Required for a structure score |

A JSON body with no file still works and returns a content only report. An upload that is not a PDF gets no structure score and a `structure_unavailable` warning; the content report is still returned.

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
| scores | Scores below. Always present |
| dimensions | array of Dimension below. Always present, possibly empty |
| structure_findings | array of StructureFinding below. Always present, possibly empty |

### Scores

`scores.content`:

| Field | Type | Meaning |
| --- | --- | --- |
| value | integer 0..100 or null | Weighted percentage over the checks that could be decided. Null when fewer than 50 of 100 points were decidable |
| band | text or null | One of the five band labels below |
| range | `[integer, integer]` or null | Low and high score still consistent with the evidence. Null when no check was applicable |
| coverage | number 0..1 | Decided weight over prepared weight |
| assessed_weight | integer 0..100 | Points that could be decided. `unable_to_assess` and `not_applicable` are not decided points |

`scores.structure`:

| Field | Type | Meaning |
| --- | --- | --- |
| value | integer 0..100 or null | Layout score. Null when the route could not run |
| band | text or null | Same five labels |
| reason | text or null | `scored`, `page_not_readable`, `page_empty`, `insufficient_evidence`, `no_file`, `unsupported_format`, `render_failed` or `provider_error` |
| assessed_weight | integer 0..100 | Structure points that could be assessed |

A null structure score is never zero. Render "Not scored" with the reason, never a number.

`scores.total`: `value` integer or null, `band` text or null, `mode` one of `combined`, `content_only`, `structure_only`, `unavailable`. The rule is `round(0.7 * content + 0.3 * structure)`. A missing structure score renormalises to content only, and the mode says so.

Bands, highest first: `Very strong evidence` at 90, `Strong evidence` at 75, `Adequate evidence` at 60, `Partial evidence` at 40, `Thin evidence` at 0.

### Dimension

`key` text, `label` text, `owner` `content` or `structure`, `weight` integer, `value` integer or null, `section` section key or null. Content rows weigh 100 together, and so do structure rows. Structure rows exist only when the structure report was scored.

### StructureFinding

`id` text, `label` text, `severity` `pass`, `minor`, `major` or `unassessable`, `points_lost` integer 0..100, `page` 0-based integer or null, `box` `{top, bottom, left, right}` fractions or null, `confidence` number 0..1 or null, `evidence` text. A pass row carries no page and no box, because the rubric does not report where a check passed. Below 0.5 box confidence the box is the whole page, and the finding says so in `evidence`.

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
| page | 0-based page index, or null/omitted. Optional. |
| box | null/omitted, or `{top, bottom, left, right}` as fractions of page width and height. Bottom must sit below top, and right to the right of left. A box without a page is rejected. |
| section | optional section key such as `experience`, `education`, `skills`, `summary`, `header` or `projects`. Case and spacing are ignored. |
| severity | optional provider or rubric label. The vocabulary is not fixed yet, so the UI only echoes it as text in the finding detail. |

The overlay draws a rectangle only when data supports it. A finding with a `section` prefers the exact box derived from the PDF text layer on its page. A finding without a section keeps its reported `page` and `box`. A finding with neither is not drawn, and still renders with a "No location" note. No rectangle is placed by guesswork.

The document pane rasterises the uploaded PDF in this tab with pdf.js and reads the same document's text layer. Page images and section boxes are built in memory, never uploaded and never stored. A scanned PDF has no text layer, so it yields no sections and the pane keeps the reported boxes or its empty state.

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

A structure request reviews at most the first six pages of the PDF, in groups of at most three. When the document is longer, warnings include `structure_page_budget` and the structure score covers the first six pages only. Warnings may also include `structure_unavailable` when the structure score is null, and `partial_response` when the provider answered fewer questions than the rubric asks.

Timeout: 120 seconds covering both provider calls, response headers and body. There are no automatic retries. Timeout can leave server-side processing running; UI warns a manual retry may incur another charge. No cancellation/deletion guarantee. Reset is disabled while a request is pending to prevent late responses repopulating cleared state.

## Error envelope

Every non-2xx, including FastAPI validation failures:

```json
{"error":{"code":"PROVIDER_UNAVAILABLE","message":"Provider is not configured.","retryable":true},"request_id":"request-scoped-id"}
```

`request_id` is at the envelope root and may be null. `error.code`, `error.message`: nonempty strings. `retryable`: boolean. Do not return provider secrets, exception traces, applicant text, or raw validation payloads. Frontend preserves this flag in ApiError; it never automatically retries, including when true. False does not prohibit a corrected manual submission.

Expected statuses: 413 limits, 415 unsupported format, 422 unreadable/invalid input, 429 capacity, 502 upstream/invalid response, 503 unconfigured provider, 504 timeout. Generic non-JSON errors yield safe HTTP-status copy, not raw server HTML. A malformed 2xx yields `RESPONSE_INVALID` and no report. Network failures yield `NETWORK_UNREACHABLE`. Client timeout yields `REQUEST_TIMEOUT`.

## UI state and storage

Upload -> extracting -> check text -> analysing -> report. After extraction the page becomes a two pane workspace: the document pane on the left, the editable text or the report on the right, with no page change between them. Below 900px the panes stack and the document pane collapses. Extraction failure returns to upload with an error; analysis failure returns to check text with the error and both edited inputs preserved. Native file input and keyboard-accessible disclosures are the baseline; drop is an enhancement. Focus moves to the stage heading on a stage change, errors and statuses are announced, actions have 44px minimum height, and reduced motion is respected. Results render server strings as React text, never HTML.

Session state lives in sessionStorage under one versioned key, `jev.state.v1`: stage, file name, extraction, CV text, job posting, report and the selected finding. The file bytes are never stored, so after a reload the text and report return and the document pane asks for the file again instead of showing an empty page. Page images and section boxes are derived from the in-memory File on every attach and are not persisted. Writes are wrapped in try/catch: on a quota failure the app keeps working in memory and shows a short notice. Reset and a new upload clear every `jev.` key. No localStorage, IndexedDB, cookie or service worker cache is used, and there is no account or database.

### Exact section boxes

pdf.js renders each page to a canvas at twice the point size and reads text items from the same document. Items are grouped into lines by baseline, and each line splits where the horizontal gap exceeds a word space, which keeps two columns apart. A heading is a short line that matches HEADER, SUMMARY or PROFILE, EXPERIENCE, EDUCATION, SKILLS, PROJECTS, or a listed variant, and whose glyph height is at or above the page body median. A section span runs from its heading top to the next heading top in the same column, or the page bottom. Spans are clamped to the page and sorted. A page that starts without a heading continues the previous page's last section, with one box per section per page. `frontend/tests/pdfLayout.test.ts` covers a single column, two columns, a page without headings, two heading sizes and a continuation page.

Edit text from the report clears the report and returns to check text. Clear document and start over clears CV, extraction, job posting, filename, error, report, selected finding and stored keys. Clearing this tab does not imply provider deletion. Before submission the UI discloses TypeSafe transfer and unverified retention terms.

## Verification and integration gaps

- `npm run build`, `npm run typecheck`, `npm test` verify implementation and synthetic contracts.
- Browser tests: start `npm run dev`, then `CHROMIUM_PATH=<installed Chromium executable> npx playwright test`. Verified here with `/root/.cache/ms-playwright/chromium_headless_shell-1208/chrome-headless-shell-linux64/chrome-headless-shell`; the shell installs with `npx playwright install chromium-headless-shell`.
- Browser suite asserts title before flow actions; prevents accidentally testing another service. First test requires backend absent and checks the real Vite 502 error path using only a synthetic upload, tabbing from the skip link to the file input. Two further tests intercept APIs with explicitly labelled synthetic fixtures at 375 and 1280px, check the two pane workspace, box selection in both directions, provider-error text preservation, finding details, session storage, reset, no JS exceptions, no horizontal overflow, 44px targets and axe WCAG A/AA checks.
- PDF rendering and text layout were checked manually in Chromium against a synthetic two page PDF generated outside the repo; no fixture is committed. DOCX pages are not rendered. Provider output mapping, billing/retention, backend budgets, and real upload-to-TypeSafe-to-report integration remain untested because the backend does not exist yet. No test fixture claims to be live output.
- Screenshot files are under `frontend/test-results`. They are synthetic fixtures only. A visual review at 375 and 1280 was done against those files, with the document pane's overlay checked against a local harness; DOM geometry and axe checks are not a substitute for a real design review.
