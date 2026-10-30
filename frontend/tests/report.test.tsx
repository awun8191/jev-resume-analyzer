import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
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

function show(subject: AnalysisReport = multiReport, selectedId: string | null = null, onSelect = noop) {
  return render(
    <ResultStage
      report={subject}
      onEdit={noop}
      selectedId={selectedId}
      onSelect={onSelect}
    />,
  )
}

it('shows the total, band, range and coverage for a combined report', () => {
  const { container } = show(report)
  const block = container.querySelector('.score') as HTMLElement
  expect(block.getAttribute('data-mode')).toBe('combined')
  expect(block.querySelector('.score__value')!.textContent).toBe('71/ 100')
  expect(block.textContent).toContain('Adequate evidence')
  expect(block.textContent).toContain('Content and layout')
  expect(block.textContent).toContain('86% of prepared content weight')
  expect(block.textContent).toContain('Weighted 70% content and 30% layout.')
  // A combined total has no range of its own, so none is shown.
  expect(block.querySelector('.score__range')).toBeNull()
})

it('shows structure and then content with their own bands', () => {
  const { container } = show()
  const subscores = [...container.querySelectorAll('.subscore')]
  expect(subscores.map(node => node.getAttribute('data-owner'))).toEqual(['structure', 'content'])
  expect(subscores[0].textContent).toContain('81')
  expect(subscores[0].textContent).toContain('Strong evidence')
  expect(subscores[1].textContent).toContain('58')
  expect(subscores[1].textContent).toContain('Partial evidence')
  expect(subscores[1].textContent).toContain('Range 46 to 69')
})

it('labels a content only total and explains why layout is missing', () => {
  const { container } = show(contentOnlyReport)
  const block = container.querySelector('.score') as HTMLElement
  expect(block.getAttribute('data-mode')).toBe('content_only')
  expect(block.textContent).toContain('Content only')
  expect(block.textContent).toContain('Layout is scored for PDF uploads only.')
  expect(block.textContent).toContain('unsupported_format')
  // The total is the content value, so its range belongs here.
  expect(block.textContent).toContain('Range 46 to 69')
  const structure = container.querySelector('.subscore[data-owner="structure"]') as HTMLElement
  expect(structure.textContent).toContain('Not scored')
  expect(structure.querySelector('.score__value')).toBeNull()
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
})

it('shows no number at all when nothing could be scored', () => {
  const { container } = show(unavailableReport)
  const block = container.querySelector('.score') as HTMLElement
  expect(block.getAttribute('data-mode')).toBe('unavailable')
  expect(block.querySelector('.score__value')).toBeNull()
  expect(block.querySelector('.score__none')!.textContent).toBe('Not scored')
  expect(block.textContent).toContain('Neither content nor layout produced a score.')
  expect(block.textContent).toContain('The layout check could not read the pages.')
  expect(block.textContent).not.toMatch(/\b0\/ 100\b/)
})

it('groups dimension rows by owner and keeps a null value a word', () => {
  const { container } = show()
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
  expect(structure[1].textContent).toContain('Not scored')
})

it('says when a report has no dimension rows', () => {
  show({ ...multiReport, dimensions: [] })
  expect(screen.getByText('No dimension rows were returned for this report.')).toBeTruthy()
})

it('shows every answer state as a word plus a shape', () => {
  const { container } = show()
  const states = [...container.querySelectorAll('.state')]
  expect(states.map(el => el.textContent!.trim())).toEqual([
    '\u25A0Present',
    '\u25A1Absent',
    '\u2212Not applicable',
    '?Unable to assess',
  ])
  expect(states.map(el => el.querySelector('.state__glyph')!.textContent)).toEqual([
    '\u25A0',
    '\u25A1',
    '\u2212',
    '?',
  ])
})

it('expands a finding to its question, criteria, answer and distribution', async () => {
  const user = userEvent.setup()
  const { container } = show()
  const first = container.querySelector('.finding') as HTMLElement
  expect(first.textContent).toContain('SYNTHETIC: is the work described clearly?')

  await user.click(within(first).getAllByText('Question and answer detail')[0])
  const detail = first.querySelector('.disclosure__body') as HTMLElement
  expect(detail.textContent).toContain('SYNTHETIC criterion A.')
  expect(detail.textContent).toContain('SYNTHETIC criterion B.')
  expect(detail.textContent).toContain('62.0%')
  expect(detail.textContent).toContain('58.0%')
  expect(detail.textContent).toContain('not hiring likelihood or CV quality')
  expect(detail.textContent).toContain('Page 1')
})

it('keeps a missing distribution and confidence explicit', () => {
  const { container } = show()
  const last = [...container.querySelectorAll('.finding')].at(-1) as HTMLElement
  expect(last.textContent).toContain('Unable to assess')
  const detail = last.querySelector('.disclosure__body') as HTMLElement
  expect(detail.textContent).toContain('Not reported by the provider.')
  expect(detail.textContent).toContain('Provider confidenceNot reported')
  expect(last.querySelector('.dist')).toBeNull()
})

it('shows the partial response count without inventing a score', () => {
  show()
  expect(screen.getByText(/1 question not returned/)).toBeTruthy()
  expect(screen.getByText('Adequate evidence')).toBeTruthy()
  expect(screen.getByRole('heading', { name: 'Analysis limitations' })).toBeTruthy()
})

it('selects a finding from its title button and marks the located ones', async () => {
  const user = userEvent.setup()
  const onSelect = vi.fn()
  const { container } = show(multiReport, null, onSelect)

  await user.click(screen.getByRole('button', { name: 'Work clarity. Page 1. Present.' }))
  expect(onSelect).toHaveBeenCalledWith('q-clarity')

  const rows = [...container.querySelectorAll('.finding')]
  expect(rows[2].textContent).toContain('No location')
  expect(rows[0].querySelector('.finding__loc')!.textContent).toBe('Page 1')
})

it('marks the selected finding in the list', () => {
  const { container } = show(multiReport, 'q-clarity')
  const first = container.querySelector('.finding') as HTMLElement
  expect(first.getAttribute('data-selected')).toBe('true')
  expect(within(first).getByRole('button', { name: /Work clarity/ }).getAttribute('aria-pressed')).toBe('true')
})

it('lists structure findings with a reason and no target for a pass', async () => {
  const user = userEvent.setup()
  const onSelect = vi.fn()
  const { container } = show(multiReport, null, onSelect)

  const section = container.querySelector('[aria-labelledby="structure-title"]') as HTMLElement
  const rows = [...section.querySelectorAll('.sfind')]
  expect(rows).toHaveLength(4)
  expect(rows.map(row => row.querySelector('.sfind__label')!.textContent)).toEqual([
    'Section order follows the rubric',
    'Two column layout is dense',
    'Section breaks across pages',
    'Font sizes are inconsistent',
  ])
  expect(rows[0].textContent).toContain('Pass')
  expect(rows[0].textContent).toContain('No location')
  expect(rows[0].querySelector('button')).toBeNull()
  expect(rows[2].textContent).toContain('Page 2')

  await user.click(within(section).getByRole('button', { name: 'Two column layout is dense. Major issue. Page 1.' }))
  expect(onSelect).toHaveBeenCalledWith('structure:dense-columns')
  expect(section.textContent).toContain('12 points lost')
  expect(section.textContent).toContain('SYNTHETIC: column gap is below the body text size.')
})

it('marks a selected structure finding', () => {
  const { container } = show(multiReport, 'structure:dense-columns')
  const selected = container.querySelector('.sfind[data-selected="true"]') as HTMLElement
  expect(selected.querySelector('.sfind__label')!.textContent).toBe('Two column layout is dense')
  expect(selected.querySelector('button')!.getAttribute('aria-pressed')).toBe('true')
})

it('says a content only report has no structure checks', () => {
  show(contentOnlyReport)
  expect(screen.getByText('No structure checks were returned. A content only report has no layout rows.')).toBeTruthy()
})

it('renders the report blocks in the contract order', () => {
  const { container } = show()
  const headings = [...container.querySelectorAll('h2')].map(node => node.textContent)
  expect(headings).toEqual([
    'Total score',
    'Sub-scores',
    'Dimensions',
    'Findings',
    'Structure findings',
    'Analysis limitations',
  ])
})
