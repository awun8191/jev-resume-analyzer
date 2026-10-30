import type {
  AnswerCategory, Dimension, Finding, ScoreMode, Scores, StructureFinding, StructureScore,
} from '../../api/schema'
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

/* Only findings with page geometry or an identifiable section get a box. A
 * section can be resolved later from the PDF text layer. */
export function boxFindings(findings: Finding[]): BoxFinding[] {
  const boxes: BoxFinding[] = []
  for (const finding of findings) {
    if (finding.page == null && !finding.section) continue
    if (finding.page != null && !finding.box && !finding.section) continue
    boxes.push({
      id: finding.question_id,
      kind: 'content',
      page: finding.page ?? null,
      box: finding.box ?? null,
      section: finding.section ?? null,
      label: finding.dimension,
      state: ANSWER_TEXT[finding.answer],
      severity: finding.severity ?? null,
    })
  }
  return boxes
}

export const percent = (n: number) => `${(n * 100).toFixed(1)}%`

export const SEVERITY_TEXT: Record<StructureFinding['severity'], string> = {
  pass: 'Pass',
  minor: 'Minor issue',
  major: 'Major issue',
  unassessable: 'Unable to assess',
}

/* Structure checks carry their own page, and sometimes a box. A pass has no
 * location, so it never reaches the overlay. A check with a page and no box
 * keeps the page index and lets the pane outline the whole page. */
export function structureBoxes(findings: StructureFinding[]): BoxFinding[] {
  const boxes: BoxFinding[] = []
  for (const finding of findings) {
    if (finding.severity === 'pass' || finding.page == null) continue
    boxes.push({
      id: `structure:${finding.id}`,
      kind: 'structure',
      page: finding.page,
      box: finding.box ?? null,
      section: null,
      label: finding.label,
      state: SEVERITY_TEXT[finding.severity],
      severity: finding.severity,
    })
  }
  return boxes
}

/* API dimension rows, split by the score that owns them. Order is kept as the
 * server sent it. A row with a null value is shown as not scored. */
export function groupDimensions(rows: Dimension[]): { content: Dimension[]; structure: Dimension[] } {
  return {
    content: rows.filter(row => row.owner === 'content'),
    structure: rows.filter(row => row.owner === 'structure'),
  }
}

/* Total mode labels. The label is part of the score, not a caption. */
export const MODE_LABEL: Record<ScoreMode, string> = {
  combined: 'Content and layout',
  content_only: 'Content only',
  structure_only: 'Layout only',
  unavailable: 'Not scored',
}

const MODE_NOTE: Record<ScoreMode, string> = {
  combined: 'Weighted 70% content and 30% layout.',
  content_only: 'The total is the content score. Layout did not contribute.',
  structure_only: 'The total is the layout score. Content coverage was too thin to score.',
  unavailable: 'Neither content nor layout produced a score.',
}

export function modeNote(mode: ScoreMode): string {
  return MODE_NOTE[mode]
}

/* Known reasons get a plain sentence. An unknown reason still says the layout
 * was not scored, and the raw code stays visible next to it. */
const STRUCTURE_REASON: Record<string, string> = {
  unsupported_format: 'Layout is scored for PDF uploads only.',
  provider_error: 'Layout check failed, content review is complete.',
  render_failed: 'The layout check could not render the pages.',
  page_not_readable: 'The layout check could not read the pages.',
  page_empty: 'The pages held no text for the layout check.',
  insufficient_evidence: 'Too little of the layout could be checked to score it.',
  no_file: 'No PDF was sent, so layout was not checked.',
}

export function structureReasonText(structure: StructureScore): string | null {
  if (structure.value !== null) return null
  if (!structure.reason) return 'Layout was not scored, and no reason was reported.'
  return STRUCTURE_REASON[structure.reason] ?? 'Layout was not scored for this document.'
}

/* A content score needs at least half of the prepared weight decided. Below
 * that the value is null, so the report says how much could be decided. */
export function contentReasonText(scores: Scores): string | null {
  if (scores.content.value !== null) return null
  return `Only ${scores.content.assessed_weight} of 100 content points could be decided.`
}

/* The total carries a range only when the total is the content value itself. */
export function totalRange(scores: Scores): [number, number] | null {
  if (scores.total.mode !== 'content_only') return null
  return scores.content.range
}

export function rangeText(range: [number, number]): string {
  return `${range[0]} to ${range[1]}`
}

export function coverageText(scores: Scores): string {
  return `${Math.round(scores.content.coverage * 100)}% of prepared content weight`
}
