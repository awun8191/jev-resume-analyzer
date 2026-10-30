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
}
