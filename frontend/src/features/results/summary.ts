import type {
  AnswerCategory, Dimension, Finding, StructureFinding,
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

/* The per-finding score, defined once. A present answer earns the row's full
 * stake, an absent answer earns nothing, and the two answers that decide
 * nothing show a dash. They are never 0. */
export const FINDING_SCORE: Record<AnswerCategory, number | null> = {
  present: 100,
  absent: 0,
  not_applicable: null,
  unable_to_assess: null,
}

/* A structure check is read the same way: full marks minus the points it cost.
 * A check that could not be assessed is a dash, not a zero. */
export function structureScore(finding: StructureFinding): number | null {
  if (finding.severity === 'unassessable') return null
  return Math.min(100, Math.max(0, 100 - finding.points_lost))
}

/* Band thresholds, applied to every number on the page. Colour is the second
 * signal: the band word always sits beside the number. */
export type Band = 'good' | 'fair' | 'poor'

export function bandOf(value: number | null): Band | null {
  if (value === null) return null
  if (value >= 75) return 'good'
  if (value >= 40) return 'fair'
  return 'poor'
}

/* A number, or a dash when there is no number. Never a zero in its place. */
export const scoreText = (value: number | null) => (value === null ? '\u2014' : String(value))

/* The stake one finding carries, in points. A dimension's weight is shared
 * across the findings that sit in it, and the shares add back up to the
 * dimension. A dimension the report does not score gives no stake, so the row
 * shows none rather than an invented one. */
export function findingStakes(findings: Finding[], dimensions: Dimension[]): Map<string, number> {
  const weight = new Map<string, number>()
  for (const row of dimensions) {
    if (row.owner === 'content') weight.set(row.label, row.weight)
  }

  const groups = new Map<string, Finding[]>()
  for (const finding of findings) {
    const group = groups.get(finding.dimension)
    if (group) group.push(finding)
    else groups.set(finding.dimension, [finding])
  }

  const stakes = new Map<string, number>()
  for (const [label, group] of groups) {
    const total = weight.get(label)
    if (total === undefined) continue
    const base = Math.floor(total / group.length)
    const remainder = total - base * group.length
    group.forEach((finding, index) => {
      stakes.set(finding.question_id, base + (index < remainder ? 1 : 0))
    })
  }
  return stakes
}

/* What a row earned out of its stake. A dash answer earns a dash. */
export function earnedPoints(answer: AnswerCategory, stake: number): number | null {
  const score = FINDING_SCORE[answer]
  if (score === null) return null
  return Math.round((stake * score) / 100)
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

/* Content findings in server order, grouped by scope and dimension. The order
 * is the order the server sent them in, so the highest weighted dimension
 * stays first. A job alignment row never merges into a general one. */
export interface FindingGroup {
  key: string
  dimension: string
  scope: Finding['scope']
  findings: Finding[]
}

export function groupFindings(findings: Finding[]): FindingGroup[] {
  const groups: FindingGroup[] = []
  for (const finding of findings) {
    const key = `${finding.scope}:${finding.dimension}`
    const existing = groups.find(group => group.key === key)
    if (existing) existing.findings.push(finding)
    else groups.push({ key, dimension: finding.dimension, scope: finding.scope, findings: [finding] })
  }
  return groups
}

/* A short name for one check, taken from the server's own question id and the
 * row's dimension. The full question stays one tap away; nothing is paraphrased
 * and nothing is invented. */
export function findingLabel(dimension: string, questionId: string): string {
  const slug = questionId.toLowerCase()
  const prefix = dimension.toLowerCase().replace(/\s+/g, '[_-]')
  const tail = slug.replace(new RegExp(`^${prefix}[_-]`), '')
  const words = tail.replace(/[-_]+/g, ' ').trim()
  if (!words) return dimension
  return words.charAt(0).toUpperCase() + words.slice(1)
}
