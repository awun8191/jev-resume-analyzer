import { useEffect, useMemo, useRef, useState } from 'react'
import { checkHealth, extractDocument, runAnalysis } from './api/client'
import { useAppState } from './appState'
import { failureFromUnknown } from './failures'
import StageBar from './components/StageBar'
import DocumentPane from './features/document/DocumentPane'
import { previewPages } from './features/document/previewSource'
import type { PagePreview } from './features/document/types'
import UploadStage from './features/upload/UploadStage'
import ReviewStage from './features/preview/ReviewStage'
import ResultStage from './features/results/ResultStage'
import { boxFindings, structureBoxes } from './features/results/summary'
import './styles/layout.css'

type Health = 'checking' | 'ok' | 'down'

const HEALTH_TEXT: Record<Health, string> = {
  checking: 'Checking backend',
  ok: 'Backend connected',
  down: 'Backend unavailable',
}

export default function App() {
  const s = useAppState()
  const pending = useRef(false)
  const main = useRef<HTMLElement>(null)
  const [health, setHealth] = useState<Health>('checking')

  useEffect(() => {
    let active = true
    checkHealth()
      .then(() => { if (active) setHealth('ok') })
      .catch(() => { if (active) setHealth('down') })
    return () => { active = false }
  }, [])

  const lastStage = useRef(s.stage)
  useEffect(() => {
    if (lastStage.current === s.stage) return
    lastStage.current = s.stage
    // Move focus to the stage heading: it announces the new stage and brings the
    // top of the new content into view.
    main.current?.querySelector<HTMLElement>('h1')?.focus()
  }, [s.stage])

  /* The PDF is read in this tab. A reload keeps the text and report but not
   * the file, so the pane falls back to its attached state. */
  const [pages, setPages] = useState<PagePreview[]>([])
  useEffect(() => {
    let active = true
    setPages([])
    if (!s.file) return () => { active = false }
    previewPages(s.file).then(next => { if (active) setPages(next) })
    return () => { active = false }
  }, [s.file])

  const boxes = useMemo(() => [
    ...boxFindings(s.report?.findings ?? []),
    ...structureBoxes(s.report?.structure_findings ?? []),
  ], [s.report])

  async function upload(file: File) {
    if (pending.current) return
    pending.current = true
    s.startUpload(file)
    try {
      const result = await extractDocument(file)
      s.setExtraction(result)
      s.setCvText(result.text)
      s.setStage('reviewing')
    } catch (error) {
      s.setError(failureFromUnknown(error))
      s.setStage('empty')
    } finally {
      pending.current = false
    }
  }

  async function analyse() {
    if (pending.current || !s.cvText.trim()) return
    pending.current = true
    s.setError(null)
    s.setReport(null)
    s.setStage('analysing')
    try {
      const result = await runAnalysis({
        cv_text: s.cvText.trim(),
        ...(s.extraction?.document_evidence && s.cvText.trim() === s.extraction.text.trim()
          ? { document_evidence: s.extraction.document_evidence }
          : {}),
        ...(s.jobText.trim() ? { job_text: s.jobText.trim() } : {}),
        mode: 'review',
      }, s.file)
      s.setReport(result)
      s.setStage('result')
    } catch (error) {
      s.setError(failureFromUnknown(error))
      s.setStage('reviewing')
    } finally {
      pending.current = false
    }
  }

  const busy = s.stage === 'extracting' || s.stage === 'analysing'
  const workspace = Boolean(s.extraction) && s.stage !== 'empty' && s.stage !== 'extracting'

  const alert = s.error ? (
    <div className="alert" role="alert">
      <p className="label">Request failed</p>
      <h2>{s.error.title}</h2>
      <p>{s.error.detail}</p>
      {s.extraction && (
        <p>
          Your CV and job posting are preserved below. A retry sends a new request and may incur
          provider cost.
        </p>
      )}
      {s.error.requestId && <p>Request ID: <code>{s.error.requestId}</code></p>}
    </div>
  ) : null

  const reset = s.stage !== 'empty' && (
    <div className="reset">
      <p className="help">Clears this tab, including the saved report. Provider records are not touched.</p>
      <button className="btn btn--quiet" disabled={busy} onClick={s.reset}>
        Clear document and start over
      </button>
    </div>
  )

  return (
    <div className="app">
      <a className="skip" href="#main">Skip to content</a>

      <header className="masthead">
        <div className="shell masthead__row">
          <p className="wordmark"><strong>JEV</strong><span>Resume Analyzer</span></p>
          <p className={`health health--${health}`} role="status">
            <span className="health__mark" aria-hidden="true" />
            {HEALTH_TEXT[health]}
          </p>
        </div>
      </header>

      <div className="progressbar">
        <div className="shell">
          <StageBar stage={s.stage} hasExtraction={Boolean(s.extraction)} fileName={s.fileName} />
        </div>
      </div>

      <main ref={main} tabIndex={-1} className="shell" id="main">
        {s.restoreNotice && <p className="storage" role="status">{s.restoreNotice}</p>}
        {s.storageNotice && <p className="storage" role="status">{s.storageNotice}</p>}

        {s.stage === 'empty' && (
          <div className="page">
            <div className="stage">
              {alert}
              <UploadStage onFile={upload} />
            </div>
          </div>
        )}

        {s.stage === 'extracting' && (
          <div className="page">
            <div className="stage">
              <section aria-labelledby="extracting-title" aria-busy="true">
                <header className="stage__head">
                  <span className="stage__index">01 / Upload</span>
                  <h1 className="stage__title" tabIndex={-1} id="extracting-title">Reading the document.</h1>
                  <p className="help stage__file">{s.fileName}</p>
                </header>
                <p role="status" className="busy">
                  Text is being extracted on the analysis server. No model request has been made.
                </p>
              </section>
            </div>
          </div>
        )}

        {workspace && (
          <div className="workspace">
            <div className="workspace__doc">
              <DocumentPane
                pages={pages}
                boxes={boxes}
                selectedId={s.selectedId}
                onSelect={s.selectFinding}
                fileName={s.fileName}
                attached={Boolean(s.file)}
                onReattach={s.attachFile}
              />
            </div>

            <div className="workspace__report">
              {alert}

              {s.stage === 'result' && s.report ? (
                <ResultStage
                  report={s.report}
                  onEdit={s.edit}
                  selectedId={s.selectedId}
                  onSelect={s.selectFinding}
                />
              ) : (
                <ReviewStage
                  fileName={s.fileName}
                  extraction={s.extraction!}
                  cvText={s.cvText}
                  jobText={s.jobText}
                  onTextChange={s.setCvText}
                  onJobChange={s.setJobText}
                  onAnalyse={analyse}
                  busy={busy}
                />
              )}

              {reset}
            </div>
          </div>
        )}
      </main>

      <footer className="footer">
        <div className="shell footer__grid">
          <p className="label">Local demo</p>
          <p>
            Stored in this tab only, cleared when the tab closes. No accounts, no database. The
            document file is never saved.
          </p>
          <p>
            Analysis sends CV text and any job posting to TypeSafe. Layout metadata is checked
            locally. Provider retention terms have not been verified. This is not an offline tool.
          </p>
        </div>
      </footer>
    </div>
  )
}
