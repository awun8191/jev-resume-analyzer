import { useEffect, useRef } from 'react'
import type { RefObject } from 'react'
import type { AnalysisReport, Finding } from '../../api/schema'
import Warnings from '../../components/Warnings'
import { ANSWER_GLYPH, ANSWER_ORDER, ANSWER_TEXT, percent } from './summary'
import Dimensions from './Dimensions'
import ScoreBlock from './ScoreBlock'
import StructureFindings from './StructureFindings'
import './report.css'

function FindingRow({
  finding: f,
  index,
  selected,
  onSelect,
  nodeRef,
}: {
  finding: Finding
  index: number
  selected: boolean
  onSelect: (id: string) => void
  nodeRef: RefObject<HTMLElement>
}) {
  const located = f.page != null && f.box != null
  return (
    <article className="finding" data-selected={selected} ref={selected ? nodeRef : undefined}>
      <div className="finding__head">
        <h4 className="finding__dim">
          <button
            type="button"
            className="finding__select"
            aria-pressed={selected}
            aria-label={`${f.dimension}. ${located ? `Page ${f.page! + 1}.` : 'No page location.'} ${ANSWER_TEXT[f.answer]}.`}
            onClick={() => onSelect(f.question_id)}
            onFocus={() => onSelect(f.question_id)}
          >
            <span className="finding__index" aria-hidden="true">{String(index).padStart(2, '0')}</span>
            <span>{f.dimension}</span>
            <span className="finding__loc" aria-hidden="true">
              {located ? `Page ${f.page! + 1}` : 'No location'}
            </span>
          </button>
        </h4>
        <p className="state">
          <span className="state__glyph" aria-hidden="true">{ANSWER_GLYPH[f.answer]}</span>
          {ANSWER_TEXT[f.answer]}
        </p>
      </div>

      {f.source_text && <blockquote className="finding__source">{f.source_text}</blockquote>}

      <div className="finding__question">
        <p className="label">Question</p>
        <p>{f.question}</p>
      </div>

      <details className="disclosure">
        <summary>
          <span>Question and answer detail</span>
          <span className="disclosure__mark" aria-hidden="true" />
        </summary>
        <div className="disclosure__body">
          <p className="help">
            {f.assessment_level === 'bullet' ? 'Bullet assessment' : 'Whole document'} /{' '}
            {f.source === 'document_metadata' ? 'Metadata check' : 'Jev'} / <code>{f.question_id}</code>
          </p>

          <dl className="kv">
            <div>
              <dt>Answer</dt>
              <dd>{ANSWER_TEXT[f.answer]} <code>({f.answer})</code></dd>
            </div>
            <div>
              <dt>Page location</dt>
              <dd>{located ? `Page ${f.page! + 1}` : 'Not reported'}</dd>
            </div>
            {f.severity && (
              <div><dt>Severity</dt><dd>{f.severity}</dd></div>
            )}
            <div>
              <dt>Provider confidence</dt>
              <dd>{f.confidence === null ? 'Not reported' : percent(f.confidence)}</dd>
            </div>
          </dl>

          <p className="label">Answer criteria</p>
          <ol className="criteria">
            {f.criteria.map((criterion, i) => (
              <li key={i}>
                <span className="n" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>
                <span>{criterion}</span>
              </li>
            ))}
          </ol>

          <p className="label">Provider answer probabilities</p>
          {f.probabilities ? (
            <dl className="dist">
              {ANSWER_ORDER.map(answer => (
                <div className="dist__row" key={answer} data-current={f.answer === answer}>
                  <dt>{ANSWER_TEXT[answer]}</dt>
                  <dd className="dist__track" aria-hidden="true">
                    <span className="dist__fill" style={{ width: `${f.probabilities![answer] * 100}%` }} />
                  </dd>
                  <dd className="dist__pct">{percent(f.probabilities![answer])}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p>Not reported by the provider.</p>
          )}
          <p className="help">
            These describe uncertainty in the answer, not hiring likelihood or CV quality.
          </p>

          {f.rubric_explanation && (
            <div className="rubric">
              <p className="label">Rubric explanation</p>
              <p className="rubric__text">{f.rubric_explanation.text}</p>
              <p className="help">Predefined rubric text / {f.rubric_explanation.template_ref}</p>
            </div>
          )}
        </div>
      </details>
    </article>
  )
}

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
  const o = r.overview
  const selectedRef = useRef<HTMLElement>(null)
  const structureRef = useRef<HTMLLIElement>(null)
  const firstRun = useRef(true)

  /* A box click selects a finding. Bring that finding into view, but leave the
   * first render alone so a restored report does not jump. */
  useEffect(() => {
    if (firstRun.current) {
      firstRun.current = false
      return
    }
    const target = selectedId?.startsWith('structure:') ? structureRef.current : selectedRef.current
    target?.scrollIntoView?.({ block: 'nearest' })
  }, [selectedId])

  return (
    <section aria-labelledby="report-title">
      <header className="stage__head">
        <span className="stage__index">03 / Report</span>
        <h1 className="stage__title" tabIndex={-1} id="report-title">The report.</h1>
        <p className="stage__lead">
          Findings with their source passages, criteria and uncertainty. No generated advice.
        </p>
      </header>

      <ScoreBlock scores={r.scores} overview={o} />

      <section className="section" aria-labelledby="dims-title">
        <div className="section__head">
          <h2 className="section__title" id="dims-title">Dimensions</h2>
          <p className="section__note">Scored rows by owner</p>
        </div>
        <Dimensions rows={r.dimensions} />
      </section>

      <section className="section" aria-labelledby="findings-title">
        <div className="section__head">
          <h2 className="section__title" id="findings-title">Findings</h2>
          <p className="section__note">{r.findings.length} returned</p>
        </div>
        {!r.findings.length && (
          <p className="help">No findings were returned. Review the limitations above.</p>
        )}
        {(['general_review', 'job_alignment'] as const).map(scope => {
          const findings = r.findings.filter(f => f.scope === scope)
          if (!findings.length) return null
          return (
            <div className="group" key={scope}>
              <h3 className="group__title">
                {scope === 'general_review' ? 'General review' : 'Job alignment'}
              </h3>
              {findings.map(finding => {
                const index = r.findings.indexOf(finding) + 1
                const selected = finding.question_id === selectedId
                return (
                  <FindingRow
                    key={finding.question_id}
                    finding={finding}
                    index={index}
                    selected={selected}
                    onSelect={onSelect}
                    nodeRef={selectedRef}
                  />
                )
              })}
            </div>
          )
        })}
      </section>

      <details className="disclosure request">
        <summary>
          <span>Request details and metrics</span>
          <span className="disclosure__mark" aria-hidden="true" />
        </summary>
        <div className="disclosure__body">
          <dl className="kv">
            <div><dt>Request-scoped ID</dt><dd>{r.analysis_id}</dd></div>
            <div><dt>Rubric</dt><dd>{r.rubric_version}</dd></div>
            <div><dt>Model</dt><dd>{r.model}</dd></div>
            <div>
              <dt>Duration</dt>
              <dd>{r.metrics?.duration_ms == null ? 'Not reported' : `${(r.metrics.duration_ms / 1000).toFixed(2)} s`}</dd>
            </div>
            <div>
              <dt>Input and output tokens</dt>
              <dd>{r.metrics?.input_tokens ?? 'Not reported'} / {r.metrics?.output_tokens ?? 'Not reported'}</dd>
            </div>
            <div>
              <dt>Reported cost</dt>
              <dd>{r.metrics?.cost_usd == null ? 'Not reported' : `$${r.metrics.cost_usd.toFixed(6)}`}</dd>
            </div>
          </dl>
        </div>
      </details>

      <section className="section" aria-labelledby="structure-title">
        <div className="section__head">
          <h2 className="section__title" id="structure-title">Structure findings</h2>
          <p className="section__note">{r.structure_findings.length} checks</p>
        </div>
        <StructureFindings
          findings={r.structure_findings}
          selectedId={selectedId}
          onSelect={onSelect}
          nodeRef={structureRef}
        />
      </section>

      <Warnings warnings={r.warnings} title="Analysis limitations" />

      <div className="actions">
        <p className="actions__note">
          Editing clears this report. A new analysis needs an explicit submission.
        </p>
        <button className="btn btn--primary" onClick={onEdit}>Edit text and run a new review</button>
      </div>
    </section>
  )
}
