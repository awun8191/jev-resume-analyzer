import { describe, expect, it } from 'vitest'
import { layoutDocument, layoutPage, sectionKey } from '../src/features/document/pdfLayout'
import type { PdfTextItemLike } from '../src/features/document/pdfLayout'

const PAGE_HEIGHT = 800
const PAGE_WIDTH = 600

/* Synthetic text items in PDF points. top is measured from the page top, which
 * is how a person reads the page. */
function item(text: string, left: number, top: number, size: number, width?: number): PdfTextItemLike {
  return {
    str: text,
    transform: [size, 0, 0, size, left, PAGE_HEIGHT - top - size],
    width: width ?? text.length * size * 0.55,
    height: size,
  }
}

const page = (...items: PdfTextItemLike[]) => ({ items })

describe('layoutPage', () => {
  it('spans every known heading down to the next heading', () => {
    const layout = layoutPage(
      page(
        item('HEADER', 48, 40, 18),
        item('Ada Lovelace', 48, 70, 12),
        item('SUMMARY', 48, 120, 15),
        item('Engineer with ten years of experience building systems.', 48, 145, 12),
        item('EXPERIENCE', 48, 220, 15),
        item('Staff engineer, analytical engine programme.', 48, 245, 12),
        item('EDUCATION', 48, 420, 15),
        item('BSc Mathematics, 1840.', 48, 445, 12),
        item('SKILLS', 48, 560, 15),
        item('Analysis, notation, correspondence.', 48, 585, 12, 500),
      ),
      PAGE_HEIGHT,
      PAGE_WIDTH,
    )

    expect(layout.sections.map(section => section.id)).toEqual([
      'header', 'summary', 'experience', 'education', 'skills',
    ])
    expect(layout.sections.map(section => section.label)).toEqual([
      'HEADER', 'SUMMARY', 'EXPERIENCE', 'EDUCATION', 'SKILLS',
    ])

    const [header, summary, experience, education, skills] = layout.sections
    expect(header.box.top).toBeCloseTo(40 / PAGE_HEIGHT, 4)
    expect(summary.box.top).toBeCloseTo(120 / PAGE_HEIGHT, 4)
    expect(summary.box.bottom).toBeCloseTo(220 / PAGE_HEIGHT, 4)
    expect(experience.box.bottom).toBeCloseTo(420 / PAGE_HEIGHT, 4)
    expect(education.box.bottom).toBeCloseTo(560 / PAGE_HEIGHT, 4)
    expect(skills.box.bottom).toBe(1)
    expect(skills.box.left).toBeLessThan(0.1)
    expect(skills.box.right).toBeGreaterThan(0.9)

    for (const section of layout.sections) {
      expect(section.box.bottom).toBeGreaterThan(section.box.top)
      expect(section.box.right).toBeGreaterThan(section.box.left)
    }
  })

  it('keeps two columns apart instead of spanning the gutter', () => {
    const layout = layoutPage(
      page(
        item('EXPERIENCE', 48, 100, 15, 120),
        item('Staff engineer at the analytical engine programme.', 48, 130, 12, 240),
        item('Led the notation working group.', 48, 150, 12, 200),
        item('EDUCATION', 48, 300, 15, 100),
        item('BSc Mathematics, 1840.', 48, 330, 12, 200),
        item('SKILLS', 320, 110, 15, 70),
        item('Analysis and notation.', 320, 140, 12, 220),
        item('Correspondence and translation.', 320, 160, 12, 230),
        item('PROJECTS', 320, 320, 15, 90),
        item('Difference engine notes.', 320, 350, 12, 210),
      ),
      PAGE_HEIGHT,
      PAGE_WIDTH,
    )

    expect(layout.sections.map(section => section.id)).toEqual([
      'experience', 'skills', 'education', 'projects',
    ])

    const experience = layout.sections.find(section => section.id === 'experience')!
    const skills = layout.sections.find(section => section.id === 'skills')!
    expect(experience.box.right).toBeLessThan(0.5)
    expect(experience.box.bottom).toBeCloseTo(300 / PAGE_HEIGHT, 4)
    expect(skills.box.left).toBeGreaterThan(0.5)
    expect(skills.box.bottom).toBeCloseTo(320 / PAGE_HEIGHT, 4)
    for (const section of layout.sections) {
      expect(section.box.right - section.box.left).toBeLessThan(0.55)
    }
  })

  it('returns no sections when the page has no known heading', () => {
    const layout = layoutPage(
      page(
        item('A paragraph of ordinary resume prose without a heading.', 48, 100, 12),
        item('Another paragraph, still ordinary.', 48, 130, 12),
      ),
      PAGE_HEIGHT,
      PAGE_WIDTH,
    )
    expect(layout.sections).toEqual([])
    expect(layout.lines.length).toBe(2)
  })

  it('returns no sections for an empty text layer', () => {
    expect(layoutPage(page(), PAGE_HEIGHT, PAGE_WIDTH)).toEqual({ sections: [], lines: [] })
    expect(layoutPage(page(), 0, PAGE_WIDTH).sections).toEqual([])
  })

  it('accepts headings at two font sizes above the body median', () => {
    const layout = layoutPage(
      page(
        item('PROFILE', 48, 60, 20),
        item('A short profile paragraph in the body size.', 48, 100, 11.5),
        item('EXPERIENCE', 48, 180, 14),
        item('A role description in the body size.', 48, 220, 11.5),
        item('SKILLS', 48, 320, 9),
        item('A line that happens to sit at a smaller size.', 48, 350, 11.5),
      ),
      PAGE_HEIGHT,
      PAGE_WIDTH,
    )
    expect(layout.sections.map(section => section.id)).toEqual(['summary', 'experience'])
  })
})

describe('layoutDocument', () => {
  it('continues the last section onto the next page with one box per page', () => {
    const first = page(
      item('SUMMARY', 48, 80, 15),
      item('A profile paragraph.', 48, 110, 12),
      item('EXPERIENCE', 48, 600, 15),
      item('A role that runs to the bottom of the page.', 48, 630, 12),
    )
    const second = page(item('The role continues here.', 48, 80, 12))

    const sections = layoutDocument([
      { textContent: first, height: PAGE_HEIGHT, width: PAGE_WIDTH },
      { textContent: second, height: PAGE_HEIGHT, width: PAGE_WIDTH },
    ])

    expect(sections.map(section => `${section.page}:${section.id}`)).toEqual([
      '0:summary', '0:experience', '1:experience',
    ])
    const continuation = sections[2]
    expect(continuation.box.top).toBe(0)
    expect(continuation.box.bottom).toBe(1)
    expect(continuation.label).toBe('EXPERIENCE')
  })
})

describe('sectionKey', () => {
  it('maps variants a finding may use onto layout ids', () => {
    expect(sectionKey('Work Experience')).toBe('experience')
    expect(sectionKey('PROFILE')).toBe('summary')
    expect(sectionKey('Core Skills:')).toBe('skills')
    expect(sectionKey('Certifications')).toBe('certifications')
  })
})
