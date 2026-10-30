import { expect, it } from 'vitest'
import { ANSWER_ORDER, boxFindings, groupDimensions, percent, structureBoxes } from '../src/features/results/summary'
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
