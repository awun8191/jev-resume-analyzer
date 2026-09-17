import type { Warning } from '../api/schema'
export default function Warnings({ warnings, title }: { warnings: Warning[]; title: string }) {
  if (!warnings.length) return null
  return <aside className="warning-box" aria-label={title}><h2>{title}</h2>
    <ul>{warnings.map((w, i) => <li key={`${w.code}-${i}`}>{w.message} <code>{w.code}</code></li>)}</ul></aside>
}
