import type { RefObject } from 'react'
import type { StructureFinding } from '../../api/schema'
import { SEVERITY_TEXT } from './summary'

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
    return <p className="help">No structure checks were returned for this report.</p>
  }

  return (
    <ul className="sfinds">
      {findings.map(finding => {
        const id = `structure:${finding.id}`
        const selected = id === selectedId
        const located = finding.severity !== 'pass' && finding.page != null
        const head = (
          <>
            <span className="sfind__label">{finding.label}</span>
            <span className="sfind__severity chip" data-severity={finding.severity}>
              {SEVERITY_TEXT[finding.severity]}
            </span>
            <span className="sfind__page">
              {located ? `Page ${finding.page! + 1}` : 'No location'}
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
            </p>
          </li>
        )
      })}
    </ul>
  )
}
