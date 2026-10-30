import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import ResultStage from '../src/features/results/ResultStage'
import type { AnalysisReport } from '../src/api/schema'
import { multiReport, report } from './contract/fixtures/responses'

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

it('states a missing rating in words and never substitutes a number', () => {
  const { container } = show(report)
  const block = container.querySelector('.score') as HTMLElement
  expect(within(block).getByText('Not scored yet')).toBeTruthy()
  expect(container.querySelector('.score__value')).toBeNull()
  expect(block.textContent).toContain('No scoring map is approved or calibrated')
})

it('shows the two sub-score slots as pending, with no value', () => {
  show()
  expect(screen.getByRole('heading', { name: 'Sub-scores' })).toBeTruthy()
  const subscores = document.querySelector('.subscores') as HTMLElement
  expect(subscores.textContent).toContain('Structure')
  expect(subscores.textContent).toContain('Content')
  expect(screen.getAllByText('Pending')).toHaveLength(2)
  expect(subscores.textContent).not.toMatch(/\d/)
})

it('counts findings per dimension in first-seen order', () => {
  const { container } = show()
  const rows = [...container.querySelectorAll('.dim')]
  expect(rows.map(row => row.querySelector('.dim__name')!.textContent)).toEqual([
    'Work clarity',
    'Scope',
    'Responsibility alignment',
  ])
  expect(rows.map(row => [...row.querySelectorAll('.dim__n')].map(n => n.textContent))).toEqual([
    ['1', '1', '0', '0'],
    ['0', '0', '1', '0'],
    ['0', '0', '0', '1'],
  ])
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
  expect(screen.getByText('Not scored yet')).toBeTruthy()
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
