import type { Warning } from '../api/schema'

export default function Warnings({ warnings, title }: { warnings: Warning[]; title: string }) {
  if (!warnings.length) return null
  return (
    <aside className="notice" aria-label={title}>
      <h2 className="label">{title}</h2>
      <ul>
        {warnings.map((warning, i) => (
          <li key={`${warning.code}-${i}`}>
            <span>{warning.message}</span>
          </li>
        ))}
      </ul>
    </aside>
  )
}
