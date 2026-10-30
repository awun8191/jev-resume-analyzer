# Frontend implementation plan

Binding direction: Swiss / International Typographic Style. A 12 column grid, one neo-grotesque family (self-hosted Inter), six type sizes, hairline rules, tabular numerals, a monochrome palette with one red accent. Product UI, not a landing page. Source: docs/architecture.md and the current design brief.

Design read: an applicant checks extracted text, then reads findings next to the document page. The page is a workspace, not a funnel: after upload the document stays on the left while the text or the report sits on the right. Low decoration, low motion, medium information density. 44px minimum actions, native disclosures, no colour-only state.

1. Define runtime-validated API schemas and document the exact backend contract, including optional page and box geometry.
2. Build the upload stage, the editable preview, the report pane and the document pane with a box overlay. No mock success in application.
3. Persist the session in sessionStorage under one versioned key; never store file bytes; clear on reset and on a new upload.
4. Preserve both text inputs across failures, invalidate reports when returning to editing, guard in-flight requests, clear state on reset.
5. Verify schema/client/component tests, typecheck, build, browser keyboard/upload/box-selection/error paths and responsive layout. Fixtures only in tests.

Out of scope in this branch: PDF rasterisation. `src/features/document/previewSource.ts` is the seam for it; until then the pane states plainly that no page preview is available.
