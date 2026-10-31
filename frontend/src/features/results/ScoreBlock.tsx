import type { Scores } from '../../api/schema'
import { bandOf } from './summary'

/* A score as the page reads it: the numeral in its band colour and a small
 * unit. The numeral carries the verdict, so the band word is not repeated. A
 * null score is the word Not scored in ink, with no numeral behind it. */
function Value({
  value,
  size,
}: {
  value: number | null
  size: 'total' | 'split'
}) {
  if (value === null) {
    return <span className={`score__none score__none--${size}`}>Not scored</span>
  }
  return (
    <span className={`score__figure score__figure--${size}`}>
      <span className="score__value" data-band={bandOf(value) ?? undefined}>{value}</span>
      <span className="score__unit">/100</span>
    </span>
  )
}

const STRUCTURE_NULL: Record<string, string> = {
  unsupported_format: 'PDF only',
  provider_error: 'Layout check failed',
  render_failed: 'Page render failed',
  page_not_readable: 'Page unreadable',
  page_empty: 'Page empty',
  insufficient_evidence: 'Not enough evidence',
  no_file: 'No file',
}

/* The whole verdict: one total line, then the two halves it is built from.
 * Nothing else lives here. */
export default function ScoreBlock({ scores }: { scores: Scores }) {
  const structureReason =
    scores.structure.value === null ? STRUCTURE_NULL[scores.structure.reason ?? ''] : null
  return (
    <section className="score" aria-label="Score">
      <p className="score__total">
        <Value value={scores.total.value} size="total" />
      </p>

      <dl className="score__split">
        <div className="score__half" data-owner="structure">
          <dt className="label">Structure</dt>
          <dd>
            <Value value={scores.structure.value} size="split" />
            {structureReason && <p className="score__note">{structureReason}</p>}
          </dd>
        </div>
        <div className="score__half" data-owner="content">
          <dt className="label">Content</dt>
          <dd>
            <Value value={scores.content.value} size="split" />
          </dd>
        </div>
      </dl>
    </section>
  )
}
