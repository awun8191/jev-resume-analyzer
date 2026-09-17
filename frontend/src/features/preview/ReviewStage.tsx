import type { Extraction } from '../../api/schema'
import Warnings from '../../components/Warnings'
interface Props {
  fileName: string; extraction: Extraction; cvText: string; jobText: string; busy: boolean
  onTextChange: (text: string) => void; onJobChange: (text: string) => void; onAnalyse: () => Promise<void>
}
export default function ReviewStage(p: Props) {
  return <section aria-labelledby="preview-title">
    <div className="intro compact"><p className="eyebrow">02 / Check text</p><h1 id="preview-title">Make sure it reads right.</h1>
      <p>Fix reading order or missing text before analysis. This is the complete document, not reconstructed sections.</p></div>
    <div className="document-meta"><strong className="filename">{p.fileName}</strong><span>{p.extraction.source_format.toUpperCase()} · {p.extraction.page_count === null ? 'Page count unavailable' : `${p.extraction.page_count} page(s)`}</span></div>
    <Warnings warnings={p.extraction.warnings} title="Extraction notes" />
    <form onSubmit={e => { e.preventDefault(); if (!p.busy) void p.onAnalyse() }}>
      <label className="field-label" htmlFor="cv-text">CV text <span>Editable preview</span></label>
      <textarea id="cv-text" value={p.cvText} disabled={p.busy} rows={14} spellCheck={false} autoComplete="off"
        aria-describedby="cv-help" onChange={e => p.onTextChange(e.target.value)} />
      <p id="cv-help" className="field-help">{p.cvText.length.toLocaleString()} characters. Remove any personal details you do not want to send.</p>
      {!p.cvText.trim() && <p className="empty-note">No readable text yet. Paste the document text above or start over with another file.</p>}
      <details className="job-disclosure">
        <summary>Add a job posting <span>Optional</span></summary>
        <div><label className="field-label" htmlFor="job-text">Job posting</label><p className="field-help">Adds full-document alignment questions. Not an exhaustive requirements match.</p>
          <textarea id="job-text" rows={7} disabled={p.busy} value={p.jobText} autoComplete="off" onChange={e => p.onJobChange(e.target.value)} /></div>
      </details>
      <div className="submit-row"><div><p>Ready for a closer look?</p><p className="field-help">CV text and any job posting will be sent to TypeSafe.</p></div>
        <button className="btn btn--primary" type="submit" disabled={p.busy || !p.cvText.trim()}>{p.busy ? 'Analysing…' : 'Analyse CV'}</button></div>
      {p.busy && <p className="busy-note" role="status">Waiting for the analysis response. Keep this page open. No automatic retries.</p>}
    </form>
  </section>
}
