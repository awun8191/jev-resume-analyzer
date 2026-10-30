import { expect, it } from 'vitest'
import {
  ANSWER_ORDER, FINDING_SCORE, bandOf, boxFindings, earnedPoints, findingLabel,
  findingStakes, groupFindings, percent, scoreText, structureBoxes, structureScore,
} from '../src/features/results/summary'
import { multiReport } from './contract/fixtures/responses'

it('keeps a fixed answer order and formats probabilities to one decimal', () => {
  expect(ANSWER_ORDER).toEqual(['present', 'absent', 'not_applicable', 'unable_to_assess'])
  expect(percent(0.7)).toBe('70.0%')
  expect(percent(0)).toBe('0.0%')
  expect(percent(1)).toBe('100.0%')
})

/* The per-finding score is defined in one place, and the two answers that
 * decide nothing are a dash rather than a zero. */
it('scores a finding once: present 100, absent 0, a dash for the rest', () => {
  expect(FINDING_SCORE.present).toBe(100)
  expect(FINDING_SCORE.absent).toBe(0)
  expect(FINDING_SCORE.not_applicable).toBeNull()
  expect(FINDING_SCORE.unable_to_assess).toBeNull()
  expect(scoreText(FINDING_SCORE.not_applicable)).toBe('\u2014')
  expect(scoreText(0)).toBe('0')
})

it('reads a structure check as full marks minus what it cost', () => {
  const [pass, major, , unassessable] = multiReport.structure_findings
  expect(structureScore(pass)).toBe(100)
  expect(structureScore(major)).toBe(88)
  expect(structureScore(unassessable)).toBeNull()
  expect(scoreText(structureScore(unassessable))).toBe('\u2014')
})

it('bands 75 and above green, 40 to 74 amber, below 40 red, null unbanded', () => {
  expect(bandOf(100)).toBe('good')
  expect(bandOf(75)).toBe('good')
  expect(bandOf(74)).toBe('fair')
  expect(bandOf(40)).toBe('fair')
  expect(bandOf(39)).toBe('poor')
  expect(bandOf(0)).toBe('poor')
  expect(bandOf(null)).toBeNull()
})

/* A dimension's weight is shared across its findings, so the row reads its own
 * stake and the shares add back up to the dimension. */
it('splits a dimension weight across its findings without losing a point', () => {
  const stakes = findingStakes(multiReport.findings, multiReport.dimensions)
  expect(stakes.get('q-clarity')).toBe(20)
  expect(stakes.get('q-ownership')).toBe(20)
  expect(stakes.get('q-scope')).toBe(25)
  expect(stakes.get('q-align')).toBe(35)

  const clarity = [...stakes.values()].slice(0, 2).reduce((a, b) => a + b, 0)
  expect(clarity).toBe(40)

  // A dimension the report does not score gives no stake at all.
  expect(findingStakes(multiReport.findings, []).size).toBe(0)
})

it('earns the whole stake or none of it, and a dash earns a dash', () => {
  expect(earnedPoints('present', 20)).toBe(20)
  expect(earnedPoints('absent', 20)).toBe(0)
  expect(earnedPoints('not_applicable', 20)).toBeNull()
  expect(earnedPoints('unable_to_assess', 20)).toBeNull()
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
