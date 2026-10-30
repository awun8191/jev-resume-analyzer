import { z } from 'zod'
import { EvidenceSchema } from './evidence'

// Binding frontend contract, documented in docs/frontend-contract.md.
const text = z.string().min(1)
const count = z.number().int().nonnegative()
const probability = z.number().finite().min(0).max(1)
export const WarningSchema = z.object({ code: text, message: text })
export const HealthSchema = z.object({ status: z.literal('ok') })
export const ErrorEnvelopeSchema = z.object({
  error: z.object({ code: text, message: text, retryable: z.boolean() }),
  request_id: text.nullable(),
})
export const ExtractionSchema = z.object({
  document_evidence: EvidenceSchema.nullable().optional(),
  text: z.string(), page_count: z.number().int().positive().nullable(),
  warnings: z.array(WarningSchema), source_format: z.enum(['pdf', 'docx']),
})
export const AnalysisRequestSchema = z.object({
  document_evidence: EvidenceSchema.optional(),
  cv_text: z.string().trim().min(1),
  job_text: z.string().trim().min(1).optional(), mode: z.literal('review'),
}).strict()
export const AnswerCategorySchema = z.enum(['present', 'absent', 'not_applicable', 'unable_to_assess'])
// Page geometry arrives as fractions of page width and height, page index is 0-based.
const fraction = z.number().finite().min(0).max(1)
export const FindingBoxSchema = z
  .object({ top: fraction, bottom: fraction, left: fraction, right: fraction })
  .refine(box => box.bottom > box.top, 'Box bottom must sit below its top')
  .refine(box => box.right > box.left, 'Box right must sit right of its left')
export const DistributionSchema = z.object({
  present: probability, absent: probability,
  not_applicable: probability, unable_to_assess: probability,
}).refine(d => Math.abs(Object.values(d).reduce((a, b) => a + b, 0) - 1) <= 0.001,
  'Probabilities must sum to 1 (tolerance 0.001)')
export const FindingSchema = z.object({
  question_id: text, dimension: text,
  scope: z.enum(['general_review', 'job_alignment']),
  assessment_level: z.enum(['full_document', 'bullet']), question: text,
  source_text: z.string().nullable().optional(),
  source: z.enum(['provider', 'document_metadata']).optional(),
  criteria: z.array(text).min(1), answer: AnswerCategorySchema,
  probabilities: DistributionSchema.nullable(), confidence: probability.nullable(),
  rubric_explanation: z.object({ kind: z.literal('rubric'), template_ref: text, text }).nullable(),
  // Page location is optional: the backend does not send it yet. A finding
  // without a location still renders, it just has nothing to highlight.
  page: z.number().int().nonnegative().nullable().optional(),
  box: FindingBoxSchema.nullable().optional(),
  // Section key from the provider, matched to a layout span on the page.
  section: z.string().min(1).nullable().optional(),
  severity: z.string().min(1).nullable().optional(),
})
export const RatingSchema = z.object({
  value: z.number().finite(), scale_min: z.number().finite(), scale_max: z.number().finite(),
  label: text, basis: text,
}).refine(r => r.scale_min < r.scale_max && r.value >= r.scale_min && r.value <= r.scale_max,
  'Rating must be within an ordered scale')
export const OverviewSchema = z.object({
  questions_total: count, questions_answered: count, questions_assessable: count,
  rating: RatingSchema.nullable(),
}).refine(o => o.questions_assessable <= o.questions_answered && o.questions_answered <= o.questions_total,
  'Coverage counts must be ordered')
export const MetricsSchema = z.object({
  duration_ms: z.number().finite().nonnegative().nullable(),
  input_tokens: count.nullable(), output_tokens: count.nullable(),
  cost_usd: z.number().finite().nonnegative().nullable(),
})
// Every score is an integer 0..100 or null. Null means not scored, never zero.
const scoreValue = z.number().int().min(0).max(100).nullable()
const band = z.string().min(1).nullable()
export const ContentScoreSchema = z.object({
  value: scoreValue, band, coverage: z.number().finite().min(0).max(1),
  assessed_weight: z.number().int().min(0).max(100),
  range: z.tuple([z.number().int().min(0).max(100), z.number().int().min(0).max(100)])
    .refine(([low, high]) => low <= high, 'Score range must be ordered').nullable(),
})
export const StructureScoreSchema = z.object({
  value: scoreValue, band, reason: z.string().min(1).nullable(),
  assessed_weight: z.number().int().min(0).max(100),
})
export const TotalScoreSchema = z.object({
  value: scoreValue, band,
  mode: z.enum(['combined', 'content_only', 'structure_only', 'unavailable']),
})
export const ScoresSchema = z.object({
  content: ContentScoreSchema, structure: StructureScoreSchema, total: TotalScoreSchema,
})
export const DimensionSchema = z.object({
  key: text, label: text, owner: z.enum(['content', 'structure']),
  weight: z.number().int().min(0).max(100), value: scoreValue,
  section: z.string().min(1).nullable().optional(),
})
export const StructureFindingSchema = z.object({
  id: text, label: text, severity: z.enum(['pass', 'minor', 'major', 'unassessable']),
  points_lost: z.number().int().min(0).max(100),
  page: z.number().int().nonnegative().nullable().optional(),
  box: FindingBoxSchema.nullable().optional(),
  confidence: probability.nullable(), evidence: text,
})
export const AnalysisReportSchema = z.object({
  analysis_id: text, rubric_version: text, model: text,
  findings: z.array(FindingSchema), overview: OverviewSchema,
  warnings: z.array(WarningSchema), metrics: MetricsSchema.nullable(),
  scores: ScoresSchema, dimensions: z.array(DimensionSchema).default([]),
  structure_findings: z.array(StructureFindingSchema).default([]),
}).superRefine((r, ctx) => {
  for (const f of r.findings) {
    if (f.assessment_level === 'bullet' && !f.source_text?.trim())
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: 'Bullet findings need source text' })
    if (f.box && f.page == null)
      ctx.addIssue({ code: z.ZodIssueCode.custom, message: 'A box needs a page index' })
  }
  const assessable = r.findings.filter(f => f.answer === 'present' || f.answer === 'absent').length
  if (r.overview.questions_answered !== r.findings.length || r.overview.questions_assessable !== assessable)
    ctx.addIssue({ code: z.ZodIssueCode.custom, message: 'Coverage must match returned findings' })
  if (new Set(r.findings.map(f => f.question_id)).size !== r.findings.length)
    ctx.addIssue({ code: z.ZodIssueCode.custom, message: 'Question IDs must be unique' })
  if (r.overview.questions_answered < r.overview.questions_total && !r.warnings.some(w => w.code === 'partial_response'))
    ctx.addIssue({ code: z.ZodIssueCode.custom, message: 'Incomplete reports need partial_response warning' })
  if (r.overview.rating !== null && assessable === 0)
    ctx.addIssue({ code: z.ZodIssueCode.custom, message: 'Unassessable reports cannot have a rating' })
})
export type AnalysisRequest = z.infer<typeof AnalysisRequestSchema>
export type AnalysisReport = z.infer<typeof AnalysisReportSchema>
export type Finding = z.infer<typeof FindingSchema>
export type FindingBox = z.infer<typeof FindingBoxSchema>
export type AnswerCategory = z.infer<typeof AnswerCategorySchema>
export type Extraction = z.infer<typeof ExtractionSchema>
export type Health = z.infer<typeof HealthSchema>
export type Warning = z.infer<typeof WarningSchema>
export type Scores = z.infer<typeof ScoresSchema>
export type ContentScore = z.infer<typeof ContentScoreSchema>
export type StructureScore = z.infer<typeof StructureScoreSchema>
export type TotalScore = z.infer<typeof TotalScoreSchema>
export type ScoreMode = TotalScore['mode']
export type Dimension = z.infer<typeof DimensionSchema>
export type StructureFinding = z.infer<typeof StructureFindingSchema>
