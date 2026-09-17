import { useState } from 'react'
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
  function select(files: File[]) {
    if (files.length !== 1) { setError('Choose one document at a time.'); return }
    const problem = validateFile(files[0])
    setError(problem)
    if (!problem) void onFile(files[0])
  }
  return <section aria-labelledby="upload-title">
    <div className="intro"><p className="eyebrow">A closer look at your CV</p>
      <h1 id="upload-title">Clarity starts with<br />the whole picture.</h1>
      <p>Review how your CV communicates your work. Check the extracted text first, then see the questions behind every finding.</p>
    </div>
    <div className={`dropzone ${dragging ? 'is-dragging' : ''}`}
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => { e.preventDefault(); setDragging(false); select(Array.from(e.dataTransfer.files)) }}>
      <svg width="40" height="48" viewBox="0 0 40 48" fill="none" aria-hidden="true"><path d="M8 2h16l10 10v34H8zM24 2v12h10M14 24h14M14 31h14M14 38h8" stroke="currentColor" strokeWidth="1.5" /></svg>
      <h2>Bring your document</h2><p>Drop a file here, or choose one below.</p>
      <label className="file-label" htmlFor="cv-file">Choose CV file</label>
      <input id="cv-file" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        aria-describedby="upload-help upload-error" onChange={e => {
          if (e.currentTarget.files?.length) select(Array.from(e.currentTarget.files))
          e.currentTarget.value = ''
        }} />
      <p id="upload-help" className="muted">PDF or DOCX · Up to 10 MiB · One file at a time</p>
      <p id="upload-error" role={error ? 'alert' : undefined}>{error}</p>
    </div>
    <div className="upload-notes"><h2>Before you begin</h2><p>Use a document with selectable text. Scanned PDFs need OCR, which this demo does not provide.</p>
      <p>You can remove contact details in the preview. Only selecting “Analyse CV” sends text to TypeSafe.</p></div>
  </section>
}
