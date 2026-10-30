import type { AnswerCategory, Finding } from '../../api/schema'
import type { BoxFinding } from '../document/types'

/* Fixed order so counts and distributions read the same way everywhere. */
export const ANSWER_ORDER: readonly AnswerCategory[] = [
  'present',
  'absent',
  'not_applicable',
  'unable_to_assess',
]

export const ANSWER_TEXT: Record<AnswerCategory, string> = {
  present: 'Present',
  absent: 'Absent',
  not_applicable: 'Not applicable',
  unable_to_assess: 'Unable to assess',
}

/* Shape, not colour, carries the state. */
export const ANSWER_GLYPH: Record<AnswerCategory, string> = {
  present: '\u25A0',
  absent: '\u25A1',
  not_applicable: '\u2212',
  unable_to_assess: '?',
}

export interface DimensionRow {
  dimension: string
  total: number
  counts: Record<AnswerCategory, number>
}

/* Only findings with page geometry or an identifiable section get a box. A
 * section can be resolved later from the PDF text layer. */
export function boxFindings(findings: Finding[]): BoxFinding[] {
  const boxes: BoxFinding[] = []
  for (const finding of findings) {
    if (finding.page == null && !finding.section) continue
    if (finding.page != null && !finding.box && !finding.section) continue
    boxes.push({
      id: finding.question_id,
      page: finding.page ?? null,
      box: finding.box ?? null,
      section: finding.section ?? null,
      label: finding.dimension,
      answer: finding.answer,
      severity: finding.severity ?? null,
    })
  }
  return boxes
}

/* Counts returned findings per dimension. No weighting, no score. */
export function dimensionRows(findings: Finding[]): DimensionRow[] {
  const rows = new Map<string, DimensionRow>()
  for (const finding of findings) {
    let row = rows.get(finding.dimension)
    if (!row) {
      row = {
        dimension: finding.dimension,
        total: 0,
        counts: { present: 0, absent: 0, not_applicable: 0, unable_to_assess: 0 },
      }
      rows.set(finding.dimension, row)
    }
    row.counts[finding.answer] += 1
    row.total += 1
  }
  return [...rows.values()]
}

/* The report hierarchy below the overall rating. Both slots stay pending while
 * the backend sends no sub-score values. */
export const SUBSCORES = [
  { key: 'structure', label: 'Structure' },
  { key: 'content', label: 'Content' },
] as const

export const percent = (n: number) => `${(n * 100).toFixed(1)}%`
