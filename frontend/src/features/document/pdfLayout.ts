import type { FindingBox } from '../../api/schema'

/*
 * Section spans from the PDF text layer.
 *
 * The provider reports boxes with low confidence. The page text has exact
 * positions, so the pane derives section rectangles from headings instead.
 * A heading is a short line whose text matches a known resume label and whose
 * glyph height is at least the page body median. A section runs from its
 * heading top to the top of the next heading in the same column, or to the
 * page bottom. Boxes are fractions of the page, origin top left.
 */

export interface PdfTextItemLike {
  str: string
  transform: number[]
  width: number
  height: number
  fontName?: string
}

export interface PdfTextContentLike {
  items: ReadonlyArray<PdfTextItemLike | { type: string }>
}

export interface SectionSpan {
  id: string
  label: string
  box: FindingBox
}

export interface LayoutLine {
  text: string
  height: number
  box: FindingBox
}

export interface PageLayout {
  sections: SectionSpan[]
  lines: LayoutLine[]
}

export interface PdfPageSource {
  textContent: PdfTextContentLike
  height: number
  width: number
}

export interface PageSection extends SectionSpan {
  page: number
}

interface SectionLabel {
  id: string
  label: string
}

const SECTIONS: ReadonlyArray<SectionLabel & { variants: readonly string[] }> = [
  {
    id: 'header', label: 'HEADER',
    variants: ['HEADER', 'CONTACT', 'CONTACT DETAILS', 'CONTACT INFORMATION',
      'PERSONAL DETAILS', 'PERSONAL INFORMATION'],
  },
  {
    id: 'summary', label: 'SUMMARY',
    variants: ['SUMMARY', 'PROFILE', 'PROFESSIONAL SUMMARY', 'PERSONAL SUMMARY',
      'PROFILE SUMMARY', 'PERSONAL PROFILE', 'EXECUTIVE SUMMARY', 'ABOUT',
      'ABOUT ME', 'OBJECTIVE', 'CAREER OBJECTIVE'],
  },
  {
    id: 'experience', label: 'EXPERIENCE',
    variants: ['EXPERIENCE', 'WORK EXPERIENCE', 'PROFESSIONAL EXPERIENCE',
      'RELEVANT EXPERIENCE', 'EMPLOYMENT', 'EMPLOYMENT HISTORY', 'WORK HISTORY',
      'CAREER HISTORY'],
  },
  {
    id: 'education', label: 'EDUCATION',
    variants: ['EDUCATION', 'EDUCATION AND TRAINING', 'ACADEMIC BACKGROUND',
      'ACADEMIC QUALIFICATIONS', 'QUALIFICATIONS'],
  },
  {
    id: 'skills', label: 'SKILLS',
    variants: ['SKILLS', 'TECHNICAL SKILLS', 'CORE SKILLS', 'KEY SKILLS',
      'SKILL SET', 'SKILLSET', 'COMPETENCIES', 'CORE COMPETENCIES', 'TOOLS',
      'TECHNOLOGIES'],
  },
  {
    id: 'projects', label: 'PROJECTS',
    variants: ['PROJECTS', 'PROJECT EXPERIENCE', 'PERSONAL PROJECTS',
      'SELECTED PROJECTS', 'KEY PROJECTS', 'PORTFOLIO'],
  },
]

const VARIANT_INDEX = new Map<string, SectionLabel>()
for (const section of SECTIONS) {
  for (const variant of section.variants) {
    VARIANT_INDEX.set(variant, { id: section.id, label: section.label })
  }
}

const clamp01 = (value: number) => Math.min(1, Math.max(0, value))

/* Upper case, collapse whitespace, drop list markers and trailing
 * punctuation. A parenthetical continued mark is not part of the label. */
function cleanLabel(text: string): string {
  return text
    .replace(/[\u200B-\u200D\uFEFF]/g, '')
    .replace(/\s*\((?:continued|cont\.?d?|contd)\)\s*$/i, '')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/^[^A-Za-z0-9]+/, '')
    .replace(/[^A-Za-z0-9]+$/, '')
    .toUpperCase()
}

/* Maps any spelling a finding may use for a section onto the layout id. */
export function sectionKey(raw: string): string {
  const cleaned = cleanLabel(raw)
  return VARIANT_INDEX.get(cleaned)?.id ?? cleaned.toLowerCase().replace(/[^a-z0-9]+/g, '_')
}

function headingFor(text: string): SectionLabel | null {
  const cleaned = cleanLabel(text)
  if (!cleaned || cleaned.length > 40) return null
  if (cleaned.split(' ').length > 4) return null
  return VARIANT_INDEX.get(cleaned) ?? null
}

interface Glyph {
  text: string
  left: number
  right: number
  top: number
  bottom: number
  baseline: number
  height: number
}

function median(values: number[]): number {
  if (!values.length) return 0
  const sorted = [...values].sort((a, b) => a - b)
  const middle = Math.floor(sorted.length / 2)
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2
}

function overlapsHorizontally(a: FindingBox, b: FindingBox): boolean {
  const overlap = Math.min(a.right, b.right) - Math.max(a.left, b.left)
  if (overlap <= 0) return false
  const narrower = Math.min(a.right - a.left, b.right - b.left)
  const wider = Math.max(a.right - a.left, b.right - b.left)
  return overlap >= narrower * 0.3 || (wider > 0 && overlap / wider >= 0.18)
}

function glyphsFrom(
  textContent: PdfTextContentLike,
  viewportHeight: number,
  viewportWidth: number,
): Glyph[] {
  const glyphs: Glyph[] = []
  for (const item of textContent.items) {
    if (!('str' in item) || !item.str.trim()) continue
    const transform = item.transform
    if (!Array.isArray(transform) || transform.length < 6) continue
    const height = Math.abs(item.height)
      || Math.abs(transform[3])
      || Math.hypot(transform[2], transform[3])
    if (!(height > 0)) continue
    const left = transform[4]
    const top = viewportHeight - (transform[5] + height)
    const width = item.width > 0 ? item.width : (height * item.str.length) / 2
    glyphs.push({
      text: item.str,
      left: left / viewportWidth,
      right: (left + width) / viewportWidth,
      top: top / viewportHeight,
      bottom: (top + height) / viewportHeight,
      baseline: transform[5] / viewportHeight,
      height: height / viewportHeight,
    })
  }
  return glyphs
}

/* Rows share a baseline. Each row then splits wherever the horizontal gap is
 * wider than a word space, which keeps two columns apart. */
function linesFrom(glyphs: Glyph[]): LayoutLine[] {
  if (!glyphs.length) return []
  const baselineTolerance = Math.max(0.0005, median(glyphs.map(glyph => glyph.height)) * 0.45)
  const sorted = [...glyphs].sort((a, b) => b.baseline - a.baseline || a.left - b.left)
  const rows: Glyph[][] = []
  for (const glyph of sorted) {
    const row = rows[rows.length - 1]
    if (row && Math.abs(row[0].baseline - glyph.baseline) <= baselineTolerance) row.push(glyph)
    else rows.push([glyph])
  }

  const lines: LayoutLine[] = []
  for (const row of rows) {
    row.sort((a, b) => a.left - b.left)
    const fragments: Glyph[][] = []
    for (const glyph of row) {
      const current = fragments[fragments.length - 1]
      if (!current) {
        fragments.push([glyph])
        continue
      }
      const right = current.reduce((max, part) => Math.max(max, part.right), 0)
      const size = current.reduce((max, part) => Math.max(max, part.height), 0)
      if (glyph.left - right > Math.max(size * 1.6, 0.012)) fragments.push([glyph])
      else current.push(glyph)
    }

    for (const fragment of fragments) {
      const first = fragment[0]
      let text = first.text.trim()
      for (let index = 1; index < fragment.length; index += 1) {
        const previous = fragment[index - 1]
        const glyph = fragment[index]
        const gap = glyph.left - previous.right
        if (gap > Math.max(glyph.height * 0.18, 0.0005)) text += ' '
        text += glyph.text.trim()
      }
      text = text.replace(/\s+/g, ' ').trim()
      if (!text) continue
      const left = clamp01(Math.min(...fragment.map(glyph => glyph.left)))
      const right = clamp01(Math.max(...fragment.map(glyph => glyph.right)))
      const top = clamp01(Math.min(...fragment.map(glyph => glyph.top)))
      const bottom = clamp01(Math.max(...fragment.map(glyph => glyph.bottom)))
      if (right - left <= 0 || bottom - top <= 0) continue
      lines.push({
        text,
        height: Math.max(...fragment.map(glyph => glyph.height)),
        box: { top, bottom, left, right },
      })
    }
  }
  return lines
}

export function layoutPage(
  textContent: PdfTextContentLike,
  viewportHeight: number,
  viewportWidth: number,
): PageLayout {
  if (!(viewportHeight > 0) || !(viewportWidth > 0)) return { sections: [], lines: [] }
  const lines = linesFrom(glyphsFrom(textContent, viewportHeight, viewportWidth))
  if (!lines.length) return { sections: [], lines: [] }

  const labelled = lines.map(line => ({ line, label: headingFor(line.text) }))
  const bodyHeights = labelled.filter(entry => !entry.label).map(entry => entry.line.height)
  const bodyMedian = median(bodyHeights.length ? bodyHeights : lines.map(line => line.height))

  const headings = labelled.filter(
    (entry): entry is { line: LayoutLine; label: SectionLabel } =>
      entry.label !== null && entry.line.height + 1e-9 >= bodyMedian,
  )
  headings.sort((a, b) => a.line.box.top - b.line.box.top || a.line.box.left - b.line.box.left)

  const sections: SectionSpan[] = []
  const used = new Set<string>()
  for (const heading of headings) {
    if (used.has(heading.label.id)) continue
    const start = clamp01(heading.line.box.top)
    const eps = Math.max(0.0015, heading.line.height * 0.5)
    let end = 1
    for (const other of headings) {
      if (other === heading) continue
      if (other.line.box.top <= start + eps) continue
      if (!overlapsHorizontally(other.line.box, heading.line.box)) continue
      end = Math.min(end, other.line.box.top)
    }
    end = clamp01(end)
    if (end - start < 0.004) continue

    const band = lines.filter(line =>
      line.box.top >= start - eps &&
      line.box.top < end - eps &&
      overlapsHorizontally(line.box, heading.line.box))
    const left = clamp01(Math.min(...band.map(line => line.box.left), heading.line.box.left))
    const right = clamp01(Math.max(...band.map(line => line.box.right), heading.line.box.right))
    if (right - left < 0.004) continue

    sections.push({
      id: heading.label.id,
      label: heading.label.label,
      box: { top: start, bottom: end, left, right },
    })
    used.add(heading.label.id)
  }

  sections.sort((a, b) => a.box.top - b.box.top || a.box.left - b.box.left)
  return { sections, lines }
}

/* One box per section per page. A page that starts without a heading continues
 * the last section of the page before it. */
export function layoutDocument(pages: PdfPageSource[]): PageSection[] {
  const result: PageSection[] = []
  let previous: SectionSpan | null = null

  pages.forEach((source, page) => {
    const layout = layoutPage(source.textContent, source.height, source.width)
    const first = layout.sections[0]
    if (previous && (!first || first.box.top > 0.02)) {
      const bottom = first ? clamp01(first.box.top) : 1
      if (bottom > 0.004) {
        result.push({
          id: previous.id,
          label: previous.label,
          page,
          box: { top: 0, bottom, left: previous.box.left, right: previous.box.right },
        })
      }
    }
    for (const section of layout.sections) result.push({ ...section, page })
    if (layout.sections.length) previous = layout.sections[layout.sections.length - 1]
  })

  return result
}
