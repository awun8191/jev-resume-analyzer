import type { Overview, Scores } from '../../api/schema'
import {
  MODE_LABEL,
  contentReasonText,
  countsText,
  coveragePercent,
  rangeText,
  structureReasonText,
  totalRange,
} from './summary'

function ScoreValue({ value, valueClass }: { value: number | null; valueClass: string }) {
  if (value === null) return <span className="score__none">Not scored</span>
  return (
    <span className={valueClass}>
      <span>{value}</span>
      <small>/ 100</small>
    </span>
  )
}

/* Total score, one compact block: value, band, mode, range, coverage. Every
 * missing value is a word, and a missing half keeps its reason in place. */
export default function ScoreBlock({ scores, overview }: { scores: Scores; overview: Overview }) {
  const range = totalRange(scores)
  const structureReason = structureReasonText(scores.structure)
  const contentReason = contentReasonText(scores)

  return (
    <section className="score" aria-labelledby="score-title" data-mode={scores.total.mode}>
      <div className="score__head">
        <div>
          <h2 className="label score__label" id="score-title">Total score</h2>
          <ScoreValue value={scores.total.value} valueClass="score__value" />
          {scores.total.band && <p className="score__band">{scores.total.band}</p>}
        </div>
        <div className="score__flags">
          {scores.total.mode !== 'combined' && (
            <p className="label">{MODE_LABEL[scores.total.mode]}</p>
          )}
          {range && range[0] !== range[1] && (
            <p className="subscore__reason">Range {rangeText(range)}</p>
          )}
        </div>
      </div>

      <dl className="score__cov">
        <div>
          <dt>Covered</dt>
          <dd>{coveragePercent(scores)}</dd>
        </div>
        <div>
          <dt>Decided</dt>
          <dd>{scores.content.assessed_weight}<small>/100</small></dd>
        </div>
        <div>
          <dt>Layout</dt>
          <dd>{scores.structure.assessed_weight}<small>/100</small></dd>
        </div>
      </dl>
      <p className="score__counts">{countsText(overview)}</p>

      {structureReason && <p className="score__reason">{structureReason}</p>}
      {contentReason && <p className="score__reason">{contentReason}</p>}
      {scores.structure.value === null && scores.structure.reason && (
        <p className="score__code">Layout reason: <code>{scores.structure.reason}</code></p>
      )}
    </section>
  )
}
