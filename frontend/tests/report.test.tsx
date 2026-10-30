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
  structureOnlyReport,
  structureProviderErrorReport,
  unavailableReport,
} from './contract/fixtures/responses'

const noop = () => {}

/* The report is two blocks in the app: the summary sits above the document
 * pane on a phone, the body sits below it. Tests render them together. */
function show(subject: AnalysisReport = multiReport, selectedId: string | null = null, onSelect = noop) {
  return render(
    <>
      <ReportSummary
        report={subject}
        selectedId={selectedId}
        onSelect={onSelect}
        onStartOver={noop}
      />
      <ResultStage report={subject} onEdit={noop} selectedId={selectedId} onSelect={onSelect} />
    </>,
  )
}

it('shows the total, band, mode and coverage in one compact block', () => {
  const { container } = show()
  const block = container.querySelector('.score') as HTMLElement
  expect(block.getAttribute('data-mode')).toBe('combined')
  expect(block.querySelector('.score__value')!.textContent).toBe('65/ 100')
  expect(block.textContent).toContain('Adequate evidence')
  expect(block.textContent).not.toContain('Content and layout')
  expect(block.textContent).toContain('80%')
  expect(block.textContent).toContain('4 of 5 answered · 2 assessable · 1 not returned')
  // A combined total has no range of its own, so none is shown.
  expect(block.querySelector('.score__range')).toBeNull()
})

it('does not print the explainer sentences any more', () => {
  const { container } = show()
  const text = container.textContent!
  expect(text).not.toContain('Assessable means')
  expect(text).not.toContain('Weighted 70% content')
  expect(text).not.toContain('The evidence is consistent with any value in that range')
  expect(text).not.toContain('of prepared content weight')
  expect(text).not.toContain('Scored rows by owner')
  expect(text).not.toContain('Layout points assessed')
})

it('puts structure first and content second in the two tiles', () => {
  const { container } = show()
  const subscores = [...container.querySelectorAll('.subscore')]
  expect(subscores.map(node => node.getAttribute('data-owner'))).toEqual(['structure', 'content'])
  expect(subscores[0].textContent).toContain('81')
  expect(subscores[0].textContent).not.toContain('Strong evidence')
  expect(subscores[1].textContent).toContain('58')
  expect(subscores[1].textContent).toContain('Range 46 to 69')
})

it('labels a content only total and keeps the layout reason in place', () => {
  const { container } = show(contentOnlyReport)
  const block = container.querySelector('.score') as HTMLElement
  expect(block.getAttribute('data-mode')).toBe('content_only')
  expect(block.textContent).toContain('Content only')
  expect(block.textContent).toContain('Range 46 to 69')
  expect(block.textContent).toContain('Layout is scored for PDF uploads only.')
  expect(block.textContent).toContain('unsupported_format')

  const structure = container.querySelector('.subscore[data-owner="structure"]') as HTMLElement
  expect(structure.textContent).toContain('Not scored')
  expect(structure.querySelector('.subscore__value')).toBeNull()
  expect(structure.textContent).toContain('Layout is scored for PDF uploads only.')
})

it('says a layout check failed without hiding the content review', () => {
  const { container } = show(structureProviderErrorReport)
  const block = container.querySelector('.score') as HTMLElement
  expect(block.textContent).toContain('Layout check failed, content review is complete.')
  expect(block.textContent).toContain('58')
})

it('shows a layout only total when content could not be scored', () => {
  const { container } = show(structureOnlyReport)
  const block = container.querySelector('.score') as HTMLElement
  expect(block.getAttribute('data-mode')).toBe('structure_only')
  expect(block.textContent).toContain('Layout only')
  expect(block.textContent).toContain('Only 40 of 100 content points could be decided.')
  expect(block.querySelector('.score__range')).toBeNull()
  const content = container.querySelector('.subscore[data-owner="content"]') as HTMLElement
  expect(content.textContent).toContain('Not scored')
})

it('shows no number at all when nothing could be scored', () => {
  const { container } = show(unavailableReport)
  const block = container.querySelector('.score') as HTMLElement
  expect(block.getAttribute('data-mode')).toBe('unavailable')
  expect(block.querySelector('.score__value')).toBeNull()
  expect(block.querySelector('.score__none')!.textContent).toBe('Not scored')
  expect(block.textContent).toContain('The layout check could not read the pages.')
  expect(block.textContent).not.toMatch(/\b0\/ 100\b/)
})

it('lists the absent answers as short fix rows that select the finding', async () => {
  const user = userEvent.setup()
  const onSelect = vi.fn()
  const { container } = show(multiReport, null, onSelect)

  const fixes = [...container.querySelectorAll('.fix')]
  expect(fixes).toHaveLength(1)
  expect(fixes[0].textContent).toContain('Work clarity')
  expect(fixes[0].textContent).toContain('Page 1')

  await user.click(within(fixes[0] as HTMLElement).getByRole('button'))
  expect(onSelect).toHaveBeenCalledWith('q-ownership')
})

it('says so when no answer is absent, and keeps the jump path', () => {
  show(report)
  expect(screen.getByText('No absent answers.')).toBeTruthy()
  expect(screen.getByRole('button', { name: 'Jump to finding' })).toBeTruthy()
})

it('groups content findings by dimension with three visible', async () => {
  const user = userEvent.setup()
  const { container } = show()
  const findings = [...container.querySelectorAll('.finding')]
  expect(findings).toHaveLength(3)
  expect(container.querySelectorAll('.groups .group__title')[0].textContent).toBe('Work clarity')
  expect(container.querySelectorAll('.groups .group__title').length).toBe(2)

  const more = screen.getByRole('button', { name: 'Show all 4 findings' })
  expect(more.getAttribute('aria-expanded')).toBe('false')
  await user.click(more)
  expect(container.querySelectorAll('.finding')).toHaveLength(4)
  const titles = [...container.querySelectorAll('.groups .group__title')].map(node => node.textContent)
  expect(titles).toEqual(['Work clarity', 'Scope', 'Responsibility alignment'])
  expect(container.textContent).toContain('Job posting · 1 of 1')
  expect(screen.getByRole('button', { name: 'Show fewer findings' })).toBeTruthy()
})

it('shows every answer state as a word plus a shape', () => {
  const { container } = show()
  const states = [...container.querySelectorAll('.state')]
  expect(states.map(el => el.textContent!.trim())).toEqual([
    '\u25A0Present',
    '\u25A1Absent',
    '\u2212Not applicable',
  ])
  expect(states.map(el => el.querySelector('.state__glyph')!.textContent)).toEqual([
    '\u25A0',
    '\u25A1',
    '\u2212',
  ])
})

it('opens one finding on tap to its question, criteria, answer and distribution', async () => {
  const user = userEvent.setup()
  const { container } = show()
  const first = container.querySelector('.finding') as HTMLElement
  const row = within(first).getByRole('button')
  const detail = first.querySelector('.finding__detail') as HTMLElement
  expect(detail.hasAttribute('hidden')).toBe(true)

  await user.click(row)
  expect(row.getAttribute('aria-expanded')).toBe('true')
  expect(detail.hasAttribute('hidden')).toBe(false)
  expect(detail.textContent).toContain('SYNTHETIC: is the work described clearly?')
  expect(detail.textContent).toContain('SYNTHETIC criterion A.')
  expect(detail.textContent).toContain('SYNTHETIC criterion B.')
  expect(detail.textContent).toContain('62.0%')
  expect(detail.textContent).toContain('SYNTHETIC source passage one.')
  expect(detail.textContent).toContain('Page 1')

  await user.click(row)
  expect(detail.hasAttribute('hidden')).toBe(true)
})

it('keeps a missing distribution and confidence explicit', async () => {
  const user = userEvent.setup()
  const { container } = show(multiReport)
  await user.click(screen.getByRole('button', { name: 'Show all 4 findings' }))
  const last = [...container.querySelectorAll('.finding')].at(-1) as HTMLElement
  const row = within(last).getByRole('button')
  expect(row.getAttribute('aria-label')).toContain('Unable to assess')

  await user.click(row)
  const detail = last.querySelector('.finding__detail') as HTMLElement
  expect(detail.textContent).toContain('Not reported by the provider.')
  expect(detail.textContent).toContain('Provider confidenceNot reported')
  expect(last.querySelector('.dist')).toBeNull()
})

it('selects a finding from its row and marks the located ones', async () => {
  const user = userEvent.setup()
  const onSelect = vi.fn()
  const { container } = show(multiReport, null, onSelect)

  await user.click(screen.getAllByRole('button', { name: /^Work clarity:/ })[0])
  expect(onSelect).toHaveBeenCalledWith('q-clarity')
  expect((screen.getAllByRole('button', { name: /^Work clarity:/ })[0]).getAttribute('aria-label'))
    .toContain('Page 1')

  const rows = [...container.querySelectorAll('.finding')]
  expect(rows[0].querySelector('.finding__page')!.textContent).toBe('Page 1')
  // The not applicable finding has no page, so the slot stays empty.
  expect(rows[2].querySelector('.finding__page')!.getAttribute('data-empty')).toBe('true')
})

it('marks the selected finding in the list', () => {
  const { container } = show(multiReport, 'q-clarity')
  const first = container.querySelector('.finding') as HTMLElement
  expect(first.getAttribute('data-selected')).toBe('true')
  expect(within(first).getByRole('button').getAttribute('aria-current')).toBe('true')
})

it('keeps structure checks behind one disclosure that states the count and the score', async () => {
  const user = userEvent.setup()
  const { container } = show(multiReport)

  const toggle = screen.getByRole('button', { name: /Structure findings/ })
  expect(toggle.getAttribute('aria-expanded')).toBe('false')
  expect(toggle.textContent).toContain('4 checks · 81 / 100')
  const section = container.querySelector('#structure-body') as HTMLElement
  expect(section.hasAttribute('hidden')).toBe(true)

  await user.click(toggle)
  expect(section.hasAttribute('hidden')).toBe(false)
  const rows = [...section.querySelectorAll('.sfind')]
  expect(rows).toHaveLength(4)
  expect(rows.map(row => row.querySelector('.sfind__label')!.textContent)).toEqual([
    'Section order follows the rubric',
    'Two column layout is dense',
    'Section breaks across pages',
    'Font sizes are inconsistent',
  ])
  expect(rows[0].textContent).toContain('Pass')
  expect(rows[0].querySelector('button')).toBeNull()
  expect(rows[2].textContent).toContain('Page 2')
  expect(section.textContent).toContain('12 points lost')
  expect(section.textContent).toContain('SYNTHETIC: column gap is below the body text size.')
})

it('selects a structure check and opens its disclosure', async () => {
  const user = userEvent.setup()
  const onSelect = vi.fn()
  const { container } = show(multiReport, null, onSelect)
  await user.click(screen.getByRole('button', { name: /Structure findings/ }))
  await user.click(screen.getByRole('button', { name: 'Two column layout is dense. Major issue. Page 1.' }))
  expect(onSelect).toHaveBeenCalledWith('structure:dense-columns')
  expect(container.querySelectorAll('.sfind').length).toBeGreaterThan(0)
})

it('marks a selected structure finding and opens its group', () => {
  const { container } = show(multiReport, 'structure:dense-columns')
  const selected = container.querySelector('.sfind[data-selected="true"]') as HTMLElement
  expect(selected.querySelector('.sfind__label')!.textContent).toBe('Two column layout is dense')
  expect(selected.querySelector('button')!.getAttribute('aria-pressed')).toBe('true')
})

it('keeps an empty structure list visible instead of hiding it', () => {
  show(contentOnlyReport)
  expect(
    screen.getByText('No structure checks were returned for this report.'),
  ).toBeTruthy()
  expect(screen.getByRole('button', { name: /Structure findings/ }).textContent).toContain('Not scored')
})

it('hides dimension rows behind All dimensions and keeps a null a word', async () => {
  const user = userEvent.setup()
  const { container } = show()
  const toggle = screen.getByRole('button', { name: /All dimensions/ })
  expect(toggle.textContent).toContain('5 rows')
  const body = container.querySelector('#dims-body') as HTMLElement
  expect(body.hasAttribute('hidden')).toBe(true)

  await user.click(toggle)
  expect(body.hasAttribute('hidden')).toBe(false)
  const groups = [...container.querySelectorAll('.dim-group')]
  expect(groups.map(group => group.getAttribute('data-owner'))).toEqual(['content', 'structure'])

  const content = [...groups[0].querySelectorAll('.dim')]
  expect(content.map(row => row.querySelector('.dim__name')!.textContent)).toEqual([
    'Work clarity',
    'Scope',
    'Responsibility alignment',
  ])
  expect(content[0].textContent).toContain('40 of 100 points')
  expect(content[1].textContent).toContain('Not scored')
  expect(content[1].querySelector('.dim__value')!.className).toContain('dim__value--none')

  const structure = [...groups[1].querySelectorAll('.dim')]
  expect(structure.map(row => row.querySelector('.dim__name')!.textContent)).toEqual([
    'Layout order',
    'Page budget',
  ])
  expect(structure[0].querySelector('.dim__value span')!.textContent).toBe('88')
})

it('opens the dimensions block when the report has no rows', () => {
  show(unavailableReport)
  expect(screen.getByText('No dimension rows were returned for this report.')).toBeTruthy()
})

it('says fewer findings when none were returned', () => {
  show({ ...multiReport, findings: [] })
  expect(screen.getByText('No findings were returned.')).toBeTruthy()
})

it('keeps the analysis limitation without a raw code', () => {
  show()
  expect(screen.getByRole('heading', { name: 'Analysis limitations' })).toBeTruthy()
  expect(screen.queryByText('partial_response')).toBeNull()
})

it('renders the report blocks in the reading order', () => {
  const { container } = show()
  const headings = [...container.querySelectorAll('h2')].map(node => node.textContent)
  expect(headings).toEqual([
    'Total score',
    'Sub-scores',
    'Top fixes',
    'All dimensions5 rows',
    'Findings',
    'Structure findings4 checks · 81 / 100',
    'Analysis limitations',
  ])
})
