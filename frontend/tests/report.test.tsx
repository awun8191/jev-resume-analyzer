import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import ReportSummary from '../src/features/results/ReportSummary'
import ResultStage from '../src/features/results/ResultStage'
import type { AnalysisReport } from '../src/api/schema'
import {
  contentOnlyReport,
  multiReport,
  report,
  unavailableReport,
} from './contract/fixtures/responses'

const noop = () => {}

/* The report is two blocks in the app: the summary sits above the document
 * pane on a phone, the body sits below it. Tests render them together. */
function show(subject: AnalysisReport = multiReport, selectedId: string | null = null, onSelect = noop) {
  return render(
    <>
      <ReportSummary report={subject} onStartOver={noop} />
      <ResultStage report={subject} onEdit={noop} selectedId={selectedId} onSelect={onSelect} />
    </>,
  )
}

const total = (container: HTMLElement) => container.querySelector('.score__total') as HTMLElement
const halves = (container: HTMLElement) => [...container.querySelectorAll('.score__half')]

it('shows the total as one numeral, a small unit and the band word', () => {
  const { container } = show()
  const line = total(container)
  expect(line.textContent).toBe('65/100Adequate evidence')
  expect(line.querySelector('.score__value')!.textContent).toBe('65')
  expect(line.querySelector('.score__value')!.getAttribute('data-band')).toBe('fair')
  expect(line.querySelector('.score__unit')!.textContent).toBe('/100')
})

it('puts structure first and content second under the total', () => {
  const { container } = show()
  const cells = halves(container)
  expect(cells.map(cell => cell.getAttribute('data-owner'))).toEqual(['structure', 'content'])
  expect(cells[0].textContent).toContain('81')
  expect(cells[0].textContent).toContain('Strong evidence')
  expect(cells[0].querySelector('.score__value')!.getAttribute('data-band')).toBe('good')
  expect(cells[1].textContent).toContain('58')
  expect(cells[1].textContent).toContain('Partial evidence')
})

it('keeps the score to the numbers alone: no coverage, weight or counts', () => {
  const { container } = show()
  const block = container.querySelector('.score') as HTMLElement
  const text = block.textContent!
  expect(text).not.toContain('Covered')
  expect(text).not.toContain('Decided')
  expect(text).not.toContain('Layout')
  expect(text).not.toContain('prepared')
  expect(text).not.toContain('assessable')
  expect(text).not.toContain('Range')
  expect(block.querySelectorAll('dt')).toHaveLength(2)
  expect(block.querySelectorAll('dd')).toHaveLength(2)
})

it('shows a null total as the words Not scored, in ink, with no number', () => {
  const { container } = show(unavailableReport)
  const line = total(container)
  expect(line.textContent).toBe('Not scored')
  expect(line.querySelector('.score__value')).toBeNull()
  expect(line.querySelector('.score__none')!.getAttribute('data-band')).toBeNull()
  expect(line.textContent).not.toContain('0')
  const cells = halves(container).map(cell => cell.textContent ?? '')
  expect(cells[0]).toContain('StructureNot scored')
  expect(cells[1]).toContain('ContentNot scored')
})

it('keeps a scored half when the other could not be scored', () => {
  const { container } = show(contentOnlyReport)
  expect(total(container).textContent).toBe('58/100Partial evidence')
  const cells = halves(container)
  expect(cells[0].textContent).toContain('StructureNot scored')
  expect(cells[1].textContent).toBe('Content58/100Partial evidence')
})

it('lists every content finding, grouped by dimension, with no show all control', () => {
  const { container } = show()
  const rows = [...container.querySelectorAll('.frow')]
  expect(rows).toHaveLength(4)
  expect([...container.querySelectorAll('.group__title')].map(node => node.textContent)).toEqual([
    'Work clarity',
    'Scope',
    'Responsibility alignmentJob posting',
  ])
  expect(screen.queryByRole('button', { name: /Show all/ })).toBeNull()
})

it('gives every row its own score and its own stake in points', () => {
  const { container } = show()
  const rows = [...container.querySelectorAll('.frow')] as HTMLElement[]
  expect(rows.map(row => row.querySelector('.frow__score')!.textContent)).toEqual([
    '100', '0', '\u2014', '\u2014',
  ])
  expect(rows.map(row => row.querySelector('.frow__stake')!.textContent)).toEqual([
    '20 of 20 pts',
    '0 of 20 pts',
    '\u2014 of 25 pts',
    '\u2014 of 35 pts',
  ])
  expect(rows.map(row => row.querySelector('.frow__state')!.textContent)).toEqual([
    'Present', 'Absent', 'Not applicable', 'Unable to assess',
  ])
  expect(rows[0].querySelector('.frow__score')!.getAttribute('data-band')).toBe('good')
  expect(rows[1].querySelector('.frow__score')!.getAttribute('data-band')).toBe('poor')
  // A dash is a dash: no zero stands in for an undecided answer.
  expect(rows[2].querySelector('.frow__score')!.getAttribute('data-band')).toBeNull()
})

it('opens one row in place to its question, criteria, answer and probabilities', async () => {
  const user = userEvent.setup()
  const { container } = show()
  const first = container.querySelector('.frow') as HTMLElement
  const row = within(first).getByRole('button')
  const detail = first.querySelector('.fdetail') as HTMLElement

  expect(row.getAttribute('aria-expanded')).toBe('false')
  expect(row.getAttribute('aria-controls')).toBe(detail.id)
  expect(detail.hasAttribute('hidden')).toBe(true)

  await user.click(row)
  expect(row.getAttribute('aria-expanded')).toBe('true')
  expect(detail.hasAttribute('hidden')).toBe(false)
  expect(detail.textContent).toContain('SYNTHETIC: is the work described clearly?')
  expect(detail.textContent).toContain('SYNTHETIC criterion A.')
  expect(detail.textContent).toContain('SYNTHETIC criterion B.')
  expect(detail.textContent).toContain('Present')
  expect(detail.textContent).toContain('62.0%')
  // Four facts, nothing else.
  expect([...detail.querySelectorAll('.label')].map(node => node.textContent)).toEqual([
    'Question', 'Criteria', 'Answer', 'Probability per answer',
  ])

  await user.click(row)
  expect(detail.hasAttribute('hidden')).toBe(true)
})

it('keeps a missing distribution explicit', async () => {
  const user = userEvent.setup()
  const { container } = show()
  const rows = [...container.querySelectorAll('.frow')] as HTMLElement[]
  await user.click(within(rows[3]).getByRole('button'))
  expect(rows[3].querySelector('.fdetail')!.textContent).toContain('Not reported by the provider.')
  expect(rows[3].querySelector('.dist')).toBeNull()
})

it('selects a finding from its row and keeps the whole list reachable', async () => {
  const user = userEvent.setup()
  const onSelect = vi.fn()
  const { container } = show(multiReport, null, onSelect)

  await user.click(within(container.querySelector('.frow') as HTMLElement).getByRole('button'))
  expect(onSelect).toHaveBeenCalledWith('q-clarity')
})

it('marks the finding that the document pane selected', () => {
  const { container } = show(multiReport, 'q-clarity')
  const first = container.querySelector('.frow') as HTMLElement
  expect(first.getAttribute('data-selected')).toBe('true')
  expect(within(first).getByRole('button').getAttribute('aria-current')).toBe('true')
})

it('shows structure findings without a disclosure: severity, points, page, score', () => {
  const { container } = show()
  expect(screen.queryByRole('button', { name: /Structure findings/ })).toBeNull()

  const rows = [...container.querySelectorAll('.srow')] as HTMLElement[]
  expect(rows).toHaveLength(4)
  expect(rows.map(row => row.querySelector('.srow__name')!.textContent)).toEqual([
    'Section order follows the rubric',
    'Two column layout is dense',
    'Section breaks across pages',
    'Font sizes are inconsistent',
  ])
  expect(rows.map(row => row.querySelector('.srow__score')!.textContent)).toEqual([
    '100', '88', '96', '\u2014',
  ])
  expect(rows[0].textContent).toContain('Pass')
  expect(rows[0].textContent).toContain('No points lost')
  expect(rows[1].textContent).toContain('Major issue')
  expect(rows[1].textContent).toContain('12 points lost')
  expect(rows[1].textContent).toContain('Page 1')
  expect(rows[1].querySelector('.srow__score')!.getAttribute('data-band')).toBe('good')
  expect(rows[3].querySelector('.srow__score')!.getAttribute('data-band')).toBeNull()
})

it('selects a located structure check and leaves a pass alone', async () => {
  const user = userEvent.setup()
  const onSelect = vi.fn()
  const { container } = show(multiReport, null, onSelect)
  const rows = [...container.querySelectorAll('.srow')] as HTMLElement[]

  expect(within(rows[0]).queryByRole('button')).toBeNull()
  await user.click(within(rows[1]).getByRole('button'))
  expect(onSelect).toHaveBeenCalledWith('structure:dense-columns')
})

it('says when a section came back empty instead of hiding it', () => {
  show(contentOnlyReport)
  expect(screen.getByText('No structure checks were returned for this report.')).toBeTruthy()
  expect(screen.getByRole('heading', { name: 'Structure findings' })).toBeTruthy()
})

it('says fewer findings when none were returned', () => {
  show({ ...multiReport, findings: [] })
  expect(screen.getByText('No findings were returned.')).toBeTruthy()
})

/* Everything the last pass carried that hid the report or padded it. */
it('keeps the removed sections and helper sentences out', () => {
  const { container } = show()
  const text = container.textContent!
  for (const gone of [
    'Covered', 'Decided', 'Layout', 'Top fixes', 'All dimensions',
    'Analysis limitations', 'Request details', 'Rubric explanation',
    'Provider confidence', 'Jump to finding', 'Show all',
  ]) {
    expect(text).not.toContain(gone)
  }
  expect(container.querySelectorAll('details')).toHaveLength(0)
  expect(container.querySelectorAll('[aria-expanded="true"]')).toHaveLength(0)
})

it('renders the two sections in reading order', () => {
  const { container } = show()
  const headings = [...container.querySelectorAll('h2')].map(node => node.textContent)
  expect(headings).toEqual(['Content findings', 'Structure findings'])
})

it('names the score region for assistive tech', () => {
  show(report)
  expect(screen.getByRole('region', { name: 'Score' })).toBeTruthy()
})
