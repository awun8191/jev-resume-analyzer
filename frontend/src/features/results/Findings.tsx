import { useState } from 'react'
import type { Dimension, Finding } from '../../api/schema'
import {
  ANSWER_ORDER, ANSWER_TEXT, FINDING_SCORE, bandOf, earnedPoints, findingLabel,
  findingStakes, groupFindings, percent, scoreText,
} from './summary'

/* The three facts behind one row: what counts as an answer, the answer, and
 * how sure the provider was. The prompt stays out of the report. */
function Detail({ finding: f, hidden }: { finding: Finding; hidden: boolean }) {
  return (
    <div className="fdetail" id={`finding-detail-${f.question_id}`} hidden={hidden}>
      <div className="fdetail__criteria">
        <p className="label">What counts</p>
        <ul className="criteria">
          {f.criteria.map((criterion, i) => (
            <li key={i}>{criterion}</li>
          ))}
        </ul>
      </div>

      <div className="fdetail__answer">
        <p className="label">Answer</p>
        <p>{ANSWER_TEXT[f.answer]}</p>
      </div>

      <div className="fdetail__dist">
        <p className="label">Probability per answer</p>
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
          <p className="dist__none">Not reported by the provider.</p>
        )}
      </div>
    </div>
  )
}

function Row({
  finding: f,
  stake,
  selected,
  open,
  onToggle,
  onSelect,
}: {
  finding: Finding
  stake: number | undefined
  selected: boolean
  open: boolean
  onToggle: () => void
  onSelect: (id: string) => void
}) {
  const score = FINDING_SCORE[f.answer]
  const earned = stake === undefined ? null : earnedPoints(f.answer, stake)

  return (
    <li className="frow" data-selected={selected} data-open={open}>
      <button
        type="button"
        className="frow__head"
        id={`finding-row-${f.question_id}`}
        aria-expanded={open}
        aria-controls={`finding-detail-${f.question_id}`}
        aria-current={selected ? 'true' : undefined}
        onClick={() => {
          onSelect(f.question_id)
          onToggle()
        }}
        onFocus={() => onSelect(f.question_id)}
      >
        <span className="frow__name">{findingLabel(f.dimension, f.question_id)}</span>
        <span className="frow__meta">
          <span className="frow__state">{ANSWER_TEXT[f.answer]}</span>
          {stake !== undefined && (
            <span className="frow__stake">
              {earned === null ? '\u2014' : earned} of {stake} pts
            </span>
          )}
        </span>
        <span className="frow__score" data-band={bandOf(score) ?? undefined}>
          {scoreText(score)}
        </span>
        <span className="frow__mark" aria-hidden="true" />
      </button>
      <Detail finding={f} hidden={!open} />
    </li>
  )
}

/* Content findings. One row per finding, grouped by dimension and always
 * visible. The row carries its own score and its own stake; the question,
 * criteria, answer and probabilities open in place, inside the list. */
export default function Findings({
  findings,
  dimensions,
  selectedId,
  onSelect,
}: {
  findings: Finding[]
  dimensions: Dimension[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  const [openId, setOpenId] = useState<string | null>(null)

  if (!findings.length) {
    return <p className="help">No findings were returned.</p>
  }

  const stakes = findingStakes(findings, dimensions)

  return (
    <div className="groups">
      {groupFindings(findings).map(group => (
        <div className="group" key={group.key}>
          <h3 className="group__title">
            {group.dimension}
            {group.scope === 'job_alignment' && <span className="group__scope">Job posting</span>}
          </h3>
          <ul className="frows">
            {group.findings.map(finding => (
              <Row
                key={finding.question_id}
                finding={finding}
                stake={stakes.get(finding.question_id)}
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
  )
}
