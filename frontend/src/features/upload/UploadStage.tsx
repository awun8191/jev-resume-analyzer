import { useRef, useState } from 'react'
import type { MouseEvent } from 'react'
import './upload.css'

/* 4 MB, not 4 MiB: the API rejects a body above 4.5 MB before the app runs. */
export const MAX_UPLOAD_BYTES = 4_000_000

export function validateFile(file: File): string | null {
  if (!/\.(pdf|docx)$/i.test(file.name)) return 'Choose a PDF or DOCX file.'
  if (file.size === 0) return 'This file is empty. Choose a document with readable text.'
  if (file.size > MAX_UPLOAD_BYTES) return 'This demo accepts files up to 4 MB.'
  return null
}

export default function UploadStage({ onFile }: { onFile: (file: File) => Promise<void> }) {
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const dragDepth = useRef(0)
  const input = useRef<HTMLInputElement>(null)

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

  /* The whole zone is the control. A click on the label opens the picker by
   * itself, so only clicks on the surrounding area forward to the input. */
  function open(event: MouseEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement
    if (target.closest('label, input, button')) return
    input.current?.click()
  }

  return (
    <section className="hero" aria-labelledby="upload-title">
      <header className="hero__head">
        <p className="hero__badge">
          <span className="hero__dot" aria-hidden="true" />
          Free demo. No account.
        </p>
        <h1 className="hero__title" tabIndex={-1} id="upload-title">
          Check what the document actually says.
        </h1>
        <p className="hero__lead">
          Upload a PDF or DOCX, review the extracted text, then read a report built from the exact
          questions that were asked.
        </p>
      </header>

      <div className="card">
        <div className="card__bar">
          <p className="label">CV document</p>
          <p className="card__meta">PDF or DOCX, up to 4 MB</p>
        </div>

        <div
          className={`drop${dragging ? ' is-dragging' : ''}`}
          onClick={open}
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
          <span className="drop__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 16V4" />
              <path d="m7 9 5-5 5 5" />
              <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
            </svg>
          </span>

          <p className="drop__title">{dragging ? 'Release to upload.' : 'Drop a PDF or DOCX here.'}</p>
          <p className="drop__help" id="upload-help">
            {dragging
              ? 'One document at a time.'
              : 'Text is read on the analysis server. No model request is made at this step.'}
          </p>

          <label className="btn btn--primary drop__pick" htmlFor="cv-file">
            Choose CV file
          </label>
          <input
            ref={input}
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
          {error && <p className="drop__error" id="upload-error" role="alert">{error}</p>}
        </div>

        <ul className="card__facts">
          <li><b>20</b><span>content checks</span></li>
          <li><b>11</b><span>layout checks</span></li>
          <li><b>2</b><span>scores per review</span></li>
        </ul>
      </div>

      <section className="notes" aria-labelledby="notes-title">
        <h2 className="notes__title" id="notes-title">Before you begin</h2>
        <ul>
          <li><b>Selectable text.</b> Scanned pages need OCR, which this demo does not provide.</li>
          <li><b>Editable preview.</b> Remove contact details there before anything leaves this machine.</li>
          <li><b>One transfer.</b> Only Analyse CV sends text to TypeSafe. A failed request never produces a report.</li>
        </ul>
      </section>
    </section>
  )
}
