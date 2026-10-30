const STEPS = ['Upload', 'Check text', 'Report'] as const

export default function StageBar({
  stage,
  hasExtraction,
  fileName,
}: {
  stage: string
  hasExtraction: boolean
  fileName: string
}) {
  const current = stage === 'result' ? 2 : hasExtraction ? 1 : 0
  return (
    <nav className="progress" aria-label="Review progress">
      <ol className="progress__steps">
        {STEPS.map((label, i) => (
          <li key={label} aria-current={i === current ? 'step' : undefined}>
            <span className="progress__n" aria-hidden="true">{`0${i + 1}`}</span>
            <span>{label}</span>
            {i === current && <span className="progress__mark" aria-hidden="true" />}
          </li>
        ))}
      </ol>
      <p className="progress__file">{fileName || 'No document'}</p>
    </nav>
  )
}
