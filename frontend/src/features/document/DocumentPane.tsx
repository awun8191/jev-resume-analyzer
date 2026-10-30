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
  source: 'section' | 'reported' | 'page'
}

const WHOLE_PAGE: FindingBox = { top: 0, bottom: 1, left: 0, right: 1 }

/* A content finding with a section uses the exact text layer box. A content
 * finding without one keeps the reported box. A structure check carries its own
 * page: with a box it is drawn, without one the page is outlined whole. Nothing
 * is drawn unless the data supports it. */
export function resolveBoxes(findings: BoxFinding[], pages: PagePreview[]): DrawableBox[] {
  const byPage = new Map<number, Map<string, { page: number; box: FindingBox }>>()
  const anywhere = new Map<string, Array<{ page: number; box: FindingBox }>>()

  pages.forEach((page, index) => {
    for (const section of page.sections ?? []) {
      const pageIndex = Number.isFinite(section.page) ? section.page : index
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
    if (finding.kind === 'structure') {
      if (finding.page == null) continue
      if (finding.box) resolved.push({ ...finding, page: finding.page, box: finding.box, source: 'reported' })
      else resolved.push({ ...finding, page: finding.page, box: WHOLE_PAGE, source: 'page' })
      continue
    }
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
  const boxRefs = useRef<Record<string, HTMLElement | null>>({})

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
              {showBoxes && pageBoxes.filter(box => box.source === 'page' && box.id === selectedId).map(box => (
                /* A check with a page and no box has no exact rectangle. The
                 * whole page is outlined, behind the other boxes, and the row
                 * in the report stays the click target. */
                <div
                  key={box.id}
                  ref={node => { boxRefs.current[box.id] = node }}
                  className="box box--page"
                  data-kind={box.kind}
                  data-selected={box.id === selectedId}
                  style={{ top: 0, left: 0, width: '100%', height: '100%' }}
                  aria-hidden="true"
                >
                  <span className="box__n">
                    {String(numbers.get(box.id)).padStart(2, '0')}
                  </span>
                </div>
              ))}
              {showBoxes && pageBoxes.filter(box => box.source !== 'page').map(box => (
                <button
                  key={box.id}
                  ref={node => { boxRefs.current[box.id] = node }}
                  type="button"
                  className="box"
                  data-source={box.source}
                  data-kind={box.kind}
                  aria-pressed={box.id === selectedId}
                  aria-label={`Finding ${numbers.get(box.id)}: ${box.label}, ${box.state}, page ${box.page + 1}`}
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
                      {box.state}
                      {box.severity ? ` / ${box.severity}` : ''}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <div className="docpane__empty">
              <p className="docpane__empty-title">
                {attached ? 'No page preview' : 'Re-attach the file'}
              </p>
              <p className="help">
                {attached
                  ? 'Scanned PDFs and DOCX files have no page image.'
                  : 'Report restored from this tab. The file is not kept, so the page cannot be drawn.'}
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
