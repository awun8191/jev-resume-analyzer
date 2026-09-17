# JEV Resume Analyzer: proposed architecture

Status: architecture for review, not implemented.

## 1. Product scope

A localhost demo for applicants to review a CV, with optional comparison against a job posting. No sign-in, database, saved history, generated rewrites, or hiring predictions in version one.

The interface uses React, Vite, and TypeScript. Visual direction: white surfaces, thin grey borders, blue accents, restrained typography, accessible contrast, and responsive layouts.

The API uses FastAPI and Pydantic. It extracts document text and sends the full readable CV, plus an optional job posting, to Jev as shared state. All applicable independent questions are evaluated in one TypeSafe request per analysis action. Section reconstruction is not a prerequisite.

## 2. Proposed repository layout

```text
jev-resume-analyzer/
  README.md
  .gitignore
  docs/
    architecture.md
    rubric.md
  frontend/
    package.json
    package-lock.json
    tsconfig.json
    vite.config.ts
    index.html
    src/
      main.tsx
      App.tsx
      components/
        ui/
      features/
        upload/
        preview/
        analysis/
        results/
      api/
        client.ts
        schema.d.ts
      styles/
        tokens.css
        global.css
    tests/
  backend/
    pyproject.toml
    uv.lock
    .env.example
    .env                     # local only, ignored
    app/
      main.py
      config.py
      dependencies.py
      errors.py
      routers/
        health.py
        documents.py
        analyses.py
      models/
        documents.py
        analyses.py
        questions.py
        errors.py
      services/
        extraction.py
        analysis.py
        reporting.py
      parsers/
        pdf.py
        docx.py
      gateways/
        typesafe.py
      rubrics/
        cv_review_v1.py
        job_alignment_v1.py
    tests/
      unit/
      integration/
      live/
```

These are proposed files, not existing scaffolding. Create components when needed, not empty abstraction layers. There is no repository/database layer because there is no persistence requirement.

## 3. Responsibility boundaries

- Routers: HTTP validation, dependency injection, response contracts, status codes. No model prompts or document parsing logic.
- Models: Pydantic request/response and internal data contracts. These are data schemas, not database entities.
- Services: coordinate extraction, question preparation, and report assembly without depending on HTTP request objects.
- Parsers: format-specific extraction; preserve readable order and page boundaries where available. Do not force content into predefined CV sections.
- Rubrics: versioned question templates, answer definitions, applicability rules, and any approved rating mappings. No network calls.
- TypeSafe gateway: translate internal questions to the current SDK schema, invoke Jev, and normalise validated responses. No frontend code imports the SDK.
- Reporting service: deterministic labels and explanations, uncertainty handling, and approved rating calculation. No generative model.
- Dependencies: provide settings, parser registry, gateway, and services through FastAPI Depends. Use an injectable gateway boundary for testing rather than a large DI framework.
- Main: construct the app, register routes and exception handlers, manage the shared provider client's lifespan.

Question definitions have one source of truth in the backend. The UI receives the evaluated questions and criteria with the report. Generate TypeScript API types from FastAPI OpenAPI rather than hand-maintaining duplicate schemas.

## 4. Runtime flow

1. Applicant chooses or drops a PDF/DOCX.
2. Frontend calls the extraction endpoint. Backend validates the upload and extracts text without contacting Jev.
3. Frontend shows editable extracted text and parsing warnings, plus an optional job-posting text field.
4. Applicant confirms the content and selects Analyse.
5. Backend validates the supplied text and builds full-document diagnostic questions. Job-related questions are included only if a posting is present.
6. The gateway sends one shared state and all applicable questions to Jev.
7. Backend validates the answer set, assembles deterministic findings, and returns the report with question-level observability.
8. Reset removes the document and report from frontend application state.

Extraction and analysis are separate HTTP requests to support the preview. Only analysis contacts Jev. No job queue, polling, SSE, or WebSockets are needed initially. The frontend shows actual request stages, not simulated percentage progress. CPU-heavy parsing runs off the async event loop with bounded concurrency.

If a job posting is added later, a new alignment request can reuse the confirmed CV text. Existing general-review findings need not be regenerated. The frontend invalidates those findings whenever the CV text changes.

## 5. Proposed API contracts

All paths below are under /api/v1.

### GET /health

Liveness response: status. Does not call Jev or disclose credentials.

### POST /documents/extract

Input: multipart file.

Output:
- text: full extracted text, preserving page separators where practical.
- page_count: integer or null when unavailable.
- warnings: structured code/message pairs for extraction limitations.
- source_format: pdf or docx.

No server-side document ID is required because no document is retained for later lookup. Temporary upload files are closed and deleted after extraction, including failure paths.

### POST /analyses

JSON input:
- cv_text: required confirmed CV text.
- job_text: optional job posting.
- mode: review or alignment_only. Review includes alignment questions when job_text exists. Alignment-only requires job_text.

JSON output:
- analysis_id: request-scoped identifier for troubleshooting, not a saved-record ID.
- rubric_version and model identifier.
- findings: question_id, dimension, scope, question text, answer criteria, typed answer, probabilities, and provider confidence where available.
- overview: assessment coverage and optional rubric-based rating. Rating is null when not approved or insufficiently assessable.
- warnings: extraction-independent analysis limitations, uncertain results, and partial-response notices.
- metrics: measured request duration and provider-reported token usage. Monetary cost is omitted or null unless reliably provided or calculated from verified pricing.

No fabricated model reasoning or quotation. Predefined explanations must be labelled as rubric explanations. Do not claim per-bullet findings when questions are document-level.

### Error contract

Use a consistent envelope: error.code, error.message, error.retryable, request_id. Normalise FastAPI validation failures too.

- 413: upload or request exceeds configured limits.
- 415: unsupported format.
- 422: empty/unreadable document or invalid input.
- 429: request capacity/rate limit, with retry guidance when known.
- 502: upstream failure or structurally invalid response.
- 503: provider integration unavailable or unconfigured.
- 504: provider timeout.

Preserve user text on recoverable errors. Do not return exception traces or provider credentials.

## 6. Jev request design

Shared state contains the complete CV and optional complete posting, not a forced section schema. Questions explicitly reference the relevant fields and define their own criteria. Document content is untrusted evidence, never instructions.

Optional sections use answer categories such as no identifiable summary, not applicable, or unable to assess. They do not require a preliminary detection request.

Begin with document-level work clarity, contribution clarity, interpretability, outputs/results, scope, and conditional summary checks. Rewrite the earlier per-entry rubric into this scope before implementation; do not silently reuse questions requiring nonexistent entry IDs.

Initial job assessment is document-level. Exhaustive requirement-by-requirement coverage requires a reliable way to enumerate criteria and preserve AND/OR alternatives. That is not assumed solved by supplying the full posting. Do not promise exhaustive requirement matrices in the first demo.

Questions in a batch cannot see other answers. Dependent interpretations are performed in code after responses arrive. The server checks input/question budgets against verified live provider limits before sending. Never silently truncate a CV or discard questions. If too large, return a clear limitation; additional model passes need an explicitly revised design.

Do not automatically retry a potentially billable POST whose outcome is unknown. Any bounded retry behaviour must account for the provider's documented semantics. Surface rate limits honestly.

## 7. UI structure

- Upload: labelled, keyboard-accessible file input with drag/drop enhancement; accepted formats and limits visible.
- Preview: full editable extraction and warnings; no fabricated section boundaries.
- Optional posting: expandable text area, no required login or separate workflow.
- Report overview: restrained grid of dimension assessments and assessment coverage. General review and job alignment remain separately labelled.
- Finding details: readable diagnostic cards with expandable question, criteria, answer distribution, and rubric explanation.
- Error and uncertain states: text labels, not colour alone. Provider uncertainty is distinct from weak CV evidence.

Use blue for actions and navigation, not as the sole status indicator. Avoid decorative charts implying precision unsupported by the rubric. No overall percentage until scoring mappings and coverage rules are approved and tested. An overall rating measures communication quality, not hiring probability or ATS acceptance.

## 8. Configuration, security, and retention

backend/.env is the project-local secret store, read by backend settings. Never copy the key into frontend VITE_* variables or globally export it. Commit backend/.env.example with blank credential values and documented nonsecret defaults.

Proposed settings: TYPESAFE_API_KEY, TYPESAFE_MODEL, TYPESAFE_TIMEOUT_SECONDS, MAX_UPLOAD_BYTES, MAX_DOCUMENT_PAGES, MAX_EXTRACTED_CHARS. Exact model ID and provider limits are verified during integration; app limits are chosen independently and documented.

Vite proxies /api to the loopback FastAPI server during development. Browser calls relative API paths. Do not introduce wildcard CORS unnecessarily. Localhost first; anonymous public hosting requires separate abuse controls before launch.

Validate file signatures and extensions, bound decompressed DOCX content and processing work, reject encrypted/unsupported documents with an actionable message, and clean temporary resources. Scanned PDFs without usable text require OCR or pasted text; OCR is outside the initial scope.

Do not log uploaded text, request bodies, provider prompts, or credentials. Keep only request IDs, durations, counts, status codes, and safe error categories in logs. No analytics or browser persistent storage for CV content by default. Clearing local state is not a promise of provider-side deletion.

Before submission disclose that CV text is sent to TypeSafe. Localhost does not mean offline/private inference. Provider retention terms require verification before public use. Applicants can remove personal contact details in the preview.

Root .gitignore excludes .env and .env.*, except .env.example; virtual environments; node_modules; build/test caches; logs; uploads; generated reports; and real CV samples. Keep package lockfiles committed. Never commit API keys or applicant documents.

## 9. Verification and implementation order

1. Agree the document-level rubric and its report semantics. Settle whether the first live demo displays a rating or just dimensions until calibration.
2. Implement extraction and preview. Test a selectable-text PDF, DOCX with tables, multi-column reading order, empty/corrupt input, and scanned/encrypted PDFs. Use authorised or explicitly synthetic fixtures, never personal documents in git.
3. Exercise a real TypeSafe request through FastAPI using the project key. Verify full context, batch questions, actual answer schema, latency, limits, and usage. No fabricated responses in live demonstrations.
4. Add deterministic report assembly and the results interface. Mocked gateway tests remain explicitly unit tests.
5. Run backend unit/integration tests, frontend typecheck/build/tests, and browser upload-to-result checks at desktop and mobile widths. Verify keyboard access, failure recovery, request privacy, and secret exclusion.
6. Evaluate findings on human-reviewed examples before assigning rating weights or publishing accuracy/cost claims.

First end-to-end acceptance: one supported CV can be uploaded, previewed, analysed with one real Jev request, and displayed with traceable question/answer details. A failed extraction or provider request never produces a made-up report.

## 10. Deferred scope

Generative suggestions and rewrites, OCR, accounts, database/history, job-link scraping, exhaustive bullet/requirement mapping, public deployment, and AI-written-text detection are deferred. The detector is a separate research idea, not a hidden resume feature.

## References

- https://docs.typesafe.ai/concepts/state.md
- https://docs.typesafe.ai/primitives/choice.md
- https://docs.typesafe.ai/confidence.md
- https://docs.typesafe.ai/llms.txt

Read current SDK/API documentation and verify actual account access before implementing the gateway. This document records a proposed design, not benchmark results or a working application.
