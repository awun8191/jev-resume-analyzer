import { useEffect, useRef } from 'react'
import type { RefObject } from 'react'
import type { AnalysisReport, Finding } from '../../api/schema'
import Warnings from '../../components/Warnings'
import {
  ANSWER_GLYPH,
  ANSWER_ORDER,
  ANSWER_TEXT,
  SUBSCORES,
  dimensionRows,
  percent,
} from './summary'
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
  const dimensions = dimensionRows(r.findings)
  const unscored = o.questions_total - o.questions_answered
  const selectedRef = useRef<HTMLElement>(null)
  const firstRun = useRef(true)

  /* A box click selects a finding. Bring that finding into view, but leave the
   * first render alone so a restored report does not jump. */
  useEffect(() => {
    if (firstRun.current) {
      firstRun.current = false
      return
    }
    selectedRef.current?.scrollIntoView?.({ block: 'nearest' })
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

      <section className="score" aria-labelledby="rating-title">
        <div className="score__main">
          <h2 className="label score__label" id="rating-title">Overall rating</h2>
          {o.rating ? (
            <>
              <p className="score__value">
                <span>{o.rating.value}</span>
                <small>/ {o.rating.scale_max}</small>
              </p>
              <p className="score__caption">{o.rating.label}</p>
              <p className="help">
                Scale {o.rating.scale_min} to {o.rating.scale_max}. {o.rating.basis}
              </p>
            </>
          ) : (
            <>
              <p className="score__none">Not scored yet</p>
              <p className="help">
                No scoring map is approved or calibrated, so this report carries no rating. Nothing
                here is inferred from the findings below.
              </p>
            </>
          )}
        </div>

        <div className="score__coverage">
          <p className="label">Coverage</p>
          <dl className="cov">
            <div><dt>Prepared</dt><dd>{o.questions_total}</dd></div>
            <div><dt>Returned</dt><dd>{o.questions_answered}</dd></div>
            <div><dt>Assessable</dt><dd>{o.questions_assessable}</dd></div>
          </dl>
          <p className="help">
            Assessable means a present or absent answer.
            {unscored > 0 ? ` ${unscored} question${unscored === 1 ? '' : 's'} not returned.` : ''}
          </p>
        </div>
      </section>

      <section className="section" aria-labelledby="subscores-title">
        <div className="section__head">
          <h2 className="section__title" id="subscores-title">Sub-scores</h2>
        </div>
        <ul className="subscores">
          {SUBSCORES.map(slot => (
            <li className="subscore" key={slot.key}>
              <p className="label">{slot.label}</p>
              <p className="subscore__value">Pending</p>
              <p className="help">Not sent by the analysis yet. No value is inferred.</p>
            </li>
          ))}
        </ul>
      </section>

      <Warnings warnings={r.warnings} title="Analysis limitations" />

      <section className="section" aria-labelledby="dims-title">
        <div className="section__head">
          <h2 className="section__title" id="dims-title">Dimension breakdown</h2>
          <p className="section__note">Counts, not scores</p>
        </div>
        {dimensions.length ? (
          <ul className="dims">
            {dimensions.map(row => (
              <li className="dim" key={row.dimension}>
                <p className="dim__name">{row.dimension}</p>
                <ul className="dim__counts">
                  {ANSWER_ORDER.map(answer => (
                    <li key={answer} className={row.counts[answer] === 0 ? 'is-zero' : undefined}>
                      <span className="dim__glyph" aria-hidden="true">{ANSWER_GLYPH[answer]}</span>
                      <span className="dim__n">{row.counts[answer]}</span>
                      <span className="dim__s">{ANSWER_TEXT[answer]}</span>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        ) : (
          <p className="help">No findings were returned, so there is nothing to count.</p>
        )}
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

      <div className="actions">
        <p className="actions__note">
          Editing clears this report. A new analysis needs an explicit submission.
        </p>
        <button className="btn btn--primary" onClick={onEdit}>Edit text and run a new review</button>
      </div>
    </section>
  )
}
