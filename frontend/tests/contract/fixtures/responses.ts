import type { AnalysisReport, Extraction } from '../../../src/api/schema'
// SYNTHETIC TEST FIXTURES ONLY. Not provider outputs or real applicant data.
export const extraction: Extraction = {
  text: 'SYNTHETIC TEST CV\nExample project: documented a test workflow.',
  page_count: 1, source_format: 'pdf',
  warnings: [{ code: 'partial_text', message: 'SYNTHETIC extraction warning: check reading order.' }],
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
}
export const providerError = { error: { code: 'PROVIDER_UNAVAILABLE', message: 'SYNTHETIC TEST provider unavailable.', retryable: true }, request_id: 'synthetic-error-id' }
