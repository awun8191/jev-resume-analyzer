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
import ReportSummary from './features/results/ReportSummary'
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

  /* Reset is destructive, so it asks once. The question is one line and the
   * confirm button is focused, so it works from the keyboard. */
  const [confirming, setConfirming] = useState(false)
  const confirmRef = useRef<HTMLButtonElement>(null)
  const newReviewRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (confirming) confirmRef.current?.focus()
  }, [confirming])

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

  /* One path for a new file, whether it arrives from the upload stage or from
   * the document pane. A re-attached file clears the old report and runs the
   * whole extract again. */
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

  function cancelReset() {
    setConfirming(false)
    newReviewRef.current?.focus()
  }

  const busy = s.stage === 'extracting' || s.stage === 'analysing'
  const workspace = Boolean(s.extraction) && s.stage !== 'empty' && s.stage !== 'extracting'
  const showNewReview = s.stage !== 'empty'

  const alert = s.error ? (
    <div className="alert" role="alert">
      <p className="label">Request failed</p>
      <h2>{s.error.title}</h2>
      <p>{s.error.detail}</p>
      {s.extraction && (
        <p>Your CV and job posting are preserved below. A retry is a new request and may cost again.</p>
      )}
      {s.error.requestId && <p>Request ID: <code>{s.error.requestId}</code></p>}
    </div>
  ) : null

  return (
    <div className="app">
      <a className="skip" href="#main">Skip to content</a>

      <header className="masthead">
        <div className="shell masthead__row">
          <p className="wordmark"><strong>JEV</strong><span>Resume Analyzer</span></p>
          <div className="masthead__tools">
            {health === 'down' && (
              <p className="health" role="status">{HEALTH_TEXT.down}</p>
            )}
            {showNewReview && (
              <button
                ref={newReviewRef}
                type="button"
                className="btn btn--quiet newreview"
                onClick={() => setConfirming(true)}
              >
                New review
              </button>
            )}
          </div>
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

        {confirming && (
          <div
            className="confirm"
            role="dialog"
            aria-labelledby="confirm-title"
            aria-describedby="confirm-note"
            onKeyDown={event => {
              if (event.key === 'Escape') {
                event.stopPropagation()
                cancelReset()
              }
            }}
          >
            <p className="label" id="confirm-title">Start a new review</p>
            <p className="confirm__note" id="confirm-note">
              Clears this tab. Provider records are not touched.
            </p>
            <div className="confirm__row">
              <button
                ref={confirmRef}
                type="button"
                className="btn btn--primary"
                onClick={() => {
                  setConfirming(false)
                  s.reset()
                }}
              >
                Clear this tab
              </button>
              <button type="button" className="btn btn--quiet" onClick={cancelReset}>
                Cancel
              </button>
            </div>
          </div>
        )}

        {s.stage === 'empty' && (
          <div className="page">
            <div className="stage">
              {alert}
              <UploadStage onFile={upload} serverDown={health === 'down'} />
            </div>
          </div>
        )}

        {s.stage === 'extracting' && (
          <div className="page">
            <div className="stage">
              <section aria-labelledby="extracting-title" aria-busy="true">
                <header className="stage__head">
                  <h1 className="stage__title" tabIndex={-1} id="extracting-title">Reading the document.</h1>
                  <p className="help stage__file">{s.fileName}</p>
                </header>
                <p role="status" className="busy">Extracting text on the server. No model request yet.</p>
              </section>
            </div>
          </div>
        )}

        {workspace && (
          <div className="workspace">
            <div className="workspace__summary">
              {s.stage === 'result' && s.report && (
                <ReportSummary
                  report={s.report}
                  onStartOver={() => setConfirming(true)}
                />
              )}
            </div>

            <div className="workspace__doc">
              <DocumentPane
                pages={pages}
                boxes={boxes}
                selectedId={s.selectedId}
                onSelect={s.selectFinding}
                fileName={s.fileName}
                attached={Boolean(s.file)}
                onReattach={upload}
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
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
