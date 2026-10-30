import type { RefObject } from 'react'
import type { StructureFinding } from '../../api/schema'
import { SEVERITY_TEXT, percent } from './summary'

/* Layout checks. A check with a page is a click target and moves the document
 * pane to that page. A pass has no location, so it gets no target and no box. */
export default function StructureFindings({
  findings,
  selectedId,
  onSelect,
  nodeRef,
}: {
  findings: StructureFinding[]
  selectedId: string | null
  onSelect: (id: string) => void
  nodeRef: RefObject<HTMLLIElement>
}) {
  if (!findings.length) {
    return (
      <p className="help">
        No structure checks were returned. A content only report has no layout rows.
      </p>
    )
  }

  return (
    <ul className="sfinds">
      {findings.map((finding, index) => {
        const id = `structure:${finding.id}`
        const selected = id === selectedId
        const located = finding.severity !== 'pass' && finding.page != null
        const head = (
          <>
            <span className="sfind__index" aria-hidden="true">{String(index + 1).padStart(2, '0')}</span>
            <span className="sfind__label">{finding.label}</span>
            <span className="sfind__loc" aria-hidden="true">
              {located ? `Page ${finding.page! + 1}` : 'No location'}
            </span>
            <span className="sfind__severity" data-severity={finding.severity}>
              {SEVERITY_TEXT[finding.severity]}
            </span>
          </>
        )
        return (
          <li
            className="sfind"
            key={finding.id}
            data-severity={finding.severity}
            data-selected={selected}
            ref={selected ? nodeRef : undefined}
          >
            {located ? (
              <button
                type="button"
                className="sfind__select"
                aria-pressed={selected}
                aria-label={`${finding.label}. ${SEVERITY_TEXT[finding.severity]}. Page ${finding.page! + 1}.`}
                onClick={() => onSelect(id)}
                onFocus={() => onSelect(id)}
              >
                {head}
              </button>
            ) : (
              <div className="sfind__head">{head}</div>
            )}
            <p className="sfind__evidence">{finding.evidence}</p>
            <p className="sfind__meta">
              {finding.points_lost > 0 ? `${finding.points_lost} points lost` : 'No points lost'}
              {finding.confidence === null
                ? ' / confidence not reported'
                : ` / confidence ${percent(finding.confidence)}`}
            </p>
          </li>
        )
      })}
    </ul>
  )
}
