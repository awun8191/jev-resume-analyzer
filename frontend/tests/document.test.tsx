import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import DocumentPane, { resolveBoxes } from '../src/features/document/DocumentPane'
import type { BoxFinding, PagePreview } from '../src/features/document/types'

const image = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="10" height="14"></svg>'

const boxes: BoxFinding[] = [
  {
    id: 'a', page: 0,
    box: { top: 0.1, bottom: 0.2, left: 0.1, right: 0.9 },
    label: 'Work clarity', answer: 'present', severity: null,
  },
  {
    id: 'b', page: 1,
    box: { top: 0.5, bottom: 0.6, left: 0.1, right: 0.4 },
    label: 'Scope', answer: 'absent', severity: 'high',
  },
]

function show(
  pages: PagePreview[],
  attached = true,
  selectedId: string | null = null,
  findings: BoxFinding[] = boxes,
) {
  const onSelect = vi.fn()
  render(
    <DocumentPane
      pages={pages}
      boxes={findings}
      selectedId={selectedId}
      onSelect={onSelect}
      fileName="fixture.pdf"
      attached={attached}
      onReattach={vi.fn()}
    />,
  )
  return onSelect
}

it('says plainly that there is no page preview and lists the boxes', () => {
  show([])
  expect(screen.getByText('No page preview')).toBeTruthy()
  expect(screen.getByText('Boxes reported')).toBeTruthy()
  expect(screen.getAllByRole('button', { name: /Page \d/ })).toHaveLength(2)
  expect(screen.queryByRole('group', { name: 'Page navigation' })).toBeNull()
})

it('asks for the file again when the tab was restored without it', () => {
  show([], false)
  expect(screen.getByText('Re-attach the file to show the page')).toBeTruthy()
  expect(screen.getByLabelText('Re-attach the CV file')).toBeTruthy()
})

it('draws one box per returned location, positioned from the fractions', async () => {
  const user = userEvent.setup()
  const onSelect = show([{ imageUrl: image }])

  const box = screen.getByRole('button', { name: 'Finding 1: Work clarity, present, page 1' })
  expect(box.style.top).toContain('10')
  expect(box.style.left).toContain('10')
  expect(box.style.width).toContain('80')
  expect(box.style.height).toContain('10')
  // Only page 0 boxes are drawn on page 0.
  expect(screen.queryByRole('button', { name: /Scope/ })).toBeNull()

  await user.click(box)
  expect(onSelect).toHaveBeenCalledWith('a')
})

it('marks the selected box and hides the overlay on request', async () => {
  const user = userEvent.setup()
  show([{ imageUrl: image }], true, 'a')

  expect(screen.getByRole('button', { name: /Finding 1:/ }).getAttribute('aria-pressed')).toBe('true')

  await user.click(screen.getByRole('button', { name: 'Hide boxes' }))
  expect(screen.queryByRole('button', { name: /Finding 1:/ })).toBeNull()
  expect(screen.getByRole('button', { name: 'Show boxes' })).toBeTruthy()
})

it('moves between pages and shows the count', async () => {
  const user = userEvent.setup()
  show([{ imageUrl: image }, { imageUrl: image }])

  const nav = screen.getByRole('group', { name: 'Page navigation' })
  expect(nav.textContent).toContain('1 of 2')

  await user.click(screen.getByRole('button', { name: 'Next page' }))
  expect(nav.textContent).toContain('2 of 2')
  expect(screen.getByRole('button', { name: 'Finding 2: Scope, absent, page 2' })).toBeTruthy()
  expect(screen.queryByRole('button', { name: /Work clarity/ })).toBeNull()
})

const sectionPages: PagePreview[] = [
  {
    imageUrl: image,
    sections: [
      { id: 'experience', label: 'EXPERIENCE', page: 0, box: { top: 0.2, bottom: 0.5, left: 0.08, right: 0.92 } },
      { id: 'skills', label: 'SKILLS', page: 0, box: { top: 0.5, bottom: 0.7, left: 0.08, right: 0.6 } },
    ],
  },
]

const sectionFindings: BoxFinding[] = [
  {
    id: 's1', page: 0,
    box: { top: 0.9, bottom: 0.95, left: 0.1, right: 0.2 },
    section: 'Work Experience',
    label: 'Work clarity', answer: 'present', severity: null,
  },
  {
    id: 's2', page: 0,
    box: { top: 0.8, bottom: 0.85, left: 0.1, right: 0.2 },
    section: null,
    label: 'Scope', answer: 'absent', severity: 'high',
  },
]

it('draws the exact section box for a finding that names a section', async () => {
  const user = userEvent.setup()
  show(sectionPages, true, null, sectionFindings)

  const exact = screen.getByRole('button', { name: 'Finding 1: Work clarity, present, page 1' })
  expect(parseFloat(exact.style.top)).toBeCloseTo(20, 3)
  expect(parseFloat(exact.style.left)).toBeCloseTo(8, 3)
  expect(parseFloat(exact.style.width)).toBeCloseTo(84, 3)
  expect(parseFloat(exact.style.height)).toBeCloseTo(30, 3)
  expect(exact.getAttribute('data-source')).toBe('section')

  await user.click(exact)
  expect(screen.getByRole('button', { name: /Finding 1:/ }).getAttribute('aria-pressed')).toBeTruthy()
})

it('keeps the reported box for a finding without a section', () => {
  show(sectionPages, true, null, sectionFindings)
  const reported = screen.getByRole('button', { name: 'Finding 2: Scope, absent, page 1' })
  expect(parseFloat(reported.style.top)).toBeCloseTo(80, 3)
  expect(reported.getAttribute('data-source')).toBe('reported')
})

it('is reachable and activatable from the keyboard on a section box', async () => {
  const user = userEvent.setup()
  const onSelect = show(sectionPages, true, null, sectionFindings)

  const box = screen.getByRole('button', { name: /Finding 1:/ })
  box.focus()
  expect(document.activeElement).toBe(box)

  await user.keyboard('{Enter}')
  expect(onSelect).toHaveBeenCalledWith('s1')
})

it('hides section boxes with the same toggle', async () => {
  const user = userEvent.setup()
  show(sectionPages, true, null, sectionFindings)

  expect(screen.getByRole('button', { name: /Finding 1:/ })).toBeTruthy()
  await user.click(screen.getByRole('button', { name: 'Hide boxes' }))
  expect(screen.queryByRole('button', { name: /Finding 1:/ })).toBeNull()
  await user.click(screen.getByRole('button', { name: 'Show boxes' }))
  expect(screen.getByRole('button', { name: /Finding 1:/ })).toBeTruthy()
})

it('does not invent a box when no section or reported geometry matches', () => {
  const resolved = resolveBoxes(
    [{
      id: 'x', page: 0, box: null, section: 'Certifications',
      label: 'Work clarity', answer: 'present', severity: null,
    }],
    sectionPages,
  )
  expect(resolved).toEqual([])
})

it('resolves a section without a page only when it appears on one page', () => {
  const finding: BoxFinding = {
    id: 's3', page: null, box: null, section: 'Core Skills',
    label: 'Work clarity', answer: 'present', severity: null,
  }
  const [resolved] = resolveBoxes([finding], sectionPages)
  expect(resolved.page).toBe(0)
  expect(resolved.source).toBe('section')
  expect(resolved.box).toEqual({ top: 0.5, bottom: 0.7, left: 0.08, right: 0.6 })

  const repeated: PagePreview[] = [
    ...sectionPages,
    { imageUrl: image, sections: [{ id: 'skills', label: 'SKILLS', page: 1, box: { top: 0, bottom: 1, left: 0.08, right: 0.6 } }] },
  ]
  expect(resolveBoxes([finding], repeated)).toEqual([])
})
