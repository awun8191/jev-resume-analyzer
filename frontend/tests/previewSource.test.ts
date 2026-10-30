import { expect, it, vi } from 'vitest'
import { isPdf, previewPages } from '../src/features/document/previewSource'
import type { PagePreview } from '../src/features/document/types'

it('reads nothing when there is no pdf to read', async () => {
  const load = vi.fn(async () => [] as PagePreview[])
  expect(await previewPages(null, load)).toEqual([])
  expect(await previewPages(new File(['x'], 'notes.docx'), load)).toEqual([])
  expect(load).not.toHaveBeenCalled()
})

it('returns the pages an injected source supplies, without a canvas', async () => {
  const pages: PagePreview[] = [
    {
      imageUrl: 'data:image/png;base64,AA==',
      sections: [
        { id: 'experience', label: 'EXPERIENCE', page: 0, box: { top: 0.1, bottom: 0.4, left: 0.08, right: 0.9 } },
      ],
    },
  ]
  const load = vi.fn(async () => pages)
  const file = new File(['x'], 'cv.pdf', { type: 'application/pdf' })
  expect(await previewPages(file, load)).toBe(pages)
  expect(load).toHaveBeenCalledWith(file)
})

it('returns no pages when the source fails, so the pane keeps its empty state', async () => {
  const file = new File(['x'], 'cv.pdf', { type: 'application/pdf' })
  expect(await previewPages(file, async () => { throw new Error('scanned') })).toEqual([])
})

it('recognises a pdf by media type or extension', () => {
  expect(isPdf(new File(['x'], 'cv', { type: 'application/pdf' }))).toBe(true)
  expect(isPdf(new File(['x'], 'CV.PDF'))).toBe(true)
  expect(isPdf(new File(['x'], 'cv.docx'))).toBe(false)
})
