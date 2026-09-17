import { describe, it, expect } from 'vitest'
import { AnalysisReportSchema, AnalysisRequestSchema, ExtractionSchema, ErrorEnvelopeSchema } from '../../src/api/schema'
import { report, extraction, providerError } from './fixtures/responses'
describe('binding contract, synthetic fixtures only', () => {
  it('accepts extraction, review, nullable report and errors', () => {
    expect(ExtractionSchema.parse(extraction)).toEqual(extraction)
    expect(ErrorEnvelopeSchema.parse(providerError)).toEqual(providerError)
    expect(AnalysisReportSchema.parse(report)).toEqual(report)
    expect(AnalysisRequestSchema.parse({ cv_text: ' test ', mode: 'review' }).cv_text).toBe('test')
  })
  it('accepts DOCX and all optional nulls', () => {
    expect(ExtractionSchema.parse({ ...extraction, page_count: null, source_format: 'docx' }).page_count).toBeNull()
    const r = structuredClone(report); r.metrics = null; r.findings[0].confidence = null; r.findings[0].probabilities = null
    expect(AnalysisReportSchema.safeParse(r).success).toBe(true)
  })
  it('accepts honest partial and empty results', () => {
    const r = { ...report, findings: [], overview: { questions_total: 1, questions_answered: 0, questions_assessable: 0, rating: null }, warnings: [{ code: 'partial_response', message: 'Question missing' }] }
    expect(AnalysisReportSchema.safeParse(r).success).toBe(true)
  })
  it.each(['empty text', 'alignment mode', 'empty posting'])('rejects invalid request: %s', key => {
    const requests = { 'empty text': { cv_text: '  ', mode: 'review' }, 'alignment mode': { cv_text: 'x', mode: 'alignment_only' }, 'empty posting': { cv_text: 'x', job_text: ' ', mode: 'review' } }
    expect(AnalysisRequestSchema.safeParse(requests[key as keyof typeof requests]).success).toBe(false)
  })
  it.each(['coverage', 'duplicate', 'probabilities', 'scope', 'rating', 'partial', 'cost'])('rejects inconsistent %s', key => {
    const r = structuredClone(report)
    if (key === 'coverage') r.overview.questions_answered = 3
    if (key === 'duplicate') { r.findings.push(r.findings[0]); r.overview = { ...r.overview, questions_total: 2, questions_answered: 2, questions_assessable: 2 } }
    if (key === 'probabilities') r.findings[0].probabilities!.present = 0.95
    if (key === 'scope') Object.assign(r.findings[0], { assessment_level: 'bullet' })
    if (key === 'rating') r.overview.rating = { value: 6, scale_min: 1, scale_max: 5, label: 'test', basis: 'test' }
    if (key === 'partial') r.overview.questions_total = 2
    if (key === 'cost') r.metrics!.cost_usd = -1
    expect(AnalysisReportSchema.safeParse(r).success).toBe(false)
  })
})
