import { useEffect, useRef, useState } from 'react'
import type { AnalysisReport } from '../../api/schema'
import Warnings from '../../components/Warnings'
import Dimensions from './Dimensions'
import Findings from './Findings'
import StructureFindings from './StructureFindings'
import './report.css'

/* The body of the report, below the summary: dimensions, findings, structure
 * checks, limitations and request detail. Everything that a user does not need
 * to read the score is behind one disclosure, and nothing with a null value is
 * ever hidden behind one. */
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
  const structureRef = useRef<HTMLLIElement>(null)
  const firstRun = useRef(true)
  const [dimsOpen, setDimsOpen] = useState(false)
  const [structureOpen, setStructureOpen] = useState(r.structure_findings.length === 0)

  const openDims = dimsOpen || r.dimensions.length === 0
  const structureScore = r.scores.structure.value

  /* A box click selects a finding. Open the group that holds it and bring it
   * into view, but leave the first render alone so a restored report does not
   * jump. */
  useEffect(() => {
    if (selectedId?.startsWith('structure:')) setStructureOpen(true)
    if (firstRun.current) {
      firstRun.current = false
      return
    }
    if (!selectedId?.startsWith('structure:')) return
    structureRef.current?.scrollIntoView?.({ block: 'nearest' })
  }, [selectedId])

  return (
    <div className="report-body">
      <section className="section" aria-labelledby="dims-title">
        <h2 className="section__title" id="dims-title">
          <button
            type="button"
            className="section__toggle"
            aria-expanded={openDims}
            aria-controls="dims-body"
            onClick={() => setDimsOpen(value => !value)}
          >
            <span>All dimensions</span>
            <span className="section__note">{r.dimensions.length} rows</span>
            <span className="disclosure__mark" aria-hidden="true" />
          </button>
        </h2>
        <div id="dims-body" hidden={!openDims}>
          <Dimensions rows={r.dimensions} />
        </div>
      </section>

      <section className="section" aria-labelledby="findings-title">
        <div className="section__head">
          <h2 className="section__title" id="findings-title" tabIndex={-1}>
            Findings
          </h2>
          <p className="section__note">{r.findings.length} total</p>
        </div>
        <Findings findings={r.findings} selectedId={selectedId} onSelect={onSelect} />
      </section>

      <section className="section" aria-labelledby="structure-title">
        <h2 className="section__title" id="structure-title">
          <button
            type="button"
            className="section__toggle"
            aria-expanded={structureOpen}
            aria-controls="structure-body"
            onClick={() => setStructureOpen(value => !value)}
          >
            <span>Structure findings</span>
            <span className="section__note">
              {r.structure_findings.length} checks ·{' '}
              {structureScore === null ? 'Not scored' : `${structureScore} / 100`}
            </span>
            <span className="disclosure__mark" aria-hidden="true" />
          </button>
        </h2>
        <div id="structure-body" hidden={!structureOpen}>
          <StructureFindings
            findings={r.structure_findings}
            selectedId={selectedId}
            onSelect={onSelect}
            nodeRef={structureRef}
          />
        </div>
      </section>

      <Warnings warnings={r.warnings} title="Analysis limitations" />

      <details className="disclosure">
        <summary>
          <span>Request details</span>
          <span className="disclosure__mark" aria-hidden="true" />
        </summary>
        <div className="disclosure__body">
          <dl className="kv">
            <div><dt>Analysis ID</dt><dd>{r.analysis_id}</dd></div>
            <div><dt>Rubric</dt><dd>{r.rubric_version}</dd></div>
            <div><dt>Model</dt><dd>{r.model}</dd></div>
            <div>
              <dt>Duration</dt>
              <dd>{r.metrics?.duration_ms == null ? 'Not reported' : `${(r.metrics.duration_ms / 1000).toFixed(2)} s`}</dd>
            </div>
            <div>
              <dt>Tokens in / out</dt>
              <dd>{r.metrics?.input_tokens ?? 'Not reported'} / {r.metrics?.output_tokens ?? 'Not reported'}</dd>
            </div>
            <div>
              <dt>Reported cost</dt>
              <dd>{r.metrics?.cost_usd == null ? 'Not reported' : `$${r.metrics.cost_usd.toFixed(6)}`}</dd>
            </div>
          </dl>
        </div>
      </details>

      <div className="actions">
        <p className="actions__note">Editing clears this report.</p>
        <button className="btn btn--primary" onClick={onEdit}>Edit text and run a new review</button>
      </div>
    </div>
  )
}
