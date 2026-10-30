import { describe, expect, it } from 'vitest'
import { AnalysisReportSchema } from '../../src/api/schema'
import {
  combinedScores,
  contentOnlyReport,
  multiReport,
  report,
  structureOnlyReport,
  structureProviderErrorReport,
  unavailableReport,
} from './fixtures/responses'

const parse = (value: unknown) => AnalysisReportSchema.safeParse(value)

describe('score contract, synthetic fixtures only', () => {
  it('parses a combined report with both sub-scores', () => {
    const result = AnalysisReportSchema.parse(report)
    expect(result.scores).toEqual(combinedScores)
    expect(result.scores.total.mode).toBe('combined')
    expect(result.dimensions[0].owner).toBe('content')
  })

  it('parses content only and keeps the structure reason', () => {
    const result = AnalysisReportSchema.parse(contentOnlyReport)
    expect(result.scores.total.mode).toBe('content_only')
    expect(result.scores.total.value).toBe(58)
    expect(result.scores.structure.value).toBeNull()
    expect(result.scores.structure.reason).toBe('unsupported_format')
  })

  it('parses structure only with a null content score, not a zero', () => {
    const result = AnalysisReportSchema.parse(structureOnlyReport)
    expect(result.scores.content.value).toBeNull()
    expect(result.scores.content.range).toBeNull()
    expect(result.scores.total.mode).toBe('structure_only')
  })

  it('parses an unavailable total with null values', () => {
    const result = AnalysisReportSchema.parse(unavailableReport)
    expect(result.scores.total).toEqual({ value: null, band: null, mode: 'unavailable' })
    expect(result.scores.structure.reason).toBe('page_not_readable')
  })

  it('parses a structure provider error without inventing a layout score', () => {
    const result = AnalysisReportSchema.parse(structureProviderErrorReport)
    expect(result.scores.structure.value).toBeNull()
    expect(result.scores.structure.reason).toBe('provider_error')
    expect(result.scores.total.mode).toBe('content_only')
  })

  it('accepts every nullable score field as null', () => {
    const nullScores = {
      content: { value: null, band: null, range: null, coverage: 0.2, assessed_weight: 20 },
      structure: { value: null, band: null, reason: 'insufficient_evidence', assessed_weight: 0 },
      total: { value: null, band: null, mode: 'unavailable' },
    }
    expect(parse({ ...multiReport, scores: nullScores }).success).toBe(true)
  })

  it('ignores unknown extra fields instead of failing the parse', () => {
    const extra = {
      ...multiReport,
      experiment: { synthetic: true },
      scores: {
        ...multiReport.scores,
        content: { ...multiReport.scores.content, provider_note: 'SYNTHETIC extra' },
        total: { ...multiReport.scores.total, future_mode: 'x' },
      },
      dimensions: multiReport.dimensions.map(row => ({ ...row, future_field: 1 })),
      structure_findings: multiReport.structure_findings.map(row => ({ ...row, future_field: 1 })),
    }
    const result = parse(extra)
    expect(result.success).toBe(true)
    expect(result.success && result.data.scores.content).not.toHaveProperty('provider_note')
  })

  it('keeps dimension rows and structure findings optional in the body', () => {
    const { dimensions: _d, structure_findings: _s, ...withoutLists } = multiReport
    const result = parse(withoutLists)
    expect(result.success && result.data.dimensions).toEqual([])
    expect(result.success && result.data.structure_findings).toEqual([])
  })

  it('rejects a score outside 0 to 100 and a descending range', () => {
    const tooHigh = structuredClone(multiReport)
    tooHigh.scores.total.value = 101
    expect(parse(tooHigh).success).toBe(false)

    const descending = structuredClone(multiReport)
    descending.scores.content.range = [70, 60]
    expect(parse(descending).success).toBe(false)

    const negative = structuredClone(multiReport)
    negative.scores.structure.value = -1
    expect(parse(negative).success).toBe(false)
  })

  it('rejects an unknown total mode and an unknown owner', () => {
    const mode = structuredClone(multiReport)
    Object.assign(mode.scores.total, { mode: 'blended' })
    expect(parse(mode).success).toBe(false)

    const owner = structuredClone(multiReport)
    Object.assign(owner.dimensions[0], { owner: 'layout' })
    expect(parse(owner).success).toBe(false)
  })

  it('rejects a structure finding without evidence or with bad geometry', () => {
    const noEvidence = structuredClone(multiReport)
    noEvidence.structure_findings[0].evidence = ''
    expect(parse(noEvidence).success).toBe(false)

    const inverted = structuredClone(multiReport)
    inverted.structure_findings[1].box = { top: 0.5, bottom: 0.4, left: 0.1, right: 0.9 }
    expect(parse(inverted).success).toBe(false)
  })

  it('still requires scores, so an old report is not silently accepted', () => {
    const { scores: _scores, ...old } = multiReport
    expect(parse(old).success).toBe(false)
  })
})
