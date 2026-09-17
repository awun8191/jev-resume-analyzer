import type { AnalysisReport, AnswerCategory, Finding } from '../../api/schema'
import Warnings from '../../components/Warnings'
const labels: Record<AnswerCategory, string> = {
  present: 'Evidence present', absent: 'Evidence absent',
  not_applicable: 'Not applicable', unable_to_assess: 'Unable to assess',
}
const percent = (n: number) => `${(n * 100).toFixed(1)}%`
function FindingCard({ finding: f }: { finding: Finding }) {
  return <article className="finding"><div className="finding-heading"><h3>{f.dimension}</h3>
    <span className={`answer answer--${f.answer}`}>{labels[f.answer]}</span></div>
    <p className="question">{f.question}</p>
    <details><summary>Question & answer details</summary><div className="finding-detail">
      <p className="field-help">Full-document assessment · <code>{f.question_id}</code></p>
      <h4>Answer criteria</h4><ul>{f.criteria.map((criterion, i) => <li key={i}>{criterion}</li>)}</ul>
      <h4>Provider answer probabilities</h4>
      {f.probabilities ? <dl className="distribution">{Object.entries(f.probabilities).map(([key, value]) =>
        <div key={key}><dt>{labels[key as AnswerCategory]}</dt><dd>{percent(value)}</dd></div>)}</dl> : <p>Not reported by the provider.</p>}
      <p className="field-help">These describe uncertainty in the answer, not hiring likelihood or CV quality.</p>
      <p>Provider confidence: {f.confidence === null ? 'Not reported' : percent(f.confidence)}</p>
      {f.rubric_explanation && <div className="rubric-note"><h4>Rubric explanation</h4><p>{f.rubric_explanation.text}</p>
        <p className="field-help">Predefined rubric text · {f.rubric_explanation.template_ref}</p></div>}
    </div></details>
  </article>
}
export default function ResultStage({ report: r, fileName, onEdit }: { report: AnalysisReport; fileName: string; onEdit: () => void }) {
  const o = r.overview
  return <section aria-labelledby="report-title"><div className="intro compact"><p className="eyebrow">03 / Report</p>
    <h1 id="report-title">Your CV, examined.</h1><p className="filename">{fileName}</p>
    <p>Document-level findings, with the criteria and uncertainty in view. No bullet-level claims or generated advice.</p></div>
    <div className="overview"><div><p className="eyebrow">Assessment coverage</p><p className="stat">{o.questions_assessable} <span>/ {o.questions_total}</span></p>
      <p>questions assessable</p><p className="field-help">{o.questions_answered} answered · {o.questions_total - o.questions_answered} not returned</p></div>
      <div><p className="eyebrow">Communication rating</p>{o.rating ? <><p className="stat">{o.rating.value} <span>/ {o.rating.scale_max}</span></p>
        <p>{o.rating.label}</p><p className="field-help">Scale {o.rating.scale_min}–{o.rating.scale_max}. {o.rating.basis}</p></> : <><p className="no-rating">Not available</p><p className="field-help">No approved, sufficiently assessable rating was returned. No score is inferred.</p></>}</div></div>
    <Warnings warnings={r.warnings} title="Analysis limitations" />
    {!r.findings.length && <p className="empty-note">No findings were returned. Review the limitations above.</p>}
    {(['general_review', 'job_alignment'] as const).map(scope => {
      const findings = r.findings.filter(f => f.scope === scope)
      return findings.length ? <section className="finding-group" key={scope} aria-label={scope === 'general_review' ? 'General review' : 'Job alignment'}>
        <h2>{scope === 'general_review' ? 'General review' : 'Job alignment'}</h2>
        {findings.map(f => <FindingCard key={f.question_id} finding={f} />)}</section> : null
    })}
    <details className="request-details"><summary>Request details & metrics</summary><dl className="distribution">
      <div><dt>Request-scoped ID</dt><dd>{r.analysis_id}</dd></div><div><dt>Rubric</dt><dd>{r.rubric_version}</dd></div><div><dt>Model</dt><dd>{r.model}</dd></div>
      <div><dt>Duration</dt><dd>{r.metrics?.duration_ms == null ? 'Not reported' : `${(r.metrics.duration_ms / 1000).toFixed(2)} s`}</dd></div>
      <div><dt>Input / output tokens</dt><dd>{r.metrics?.input_tokens ?? 'Not reported'} / {r.metrics?.output_tokens ?? 'Not reported'}</dd></div>
      <div><dt>Reported cost</dt><dd>{r.metrics?.cost_usd == null ? 'Not reported' : `$${r.metrics.cost_usd.toFixed(6)}`}</dd></div>
    </dl></details>
    <button className="btn btn--primary" onClick={onEdit}>Edit text & run a new review</button>
    <p className="field-help">Editing clears this report. A new analysis requires an explicit submission.</p>
  </section>
}
