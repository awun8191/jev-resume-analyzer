import { useState } from 'react'
import type { Finding } from '../../api/schema'
import { ANSWER_GLYPH, ANSWER_ORDER, ANSWER_TEXT, findingLabel, groupFindings, percent } from './summary'

/* How many findings are visible before the rest is asked for. */
export const VISIBLE_FINDINGS = 3

function Detail({ finding: f, hidden }: { finding: Finding; hidden: boolean }) {
  const located = f.page != null && f.box != null
  return (
    <div className="finding__detail" id={`finding-detail-${f.question_id}`} hidden={hidden}>
      {f.source_text && <blockquote className="finding__source">{f.source_text}</blockquote>}

      <div className="finding__question">
        <p className="label">Question</p>
        <p>{f.question}</p>
      </div>

      <dl className="kv">
        <div>
          <dt>Answer</dt>
          <dd>{ANSWER_TEXT[f.answer]} <code>({f.answer})</code></dd>
        </div>
        <div>
          <dt>Page location</dt>
          <dd>{located ? `Page ${f.page! + 1}` : 'Not reported'}</dd>
        </div>
        {f.severity && <div><dt>Severity</dt><dd>{f.severity}</dd></div>}
        <div>
          <dt>Provider confidence</dt>
          <dd>{f.confidence === null ? 'Not reported' : percent(f.confidence)}</dd>
        </div>
      </dl>

      <div>
        <p className="label">Answer criteria</p>
        <ol className="criteria">
          {f.criteria.map((criterion, i) => (
            <li key={i}>
              <span className="n" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span>
              <span>{criterion}</span>
            </li>
          ))}
        </ol>
      </div>

      <div>
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
      </div>

      {f.rubric_explanation && (
        <div className="rubric">
          <p className="label">Rubric explanation</p>
          <p className="rubric__text">{f.rubric_explanation.text}</p>
        </div>
      )}
    </div>
  )
}

function Row({
  finding: f,
  index,
  selected,
  open,
  onToggle,
  onSelect,
}: {
  finding: Finding
  index: number
  selected: boolean
  open: boolean
  onToggle: () => void
  onSelect: (id: string) => void
}) {
  const located = f.page != null
  return (
    <li className="finding" data-selected={selected} data-open={open}>
      <button
        type="button"
        className="finding__row"
        id={`finding-row-${f.question_id}`}
        aria-expanded={open}
        aria-controls={`finding-detail-${f.question_id}`}
        aria-current={selected ? 'true' : undefined}
        aria-label={`${f.dimension}: ${findingLabel(f.dimension, f.question_id)}. ${
          located ? `Page ${f.page! + 1}.` : 'No page location.'
        } ${ANSWER_TEXT[f.answer]}.`}
        onClick={() => {
          onSelect(f.question_id)
          onToggle()
        }}
        onFocus={() => onSelect(f.question_id)}
      >
        <span className="finding__index" aria-hidden="true">
          {String(index).padStart(2, '0')}
        </span>
        <span className="finding__name">{findingLabel(f.dimension, f.question_id)}</span>
        <span className="finding__state">
          <span className="state">
            <span className="state__glyph" aria-hidden="true">{ANSWER_GLYPH[f.answer]}</span>
            {ANSWER_TEXT[f.answer]}
          </span>
        </span>
        <span className="finding__page" data-empty={!located}>
          {located ? `Page ${f.page! + 1}` : 'No location'}
        </span>
        <span className="finding__mark" aria-hidden="true" />
      </button>
      <Detail finding={f} hidden={!open} />
    </li>
  )
}

/* Content findings, grouped by dimension, three visible until asked for. One
 * line per finding; the question, criteria and distribution open on tap. */
export default function Findings({
  findings,
  selectedId,
  onSelect,
}: {
  findings: Finding[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  const [openId, setOpenId] = useState<string | null>(null)
  const [showAll, setShowAll] = useState(false)

  if (!findings.length) {
    return <p className="help">No findings were returned.</p>
  }

  const groups = groupFindings(findings)
  let budget = showAll ? findings.length : VISIBLE_FINDINGS
  const shown = groups
    .map(group => {
      const take = Math.max(0, Math.min(group.findings.length, budget))
      budget -= take
      return { ...group, visible: group.findings.slice(0, take) }
    })
    .filter(group => group.visible.length > 0)

  return (
    <>
      <div className="groups" id="findings-list">
        {shown.map(group => (
          <div className="group" key={group.key}>
            <div className="group__head">
              <h3 className="group__title">{group.dimension}</h3>
              <p className="group__count">
                {group.scope === 'job_alignment' ? 'Job posting · ' : ''}
                {group.visible.length} of {group.findings.length}
              </p>
            </div>
            <ul className="findings">
              {group.visible.map(finding => (
                <Row
                  key={finding.question_id}
                  finding={finding}
                  index={findings.indexOf(finding) + 1}
                  selected={finding.question_id === selectedId}
                  open={openId === finding.question_id}
                  onToggle={() =>
                    setOpenId(current => (current === finding.question_id ? null : finding.question_id))
                  }
                  onSelect={onSelect}
                />
              ))}
            </ul>
          </div>
        ))}
      </div>

      {findings.length > VISIBLE_FINDINGS && (
        <button
          type="button"
          className="jump"
          aria-expanded={showAll}
          aria-controls="findings-list"
          onClick={() => setShowAll(value => !value)}
        >
          {showAll ? 'Show fewer findings' : `Show all ${findings.length} findings`}
        </button>
      )}
    </>
  )
}
