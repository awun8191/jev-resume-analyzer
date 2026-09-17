# Frontend implementation plan

Binding direction: white surfaces, thin grey borders, restrained blue actions. Product UI, not a landing page. Source: docs/architecture.md and task t_49e21db0. No stored product tokens found in fact_store.

Design read: an applicant checks extracted text before sending it to TypeSafe. Prioritise legibility, honest limitations and recoverable actions. Dials: low decoration, low motion, medium information density. Bricolage headings, Hanken body, small mono identifiers. Single centred column, 720px reading width, 24px mobile gutters, 44px minimum actions, native disclosure controls.

1. Define runtime-validated API schemas and document exact backend contract.
2. Implement native file input plus drag/drop, editable preview, optional posting, full-document report details. No mock success in application.
3. Preserve both text inputs across failures, invalidate reports when returning to editing, guard in-flight requests, clear state on reset.
4. Verify schema/client/component tests, typecheck, build, browser keyboard/upload/error paths and responsive layout. Fixtures only in tests.

Primary taste skills unavailable in profile. Fallback: frontend-design and design-skills-pipeline, mobile-app-ui-design, mobile-interaction-patterns, css-theme-engineering. No backend or architecture edits, no Git setup, no deployment.
