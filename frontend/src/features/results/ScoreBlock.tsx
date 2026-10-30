import type { Scores } from '../../api/schema'
import { bandOf } from './summary'

/* A score as the page reads it: the numeral in its band colour, a small unit,
 * and the band word in plain text. A null score is the word Not scored in ink,
 * with no numeral behind it. */
function Value({
  value,
  band,
  size,
}: {
  value: number | null
  band: string | null
  size: 'total' | 'split'
}) {
  if (value === null) {
    return <span className={`score__none score__none--${size}`}>Not scored</span>
  }
  return (
    <span className={`score__figure score__figure--${size}`}>
      <span className="score__value" data-band={bandOf(value) ?? undefined}>{value}</span>
      <span className="score__unit">/100</span>
      {band && <span className="score__band">{band}</span>}
    </span>
  )
}

/* The whole verdict: one total line, then the two halves it is built from.
 * Nothing else lives here. */
export default function ScoreBlock({ scores }: { scores: Scores }) {
  return (
    <section className="score" aria-label="Score">
      <p className="score__total">
        <Value value={scores.total.value} band={scores.total.band} size="total" />
      </p>

      <dl className="score__split">
        <div className="score__half" data-owner="structure">
          <dt className="label">Structure</dt>
          <dd>
            <Value value={scores.structure.value} band={scores.structure.band} size="split" />
          </dd>
        </div>
        <div className="score__half" data-owner="content">
          <dt className="label">Content</dt>
          <dd>
            <Value value={scores.content.value} band={scores.content.band} size="split" />
          </dd>
        </div>
      </dl>
    </section>
  )
}
