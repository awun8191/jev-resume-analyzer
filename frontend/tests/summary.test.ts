import { expect, it } from 'vitest'
import { ANSWER_ORDER, boxFindings, dimensionRows, percent } from '../src/features/results/summary'
import { multiReport } from './contract/fixtures/responses'

it('returns nothing for no findings', () => {
  expect(dimensionRows([])).toEqual([])
})

it('groups findings by dimension and counts each answer once', () => {
  const rows = dimensionRows(multiReport.findings)
  expect(rows.map(row => row.dimension)).toEqual(['Work clarity', 'Scope', 'Responsibility alignment'])
  expect(rows[0]).toEqual({
    dimension: 'Work clarity',
    total: 2,
    counts: { present: 1, absent: 1, not_applicable: 0, unable_to_assess: 0 },
  })
  expect(rows.reduce((sum, row) => sum + row.total, 0)).toBe(multiReport.findings.length)
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
})

it('keeps a finding that only names a section, for the layout to place', () => {
  const base = multiReport.findings[0]
  const boxes = boxFindings([{ ...base, page: null, box: null, section: 'Experience' }])
  expect(boxes).toHaveLength(1)
  expect(boxes[0]).toMatchObject({ id: base.question_id, page: null, box: null, section: 'Experience' })
})
