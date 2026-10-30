import { expect, it } from 'vitest'
import {
  ANSWER_ORDER, boxFindings, countsText, findingLabel, groupDimensions, groupFindings, percent,
  rangeText, structureBoxes, structureReasonText, topFixes,
} from '../src/features/results/summary'
import { multiReport } from './contract/fixtures/responses'

it('splits API dimension rows by owner without reordering them', () => {
  const groups = groupDimensions(multiReport.dimensions)
  expect(groups.content.map(row => row.key)).toEqual(['work_clarity', 'scope', 'responsibility_alignment'])
  expect(groups.structure.map(row => row.key)).toEqual(['layout_order', 'page_budget'])
  expect([...groups.content, ...groups.structure]).toHaveLength(multiReport.dimensions.length)
})

it('returns empty groups for no rows', () => {
  expect(groupDimensions([])).toEqual({ content: [], structure: [] })
})

it('keeps a fixed answer order and formats probabilities to one decimal', () => {
  expect(ANSWER_ORDER).toEqual(['present', 'absent', 'not_applicable', 'unable_to_assess'])
  expect(percent(0.7)).toBe('70.0%')
  expect(percent(0)).toBe('0.0%')
  expect(percent(1)).toBe('100.0%')
})

it('only turns findings with real page geometry into boxes', () => {
  const boxes = boxFindings(multiReport.findings)
  expect(boxes.map(box => box.id)).toEqual(['q-clarity', 'q-ownership', 'q-align'])
  expect(boxes.map(box => box.page)).toEqual([0, 0, 1])
  expect(boxes[1].severity).toBe('high')
  expect(boxes[0].box.right).toBe(0.92)
  expect(boxes[0].kind).toBe('content')
  expect(boxes[0].state).toBe('Present')
})

it('keeps a finding that only names a section, for the layout to place', () => {
  const base = multiReport.findings[0]
  const boxes = boxFindings([{ ...base, page: null, box: null, section: 'Experience' }])
  expect(boxes).toHaveLength(1)
  expect(boxes[0]).toMatchObject({ id: base.question_id, page: null, box: null, section: 'Experience' })
})

it('turns only located, non-pass structure checks into boxes', () => {
  const boxes = structureBoxes(multiReport.structure_findings)
  expect(boxes.map(box => box.id)).toEqual(['structure:dense-columns', 'structure:no-page-break'])
  expect(boxes.map(box => box.page)).toEqual([0, 1])
  expect(boxes[0].box).toEqual({ top: 0.3, bottom: 0.46, left: 0.52, right: 0.94 })
  expect(boxes[0].state).toBe('Major issue')
  // A page with no box stays drawable, with no invented rectangle.
  expect(boxes[1].box).toBeNull()
  expect(boxes.some(box => box.severity === 'pass')).toBe(false)
})

it('names a check from the server question id, never from its prose', () => {
  expect(findingLabel('Impact', 'impact_outcome')).toBe('Outcome')
  expect(findingLabel('Scope', 'scope_stated')).toBe('Stated')
  expect(findingLabel('Clarity', 'clarity-action')).toBe('Action')
  // An id that does not follow the dimension prefix keeps all of its words.
  expect(findingLabel('Impact', 'multi_page_bullets')).toBe('Multi page bullets')
  expect(findingLabel('Impact', 'impact')).toBe('Impact')
})

it('groups findings by scope and dimension and keeps server order', () => {
  const groups = groupFindings(multiReport.findings)
  expect(groups.map(group => group.key)).toEqual([
    'general_review:Work clarity',
    'general_review:Scope',
    'job_alignment:Responsibility alignment',
  ])
  expect(groups.map(group => group.findings.length)).toEqual([2, 1, 1])
})

it('takes only the absent answers as fixes, in server order', () => {
  expect(topFixes(multiReport.findings).map(finding => finding.question_id)).toEqual(['q-ownership'])
  expect(topFixes(multiReport.findings, 1)).toHaveLength(1)
  expect(topFixes([])).toEqual([])
})

it('counts prepared, returned and assessable without inventing a total', () => {
  expect(countsText({ questions_total: 5, questions_answered: 4, questions_assessable: 2, rating: null }))
    .toBe('5 prepared · 4 returned · 2 assessable · 1 not returned')
  expect(countsText({ questions_total: 3, questions_answered: 3, questions_assessable: 3, rating: null }))
    .toBe('3 prepared · 3 returned · 3 assessable')
})

it('prints a range as one value when both ends match', () => {
  expect(rangeText([46, 69])).toBe('46 to 69')
  expect(rangeText([91, 91])).toBe('91')
})

it('maps each reported structure reason to one plain sentence', () => {
  const reason = (code: string | null) =>
    structureReasonText({ value: null, band: null, reason: code, assessed_weight: 0 })

  expect(reason('unsupported_format')).toBe('Layout is scored for PDF uploads only.')
  expect(reason('provider_error')).toBe('Layout check failed, content review is complete.')
  expect(reason('render_failed')).toBe('The layout check could not render the pages.')
  expect(reason('page_not_readable')).toBe('The layout check could not read the pages.')
  expect(reason(null)).toContain('no reason was reported')
  expect(reason('something_new')).toBe('Layout was not scored for this document.')
  expect(structureReasonText({ value: 80, band: 'Strong evidence', reason: 'scored', assessed_weight: 100 }))
    .toBeNull()
})
