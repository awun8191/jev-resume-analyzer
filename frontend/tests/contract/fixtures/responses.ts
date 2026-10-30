import type { AnalysisReport, Extraction, Scores } from '../../../src/api/schema'
// SYNTHETIC TEST FIXTURES ONLY. Not provider outputs or real applicant data.

export const extraction: Extraction = {
  text: 'SYNTHETIC TEST CV\nExample project: documented a test workflow.',
  page_count: 1, source_format: 'pdf',
  warnings: [{ code: 'partial_text', message: 'SYNTHETIC extraction warning: check reading order.' }],
}

/* One score block per total mode. The numbers are round at 70/30 so a test can
 * check the label without re-deriving the weighting. */
export const combinedScores: Scores = {
  content: { value: 72, band: 'Adequate evidence', range: [64, 80], coverage: 0.86, assessed_weight: 86 },
  structure: { value: 68, band: 'Partial evidence', reason: 'scored', assessed_weight: 100 },
  total: { value: 71, band: 'Adequate evidence', mode: 'combined' },
}

export const report: AnalysisReport = {
  analysis_id: 'synthetic-test-request', rubric_version: 'synthetic-test-rubric', model: 'synthetic-test-model',
  findings: [{ question_id: 'test-clarity', dimension: 'Work clarity', scope: 'general_review',
    assessment_level: 'full_document', question: 'SYNTHETIC TEST: Is the work described clearly across this CV?',
    criteria: ['SYNTHETIC criterion: identifiable activities across the document.'],
    answer: 'present', probabilities: { present: 0.7, absent: 0.1, not_applicable: 0.05, unable_to_assess: 0.15 },
    confidence: 0.65, rubric_explanation: { kind: 'rubric', template_ref: 'test-present', text: 'SYNTHETIC predefined rubric explanation.' },
  }],
  overview: { questions_total: 1, questions_answered: 1, questions_assessable: 1, rating: null },
  warnings: [], metrics: { duration_ms: 1234, input_tokens: 100, output_tokens: 20, cost_usd: null },
  scores: combinedScores,
  dimensions: [{ key: 'work_clarity', label: 'Work clarity', owner: 'content', weight: 100, value: 72 }],
  structure_findings: [],
}

export const providerError = { error: { code: 'PROVIDER_UNAVAILABLE', message: 'SYNTHETIC TEST provider unavailable.', retryable: true }, request_id: 'synthetic-error-id' }

// Four findings across three dimensions, one scope split, a partial response.
export const multiReport: AnalysisReport = {
  analysis_id: 'synthetic-multi-request', rubric_version: 'synthetic-test-rubric', model: 'synthetic-test-model',
  findings: [
    { question_id: 'q-clarity', dimension: 'Work clarity', scope: 'general_review',
      assessment_level: 'full_document', question: 'SYNTHETIC: is the work described clearly?',
      source_text: 'SYNTHETIC source passage one.', source: 'provider',
      criteria: ['SYNTHETIC criterion A.', 'SYNTHETIC criterion B.'], answer: 'present',
      probabilities: { present: 0.62, absent: 0.2, not_applicable: 0.08, unable_to_assess: 0.1 },
      confidence: 0.58, rubric_explanation: null,
      page: 0, box: { top: 0.12, bottom: 0.2, left: 0.08, right: 0.92 } },
    { question_id: 'q-ownership', dimension: 'Work clarity', scope: 'general_review',
      assessment_level: 'full_document', question: 'SYNTHETIC: is personal contribution identifiable?',
      criteria: ['SYNTHETIC criterion C.'], answer: 'absent',
      probabilities: { present: 0.18, absent: 0.7, not_applicable: 0.07, unable_to_assess: 0.05 },
      confidence: null, rubric_explanation: null,
      page: 0, box: { top: 0.44, bottom: 0.5, left: 0.08, right: 0.55 }, severity: 'high' },
    { question_id: 'q-scope', dimension: 'Scope', scope: 'general_review',
      assessment_level: 'full_document', question: 'SYNTHETIC: is the working scope stated?',
      criteria: ['SYNTHETIC criterion D.'], answer: 'not_applicable',
      probabilities: { present: 0.1, absent: 0.2, not_applicable: 0.6, unable_to_assess: 0.1 },
      confidence: 0.4, rubric_explanation: { kind: 'rubric', template_ref: 'synthetic-na', text: 'SYNTHETIC rubric note.' } },
    { question_id: 'q-align', dimension: 'Responsibility alignment', scope: 'job_alignment',
      assessment_level: 'full_document', question: 'SYNTHETIC: does the CV evidence the posting responsibilities?',
      criteria: ['SYNTHETIC criterion E.'], answer: 'unable_to_assess',
      probabilities: null, confidence: null, rubric_explanation: null,
      page: 1, box: { top: 0.6, bottom: 0.72, left: 0.08, right: 0.92 } },
  ],
  overview: { questions_total: 5, questions_answered: 4, questions_assessable: 2, rating: null },
  warnings: [{ code: 'partial_response', message: 'SYNTHETIC: one prepared question was not returned.' }],
  metrics: null,
  scores: {
    content: { value: 58, band: 'Partial evidence', range: [46, 69], coverage: 0.8, assessed_weight: 80 },
    structure: { value: 81, band: 'Strong evidence', reason: 'scored', assessed_weight: 100 },
    total: { value: 65, band: 'Adequate evidence', mode: 'combined' },
  },
  dimensions: [
    { key: 'work_clarity', label: 'Work clarity', owner: 'content', weight: 40, value: 55, section: 'experience' },
    { key: 'scope', label: 'Scope', owner: 'content', weight: 25, value: null },
    { key: 'responsibility_alignment', label: 'Responsibility alignment', owner: 'content', weight: 35, value: 61 },
    { key: 'layout_order', label: 'Layout order', owner: 'structure', weight: 60, value: 88 },
    { key: 'page_budget', label: 'Page budget', owner: 'structure', weight: 40, value: null },
  ],
  structure_findings: [
    { id: 'section-order', label: 'Section order follows the rubric', severity: 'pass',
      points_lost: 0, page: null, box: null, confidence: null,
      evidence: 'SYNTHETIC: headings appear in the expected order.' },
    { id: 'dense-columns', label: 'Two column layout is dense', severity: 'major',
      points_lost: 12, page: 0, box: { top: 0.3, bottom: 0.46, left: 0.52, right: 0.94 },
      confidence: 0.82, evidence: 'SYNTHETIC: column gap is below the body text size.' },
    { id: 'no-page-break', label: 'Section breaks across pages', severity: 'minor',
      points_lost: 4, page: 1, box: null, confidence: 0.61,
      evidence: 'SYNTHETIC: the experience section continues on page 2.' },
    { id: 'font-mix', label: 'Font sizes are inconsistent', severity: 'unassessable',
      points_lost: 0, page: null, box: null, confidence: null,
      evidence: 'SYNTHETIC: the page was not readable enough to compare glyph sizes.' },
  ],
}

/* Structure was not scored because the upload was not a PDF. */
export const contentOnlyReport: AnalysisReport = {
  ...multiReport,
  analysis_id: 'synthetic-content-only',
  scores: {
    content: { value: 58, band: 'Partial evidence', range: [46, 69], coverage: 0.8, assessed_weight: 80 },
    structure: { value: null, band: null, reason: 'unsupported_format', assessed_weight: 0 },
    total: { value: 58, band: 'Partial evidence', mode: 'content_only' },
  },
  dimensions: multiReport.dimensions.filter(row => row.owner === 'content'),
  structure_findings: [],
}

/* Only structure could be scored. Content coverage was too thin. */
export const structureOnlyReport: AnalysisReport = {
  ...multiReport,
  analysis_id: 'synthetic-structure-only',
  scores: {
    content: { value: null, band: null, range: null, coverage: 0.4, assessed_weight: 40 },
    structure: { value: 81, band: 'Strong evidence', reason: 'scored', assessed_weight: 100 },
    total: { value: 81, band: 'Strong evidence', mode: 'structure_only' },
  },
  dimensions: multiReport.dimensions.filter(row => row.owner === 'structure'),
}

/* Neither route produced a score. */
export const unavailableReport: AnalysisReport = {
  ...multiReport,
  analysis_id: 'synthetic-unavailable',
  scores: {
    content: { value: null, band: null, range: null, coverage: 0, assessed_weight: 0 },
    structure: { value: null, band: null, reason: 'page_not_readable', assessed_weight: 0 },
    total: { value: null, band: null, mode: 'unavailable' },
  },
  dimensions: [],
  structure_findings: [],
}

/* A combined request whose layout call failed: content is complete. */
export const structureProviderErrorReport: AnalysisReport = {
  ...multiReport,
  analysis_id: 'synthetic-structure-provider-error',
  scores: {
    content: { value: 58, band: 'Partial evidence', range: [46, 69], coverage: 0.8, assessed_weight: 80 },
    structure: { value: null, band: null, reason: 'provider_error', assessed_weight: 0 },
    total: { value: 58, band: 'Partial evidence', mode: 'content_only' },
  },
  dimensions: multiReport.dimensions.filter(row => row.owner === 'content'),
  structure_findings: [],
}
