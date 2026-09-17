import { z } from 'zod'

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
  text: z.string(), page_count: z.number().int().positive().nullable(),
  warnings: z.array(WarningSchema), source_format: z.enum(['pdf', 'docx']),
})
export const AnalysisRequestSchema = z.object({
  cv_text: z.string().trim().min(1),
  job_text: z.string().trim().min(1).optional(), mode: z.literal('review'),
}).strict()
export const AnswerCategorySchema = z.enum(['present', 'absent', 'not_applicable', 'unable_to_assess'])
export const DistributionSchema = z.object({
  present: probability, absent: probability,
  not_applicable: probability, unable_to_assess: probability,
}).refine(d => Math.abs(Object.values(d).reduce((a, b) => a + b, 0) - 1) <= 0.001,
  'Probabilities must sum to 1 (tolerance 0.001)')
export const FindingSchema = z.object({
  question_id: text, dimension: text,
  scope: z.enum(['general_review', 'job_alignment']),
  assessment_level: z.literal('full_document'), question: text,
  criteria: z.array(text).min(1), answer: AnswerCategorySchema,
  probabilities: DistributionSchema.nullable(), confidence: probability.nullable(),
  rubric_explanation: z.object({ kind: z.literal('rubric'), template_ref: text, text }).nullable(),
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
export const AnalysisReportSchema = z.object({
  analysis_id: text, rubric_version: text, model: text,
  findings: z.array(FindingSchema), overview: OverviewSchema,
  warnings: z.array(WarningSchema), metrics: MetricsSchema.nullable(),
}).superRefine((r, ctx) => {
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
export type AnswerCategory = z.infer<typeof AnswerCategorySchema>
export type Extraction = z.infer<typeof ExtractionSchema>
export type Health = z.infer<typeof HealthSchema>
export type Warning = z.infer<typeof WarningSchema>
