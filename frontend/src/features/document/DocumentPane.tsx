import { useEffect, useMemo, useRef, useState } from 'react'
import type { FindingBox } from '../../api/schema'
import { sectionKey } from './pdfLayout'
import type { BoxFinding, PagePreview } from './types'
import './document.css'

const ZOOMS = [1, 1.25, 1.5]

const pct = (n: number) => `${(n * 100).toFixed(3)}%`

interface DrawableBox extends BoxFinding {
  page: number
  box: FindingBox
  source: 'section' | 'reported'
}

/* A finding with a section uses the exact text layer box. A finding without
 * one keeps the reported box. Nothing is drawn unless one of the two exists. */
export function resolveBoxes(findings: BoxFinding[], pages: PagePreview[]): DrawableBox[] {
  const byPage = new Map<number, Map<string, { page: number; box: FindingBox }>>()
  const anywhere = new Map<string, Array<{ page: number; box: FindingBox }>>()

  pages.forEach((page, index) => {
    for (const section of page.sections ?? []) {
      const pageIndex = Number.isInteger(section.page) ? section.page : index
      const entry = { page: pageIndex, box: section.box }
      const onPage = byPage.get(pageIndex) ?? new Map<string, { page: number; box: FindingBox }>()
      onPage.set(section.id, entry)
      byPage.set(pageIndex, onPage)
      const list = anywhere.get(section.id) ?? []
      list.push(entry)
      anywhere.set(section.id, list)
    }
  })

  const resolved: DrawableBox[] = []
  for (const finding of findings) {
    if (finding.section) {
      const key = sectionKey(finding.section)
      let hit = finding.page == null ? undefined : byPage.get(finding.page)?.get(key)
      if (!hit) {
        const list = anywhere.get(key)
        /* A section that continues across pages is only unambiguous when it
         * appears on a single page. Otherwise the finding needs its own page. */
        if (list?.length === 1) hit = list[0]
      }
      if (hit) {
        resolved.push({ ...finding, page: hit.page, box: hit.box, source: 'section' })
        continue
      }
    }
    if (finding.page != null && finding.box) {
      resolved.push({ ...finding, page: finding.page, box: finding.box, source: 'reported' })
    }
  }
  return resolved
}

function initialCollapsed() {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return window.matchMedia('(max-width: 899px)').matches
}

interface Props {
  pages: PagePreview[]
  boxes: BoxFinding[]
  selectedId: string | null
  onSelect: (id: string) => void
  fileName: string
  attached: boolean
  onReattach: (file: File) => void
}

export default function DocumentPane({
  pages,
  boxes,
  selectedId,
  onSelect,
  fileName,
  attached,
  onReattach,
}: Props) {
  const [pageIndex, setPageIndex] = useState(0)
  const [zoomIndex, setZoomIndex] = useState(0)
  const [showBoxes, setShowBoxes] = useState(true)
  const [collapsed, setCollapsed] = useState(initialCollapsed)
  const boxRefs = useRef<Record<string, HTMLButtonElement | null>>({})

  const total = pages.length
  const page = pages[pageIndex]
  const hasImage = Boolean(page?.imageUrl)
  const drawable = useMemo(() => resolveBoxes(boxes, pages), [boxes, pages])
  const pageBoxes = drawable.filter(box => box.page === pageIndex)
  const numbers = new Map(drawable.map((box, index) => [box.id, index + 1]))

  /* Selecting a finding opens the pane, turns to its page and brings the box
   * into view. Focus stays on the finding: scrolling is the only movement. */
  useEffect(() => {
    if (!selectedId) return
    const target = drawable.find(box => box.id === selectedId)
    if (!target) return
    setPageIndex(target.page)
    setShowBoxes(true)
    setCollapsed(false)
    const scroll = () => {
      boxRefs.current[selectedId]?.scrollIntoView?.({ block: 'nearest', inline: 'nearest' })
    }
    if (typeof requestAnimationFrame === 'function') {
      const frame = requestAnimationFrame(scroll)
      return () => cancelAnimationFrame(frame)
    }
    scroll()
  }, [selectedId, drawable])

  return (
    <section className="docpane" aria-labelledby="docpane-title">
      <div className="docpane__bar">
        <div>
          <h2 className="label" id="docpane-title">Document</h2>
          <p className="docpane__file">{fileName || 'No document'}</p>
        </div>
        <button
          type="button"
          className="btn btn--quiet docpane__collapse"
          aria-expanded={!collapsed}
          aria-controls="document-pane"
          onClick={() => setCollapsed(value => !value)}
        >
          {collapsed ? 'Show document' : 'Hide document'}
        </button>
      </div>

      <div className="docpane__body" id="document-pane" hidden={collapsed}>
        {hasImage && (
          <div className="docpane__controls">
            <div className="docpane__group" role="group" aria-label="Page navigation">
              <button
                type="button"
                className="docpane__step"
                aria-label="Previous page"
                disabled={pageIndex === 0}
                onClick={() => setPageIndex(index => Math.max(0, index - 1))}
              >
                <span aria-hidden="true">{'\u2190'}</span>
              </button>
              <p className="docpane__count"><b>{pageIndex + 1}</b> of {total}</p>
              <button
                type="button"
                className="docpane__step"
                aria-label="Next page"
                disabled={pageIndex >= total - 1}
                onClick={() => setPageIndex(index => Math.min(total - 1, index + 1))}
              >
                <span aria-hidden="true">{'\u2192'}</span>
              </button>
            </div>

            <div className="docpane__group" role="group" aria-label="Zoom">
              <button
                type="button"
                className="docpane__step"
                aria-label="Zoom out"
                disabled={zoomIndex === 0}
                onClick={() => setZoomIndex(index => Math.max(0, index - 1))}
              >
                <span aria-hidden="true">{'\u2212'}</span>
              </button>
              <p className="docpane__count">{Math.round(ZOOMS[zoomIndex] * 100)}%</p>
              <button
                type="button"
                className="docpane__step"
                aria-label="Zoom in"
                disabled={zoomIndex >= ZOOMS.length - 1}
                onClick={() => setZoomIndex(index => Math.min(ZOOMS.length - 1, index + 1))}
              >
                <span aria-hidden="true">+</span>
              </button>
            </div>

            <button
              type="button"
              className="docpane__toggle"
              aria-pressed={!showBoxes}
              onClick={() => setShowBoxes(value => !value)}
            >
              <span className="docpane__toggle-mark" aria-hidden="true" />
              {showBoxes ? 'Hide boxes' : 'Show boxes'}
            </button>
          </div>
        )}

        <div className="docpane__scroll" tabIndex={0} role="region" aria-label="Document page">
          {hasImage ? (
            <div className="docpane__page" style={{ width: `${ZOOMS[zoomIndex] * 100}%` }}>
              <img src={page!.imageUrl} alt={`Page ${pageIndex + 1} of ${fileName}`} />
              {showBoxes && pageBoxes.map(box => (
                <button
                  key={box.id}
                  ref={node => { boxRefs.current[box.id] = node }}
                  type="button"
                  className="box"
                  data-source={box.source}
                  aria-pressed={box.id === selectedId}
                  aria-label={`Finding ${numbers.get(box.id)}: ${box.label}, ${box.answer.replace(/_/g, ' ')}, page ${box.page + 1}`}
                  style={{
                    top: pct(box.box.top),
                    left: pct(box.box.left),
                    width: pct(box.box.right - box.box.left),
                    height: pct(box.box.bottom - box.box.top),
                  }}
                  onClick={() => onSelect(box.id)}
                >
                  <span className="box__n" aria-hidden="true">
                    {String(numbers.get(box.id)).padStart(2, '0')}
                  </span>
                  {box.id === selectedId && (
                    <span className="box__sel" aria-hidden="true">
                      {numbers.get(box.id)} {box.label}
                    </span>
                  )}
                  <span className="box__tip" aria-hidden="true">
                    <strong>{box.label}</strong>
                    <span>
                      {box.answer.replace(/_/g, ' ')}
                      {box.severity ? ` / ${box.severity}` : ''}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <div className="docpane__empty">
              <p className="docpane__empty-title">
                {attached ? 'No page preview' : 'Re-attach the file to show the page'}
              </p>
              <p className="help">
                {attached
                  ? 'This build does not draw the document page. The file stays in this tab and is never uploaded for previewing.'
                  : 'The text and this report were restored from this tab. The file itself is not kept, so the page cannot be drawn.'}
              </p>
              {!attached && (
                <div className="docpane__attach">
                  <label className="label" htmlFor="reattach-file">Re-attach the CV file</label>
                  <input
                    id="reattach-file"
                    type="file"
                    accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    onChange={event => {
                      const next = event.currentTarget.files?.[0]
                      if (next) onReattach(next)
                      event.currentTarget.value = ''
                    }}
                  />
                </div>
              )}
            </div>
          )}

          {!hasImage && drawable.length > 0 && (
            <div className="docpane__index">
              <p className="label">Boxes reported</p>
              <ul className="docpane__list">
                {drawable.map(box => (
                  <li key={box.id}>
                    <button
                      type="button"
                      aria-pressed={box.id === selectedId}
                      onClick={() => onSelect(box.id)}
                    >
                      <span className="docpane__list-label">
                        <span className="docpane__list-n" aria-hidden="true">
                          {String(numbers.get(box.id)).padStart(2, '0')}
                        </span>
                        {box.label}
                      </span>
                      <span>Page {box.page + 1}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
