import type { StructureFinding } from '../../api/schema'
import { SEVERITY_TEXT, bandOf, scoreText, structureScore } from './summary'

/* Structure findings. One row per check: what it is, how bad it is, what it
 * cost, where it is, and the score that leaves the row with. A check with a
 * page is a select target and moves the document pane to it. */
export default function StructureFindings({
  findings,
  selectedId,
  onSelect,
}: {
  findings: StructureFinding[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  if (!findings.length) {
    return <p className="help">No structure checks were returned for this report.</p>
  }

  return (
    <ul className="srows">
      {findings.map(finding => {
        const id = `structure:${finding.id}`
        const selected = id === selectedId
        const located = finding.severity !== 'pass' && finding.page != null
        const score = structureScore(finding)

        const body = (
          <>
            <span className="srow__name">{finding.label}</span>
            <span className="srow__meta">
              <span className="srow__severity" data-severity={finding.severity}>
                {SEVERITY_TEXT[finding.severity]}
              </span>
              {finding.severity !== 'unassessable' && (
                <span>{finding.points_lost === 0 ? 'No points lost' : `${finding.points_lost} points lost`}</span>
              )}
              {located && <span>Page {finding.page! + 1}</span>}
            </span>
            <span className="srow__score" data-band={bandOf(score) ?? undefined}>
              {scoreText(score)}
            </span>
          </>
        )

        return (
          <li
            className="srow"
            key={finding.id}
            data-severity={finding.severity}
            data-selected={selected}
          >
            {located ? (
              <button
                type="button"
                className="srow__head"
                aria-pressed={selected}
                aria-label={`${finding.label}. ${SEVERITY_TEXT[finding.severity]}. ${
                  finding.points_lost
                } points lost. Page ${finding.page! + 1}. Score ${scoreText(score)}.`}
                onClick={() => onSelect(id)}
                onFocus={() => onSelect(id)}
              >
                {body}
              </button>
            ) : (
              <div className="srow__head">{body}</div>
            )}
          </li>
        )
      })}
    </ul>
  )
}
