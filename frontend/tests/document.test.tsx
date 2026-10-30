import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import DocumentPane from '../src/features/document/DocumentPane'
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

function show(pages: PagePreview[], attached = true, selectedId: string | null = null) {
  const onSelect = vi.fn()
  render(
    <DocumentPane
      pages={pages}
      boxes={boxes}
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
