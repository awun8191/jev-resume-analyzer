import { useRef, useState } from 'react'
import './upload.css'

/* 4 MB, not 4 MiB: the API rejects a body above 4.5 MB before the app runs. */
export const MAX_UPLOAD_BYTES = 4_000_000

export function validateFile(file: File): string | null {
  if (!/\.(pdf|docx)$/i.test(file.name)) return 'Choose a PDF or DOCX file.'
  if (file.size === 0) return 'This file is empty. Choose a document with readable text.'
  if (file.size > MAX_UPLOAD_BYTES) return 'This demo accepts files up to 4 MB.'
  return null
}

export default function UploadStage({
  onFile,
  serverDown = false,
}: {
  onFile: (file: File) => Promise<void>
  serverDown?: boolean
}) {
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)
  const dragDepth = useRef(0)

  function select(files: File[]) {
    if (files.length !== 1) {
      setError('Choose one document at a time.')
      return
    }
    const problem = validateFile(files[0])
    setError(problem)
    if (!problem) void onFile(files[0])
  }

  function leave() {
    dragDepth.current = Math.max(0, dragDepth.current - 1)
    if (dragDepth.current === 0) setDragging(false)
  }

  return (
    <section aria-labelledby="upload-title" className="upload-grid">
      <header className="stage__head upload__head">
        <h1 className="stage__title" tabIndex={-1} id="upload-title">Check what the document actually says.</h1>
        <p className="stage__lead">
          Upload a PDF or DOCX, review the extracted text, then read a report built from the exact
          questions that were asked.
        </p>
      </header>

      <div
        className={`drop${dragging ? ' is-dragging' : ''}`}
        onClick={event => {
          if ((event.target as HTMLElement).closest('label, input, button, a')) return
          fileInput.current?.click()
        }}
        onDragEnter={event => {
          event.preventDefault()
          dragDepth.current += 1
          setDragging(true)
        }}
        onDragOver={event => event.preventDefault()}
        onDragLeave={event => {
          event.preventDefault()
          leave()
        }}
        onDrop={event => {
          event.preventDefault()
          dragDepth.current = 0
          setDragging(false)
          select(Array.from(event.dataTransfer.files))
        }}
      >
        <div className="drop__lead">
          <span className="drop__mark" aria-hidden="true" />
          <p className="label">CV document</p>
          <p className="drop__title">{dragging ? 'Release to upload.' : 'Drop a PDF or DOCX here.'}</p>
          {dragging ? (
            <p className="help">One document at a time. The file is read locally before anything else happens.</p>
          ) : serverDown ? (
            <p className="drop__offline" role="status">
              The analysis server isn’t reachable. You can still choose a file; extraction will
              fail until it reconnects.
            </p>
          ) : (
            <p className="help">Text is read on the analysis server. No model request is made at this step.</p>
          )}
        </div>

        {!dragging && (
          <p className="drop__mid" aria-hidden="true">
            One document. Drag it anywhere on this panel, or use the button below.
          </p>
        )}

        <div className="drop__control">
          <input
            ref={fileInput}
            id="cv-file"
            className="sr-only"
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            aria-describedby={error ? 'upload-help upload-error' : 'upload-help'}
            onChange={event => {
              if (event.currentTarget.files?.length) select(Array.from(event.currentTarget.files))
              event.currentTarget.value = ''
            }}
          />
          <label className="btn btn--primary drop__btn" htmlFor="cv-file">Choose CV file</label>
          <p className="help" id="upload-help">PDF or DOCX. Up to 4 MB. One file at a time.</p>
          {error && <p className="drop__error" id="upload-error" role="alert">{error}</p>}
        </div>
      </div>

      <section className="notes upload__notes" aria-labelledby="notes-title">
        <h2 className="label" id="notes-title">Before you begin</h2>
        <ul>
          <li><b>Selectable text.</b> Scanned pages need OCR, which this demo does not provide.</li>
          <li><b>Editable preview.</b> Remove contact details there before anything leaves this machine.</li>
          <li><b>One transfer.</b> Only Analyse CV sends text to TypeSafe. A failed request never produces a report.</li>
        </ul>
      </section>
    </section>
  )
}
