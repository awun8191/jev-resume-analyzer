import { useRef, useState } from 'react'
import './upload.css'

export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024

export function validateFile(file: File): string | null {
  if (!/\.(pdf|docx)$/i.test(file.name)) return 'Choose a PDF or DOCX file.'
  if (file.size === 0) return 'This file is empty. Choose a document with readable text.'
  if (file.size > MAX_UPLOAD_BYTES) return 'This demo accepts files up to 10 MiB.'
  return null
}

export default function UploadStage({ onFile }: { onFile: (file: File) => Promise<void> }) {
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
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
    <section aria-labelledby="upload-title">
      <header className="stage__head">
        <span className="stage__index">01 / Upload</span>
        <h1 className="stage__title" tabIndex={-1} id="upload-title">Check what the document actually says.</h1>
        <p className="stage__lead">
          Upload a PDF or DOCX, review the extracted text, then read a report built from the exact
          questions that were asked.
        </p>
      </header>

      <div
        className={`drop${dragging ? ' is-dragging' : ''}`}
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
          <p className="label">CV document</p>
          <p className="drop__title">{dragging ? 'Release to upload.' : 'Drop a PDF or DOCX here.'}</p>
          <p className="help">
            {dragging
              ? 'One document at a time. The file is read locally before anything else happens.'
              : 'Text is read on the local server. No model request is made at this step.'}
          </p>
        </div>

        <div className="drop__control">
          <label className="label" htmlFor="cv-file">Choose CV file</label>
          <input
            id="cv-file"
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            aria-describedby={error ? 'upload-help upload-error' : 'upload-help'}
            onChange={event => {
              if (event.currentTarget.files?.length) select(Array.from(event.currentTarget.files))
              event.currentTarget.value = ''
            }}
          />
          <p className="help" id="upload-help">PDF or DOCX. Up to 10 MiB. One file at a time.</p>
          {error && <p className="drop__error" id="upload-error" role="alert">{error}</p>}
        </div>

        <dl className="specs">
          <div><dt className="label">Accepts</dt><dd>PDF, DOCX</dd></div>
          <div><dt className="label">Limit</dt><dd>10 MiB</dd></div>
          <div><dt className="label">Files</dt><dd>One per run</dd></div>
        </dl>
      </div>

      <section className="notes" aria-labelledby="notes-title">
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
