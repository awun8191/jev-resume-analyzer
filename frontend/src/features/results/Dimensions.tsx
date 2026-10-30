import type { Dimension } from '../../api/schema'
import { groupDimensions } from './summary'

const OWNER_LABEL = { content: 'Content', structure: 'Structure' } as const

function Row({ row }: { row: Dimension }) {
  return (
    <li className="dim" data-owner={row.owner}>
      <p className="dim__name">{row.label}</p>
      <p className="dim__meta">{row.weight} of 100 points</p>
      {row.value === null ? (
        <p className="dim__value dim__value--none">Not scored</p>
      ) : (
        <p className="dim__value">
          <span>{row.value}</span>
          <small>/ 100</small>
        </p>
      )}
    </li>
  )
}

/* One group per owner. Content rows and structure rows never mix, and a null
 * value stays a word rather than a zero. */
export default function Dimensions({ rows }: { rows: Dimension[] }) {
  const groups = groupDimensions(rows)
  if (!rows.length) {
    return <p className="help">No dimension rows were returned for this report.</p>
  }
  return (
    <>
      {(['content', 'structure'] as const).map(owner => {
        const group = groups[owner]
        if (!group.length) return null
        return (
          <div className="dim-group" key={owner} data-owner={owner}>
            <h3 className="group__title">{OWNER_LABEL[owner]}</h3>
            <ul className="dims">
              {group.map(row => <Row key={row.key} row={row} />)}
            </ul>
          </div>
        )
      })}
    </>
  )
}
