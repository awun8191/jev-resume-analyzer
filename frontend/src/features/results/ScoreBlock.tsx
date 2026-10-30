import type { Overview, Scores } from '../../api/schema'
import {
  MODE_LABEL,
  contentReasonText,
  coverageText,
  modeNote,
  rangeText,
  structureReasonText,
  totalRange,
} from './summary'

function ScoreValue({ value }: { value: number | null }) {
  if (value === null) return <span className="score__none">Not scored</span>
  return (
    <span className="score__value">
      <span>{value}</span>
      <small>/ 100</small>
    </span>
  )
}

/* Total first, then the two sub-scores in the same order as the rubric. Every
 * missing value is a word, and every reason is printed in plain language. */
export default function ScoreBlock({ scores, overview }: { scores: Scores; overview: Overview }) {
  const range = totalRange(scores)
  const structureReason = structureReasonText(scores.structure)
  const contentReason = contentReasonText(scores)
  const unscored = overview.questions_total - overview.questions_answered

  return (
    <>
      <section className="score" aria-labelledby="score-title" data-mode={scores.total.mode}>
        <div className="score__main">
          <h2 className="label score__label" id="score-title">Total score</h2>
          <ScoreValue value={scores.total.value} />
          <p className="score__mode">{MODE_LABEL[scores.total.mode]}</p>
          {scores.total.band && <p className="score__caption">{scores.total.band}</p>}
          {range && (
            <p className="score__range">
              Range {rangeText(range)}. The evidence is consistent with any value in that range.
            </p>
          )}
          <p className="help">{modeNote(scores.total.mode)}</p>
          {structureReason && <p className="score__reason">{structureReason}</p>}
          {contentReason && <p className="score__reason">{contentReason}</p>}
          {scores.structure.value === null && scores.structure.reason && (
            <p className="help">Layout reason reported by the server: <code>{scores.structure.reason}</code></p>
          )}
        </div>

        <div className="score__coverage">
          <p className="label">Coverage</p>
          <dl className="cov cov--scores">
            <div>
              <dt>Content</dt>
              <dd>{coverageText(scores)}</dd>
            </div>
            <div>
              <dt>Decided</dt>
              <dd>{scores.content.assessed_weight} / 100</dd>
            </div>
            <div>
              <dt>Layout</dt>
              <dd>{scores.structure.assessed_weight} / 100</dd>
            </div>
          </dl>
          <dl className="cov cov--counts">
            <div><dt>Prepared</dt><dd>{overview.questions_total}</dd></div>
            <div><dt>Returned</dt><dd>{overview.questions_answered}</dd></div>
            <div><dt>Assessable</dt><dd>{overview.questions_assessable}</dd></div>
          </dl>
          <p className="help">
            Assessable means a present or absent answer. A missing score is never shown as zero.
            {unscored > 0 ? ` ${unscored} question${unscored === 1 ? '' : 's'} not returned.` : ''}
          </p>
        </div>
      </section>

      <section className="section" aria-labelledby="subscores-title">
        <div className="section__head">
          <h2 className="section__title" id="subscores-title">Sub-scores</h2>
        </div>
        <ul className="subscores">
          <li className="subscore" data-owner="structure">
            <p className="label">Structure</p>
            <ScoreValue value={scores.structure.value} />
            <p className="subscore__band">
              {scores.structure.value === null ? 'Not scored' : (scores.structure.band ?? 'No band reported')}
            </p>
            {structureReason && <p className="help">{structureReason}</p>}
            <p className="help">Layout points assessed: {scores.structure.assessed_weight} of 100.</p>
          </li>
          <li className="subscore" data-owner="content">
            <p className="label">Content</p>
            <ScoreValue value={scores.content.value} />
            <p className="subscore__band">
              {scores.content.value === null ? 'Not scored' : (scores.content.band ?? 'No band reported')}
            </p>
            {contentReason && <p className="help">{contentReason}</p>}
            <p className="help">
              {scores.content.range
                ? `Range ${rangeText(scores.content.range)}. ${coverageText(scores)}.`
                : coverageText(scores)}
            </p>
          </li>
        </ul>
      </section>
    </>
  )
}
