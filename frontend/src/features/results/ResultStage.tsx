import { useEffect, useRef } from 'react'
import type { AnalysisReport } from '../../api/schema'
import Findings from './Findings'
import StructureFindings from './StructureFindings'
import './report.css'

/* The body of the report: content findings, then structure findings. Both
 * sections are open. A row opens in place; the sections never do. */
export default function ResultStage({
  report: r,
  onEdit,
  selectedId,
  onSelect,
}: {
  report: AnalysisReport
  onEdit: () => void
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  const body = useRef<HTMLDivElement>(null)
  const firstRun = useRef(true)

  /* A selection that came from the document pane brings its structure row into
   * view. The first render is left alone, so a restored report stays put. */
  useEffect(() => {
    if (firstRun.current) {
      firstRun.current = false
      return
    }
    if (!selectedId?.startsWith('structure:')) return
    body.current
      ?.querySelector<HTMLElement>('.srow[data-selected="true"]')
      ?.scrollIntoView?.({ block: 'nearest' })
  }, [selectedId])

  return (
    <div className="report-body" ref={body}>
      <section className="section" aria-labelledby="content-findings-title">
        <div className="section__head">
          <h2 className="section__title" id="content-findings-title" tabIndex={-1}>
            Content findings
          </h2>
        </div>
        <Findings
          findings={r.findings}
          dimensions={r.dimensions}
          selectedId={selectedId}
          onSelect={onSelect}
        />
      </section>

      <section className="section" aria-labelledby="structure-findings-title">
        <div className="section__head">
          <h2 className="section__title" id="structure-findings-title">
            Structure findings
          </h2>
        </div>
        <StructureFindings
          findings={r.structure_findings}
          selectedId={selectedId}
          onSelect={onSelect}
        />
      </section>

      <div className="actions">
        <p className="actions__note">Editing clears this report.</p>
        <button className="btn btn--primary" onClick={onEdit}>Edit text and run a new review</button>
      </div>
    </div>
  )
}
