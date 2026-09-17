import { useEffect, useRef, useState } from 'react'
import { checkHealth, extractDocument, runAnalysis } from './api/client'
import { useAppState } from './appState'
import { failureFromUnknown } from './failures'
import UploadStage from './features/upload/UploadStage'
import ReviewStage from './features/preview/ReviewStage'
import ResultStage from './features/results/ResultStage'
import './app.css'

export default function App() {
  const s = useAppState()
  const pending = useRef(false)
  const main = useRef<HTMLElement>(null)
  const [health, setHealth] = useState('Checking backend…')
  useEffect(() => {
    let active = true
    checkHealth().then(() => { if (active) setHealth('Backend connected') })
      .catch(() => { if (active) setHealth('Backend unavailable') })
    return () => { active = false }
  }, [])
  useEffect(() => { main.current?.focus() }, [s.stage])

  async function upload(file: File) {
    if (pending.current) return
    pending.current = true; s.setError(null); s.setFileName(file.name); s.setStage('extracting')
    try {
      const result = await extractDocument(file)
      s.setExtraction(result); s.setCvText(result.text); s.setStage('reviewing')
    } catch (error) { s.setError(failureFromUnknown(error)); s.setStage('empty') }
    finally { pending.current = false }
  }
  async function analyse() {
    if (pending.current || !s.cvText.trim()) return
    pending.current = true; s.setError(null); s.setReport(null); s.setStage('analysing')
    try {
      const result = await runAnalysis({ cv_text: s.cvText.trim(),
        ...(s.extraction?.document_evidence && s.cvText.trim() === s.extraction.text.trim()
          ? { document_evidence: s.extraction.document_evidence } : {}),
        ...(s.jobText.trim() ? { job_text: s.jobText.trim() } : {}), mode: 'review' })
      s.setReport(result); s.setStage('result')
    } catch (error) { s.setError(failureFromUnknown(error)); s.setStage('reviewing') }
    finally { pending.current = false }
  }
  const busy = s.stage === 'extracting' || s.stage === 'analysing'
  return <div className="app">
    <a className="skip-link" href="#main">Skip to content</a>
    <header className="app-header"><div className="app-shell app-header-row">
      <p className="app-wordmark"><span className="brand-mark" aria-hidden="true">J</span> JEV <span>Resume Analyzer</span></p>
      <p className="app-health" role="status">{health}</p>
    </div></header>
    <main ref={main} tabIndex={-1} className="app-shell" id="main">
      <nav aria-label="Review progress"><ol className="steps">
        {['Upload', 'Check text', 'Report'].map((label, i) => <li key={label}
          aria-current={(s.stage === 'result' ? 2 : s.extraction ? 1 : 0) === i ? 'step' : undefined}>
          <span aria-hidden="true">0{i + 1}</span>{label}</li>)}
      </ol></nav>
      {s.error && <div className="error-banner" role="alert">
        <h2>{s.error.title}</h2><p>{s.error.detail}</p>
        {s.extraction && <p>Your CV and job posting are preserved below. A retry sends a new request and may incur provider cost.</p>}
        {s.error.requestId && <p>Request ID: <code>{s.error.requestId}</code></p>}
      </div>}
      {s.stage === 'empty' && <UploadStage onFile={upload} />}
      {s.stage === 'extracting' && <section className="panel" aria-busy="true">
        <p className="eyebrow">01 / Upload</p><h1>Extracting text…</h1>
        <p className="filename">{s.fileName}</p>
        <p role="status">Reading your document on the local server. No model request has been made.</p>
      </section>}
      {s.extraction && (s.stage === 'reviewing' || s.stage === 'analysing') && <ReviewStage
        fileName={s.fileName} extraction={s.extraction} cvText={s.cvText} jobText={s.jobText}
        onTextChange={s.setCvText} onJobChange={s.setJobText} onAnalyse={analyse} busy={busy} />}
      {s.stage === 'result' && s.report && <ResultStage fileName={s.fileName} report={s.report} onEdit={s.edit} />}
      {s.stage !== 'empty' && <div className="reset-row"><button disabled={busy} className="btn btn--ghost" onClick={s.reset}>
        Clear document & start over</button><span>Clears this page’s memory, not provider records.</span></div>}
    </main>
    <footer className="app-footer app-shell"><p>Localhost demo · No sign-in · No saved history</p>
      <p>Analysis sends CV text and any job posting to TypeSafe. Layout metadata is checked locally. Provider retention terms have not been verified. This is not an offline tool.</p></footer>
  </div>
}
