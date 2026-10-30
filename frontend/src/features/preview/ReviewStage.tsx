import type { Extraction } from '../../api/schema'
import Warnings from '../../components/Warnings'
import DocumentEvidence from './DocumentEvidence'
import './preview.css'

interface Props {
  fileName: string
  extraction: Extraction
  cvText: string
  jobText: string
  busy: boolean
  onTextChange: (text: string) => void
  onJobChange: (text: string) => void
  onAnalyse: () => Promise<void>
}

export default function ReviewStage(p: Props) {
  const pages = p.extraction.page_count === null ? 'Not reported' : String(p.extraction.page_count)

  return (
    <section aria-labelledby="preview-title">
      <header className="stage__head">
        <span className="stage__index">02 / Check text</span>
        <h1 className="stage__title" tabIndex={-1} id="preview-title">Check the extracted text.</h1>
        <p className="stage__lead">
          Fix reading order or missing text before analysis. This is the whole document, not
          reconstructed sections.
        </p>
      </header>

      <dl className="doc">
        <div className="doc__file">
          <dt className="label">Document</dt>
          <dd>{p.fileName}</dd>
        </div>
        <div>
          <dt className="label">Format</dt>
          <dd>{p.extraction.source_format.toUpperCase()}</dd>
        </div>
        <div>
          <dt className="label">Pages</dt>
          <dd>{pages}</dd>
        </div>
        <div>
          <dt className="label">Characters</dt>
          <dd>{p.cvText.length.toLocaleString('en-US')}</dd>
        </div>
      </dl>

      <Warnings warnings={p.extraction.warnings} title="Extraction notes" />
      <DocumentEvidence extraction={p.extraction} edited={p.cvText.trim() !== p.extraction.text.trim()} />

      <form
        className="form"
        onSubmit={event => {
          event.preventDefault()
          if (!p.busy) void p.onAnalyse()
        }}
      >
        <div className="field">
          <div className="field-label">
            <label className="label" htmlFor="cv-text">CV text</label>
            <span className="field-meta">{p.cvText.length.toLocaleString('en-US')} characters</span>
          </div>
          <textarea
            id="cv-text"
            value={p.cvText}
            disabled={p.busy}
            rows={12}
            spellCheck={false}
            autoComplete="off"
            aria-describedby="cv-help"
            onChange={event => p.onTextChange(event.target.value)}
          />
          <p className="help measure" id="cv-help">
            Remove any personal details you do not want to send. Editing here does not contact the server.
          </p>
          {!p.cvText.trim() && (
            <p className="empty">
              No readable text yet. Paste the document text above, or start over with another file.
            </p>
          )}
        </div>

        <details className="disclosure">
          <summary>
            <span>Add a job posting</span>
            <span className="summary-note">Optional</span>
            <span className="disclosure__mark" aria-hidden="true" />
          </summary>
          <div className="disclosure__body job-body">
            <p className="help">
              Adds document-level alignment questions. It is not an exhaustive requirements match.
            </p>
            <label className="label" htmlFor="job-text">Job posting</label>
            <textarea
              id="job-text"
              rows={7}
              disabled={p.busy}
              value={p.jobText}
              autoComplete="off"
              onChange={event => p.onJobChange(event.target.value)}
            />
          </div>
        </details>

        <div className="actions">
          <p className="actions__note">
            CV text and any job posting will be sent to TypeSafe. One request per submission.
          </p>
          <button className="btn btn--primary" type="submit" disabled={p.busy || !p.cvText.trim()}>
            {p.busy ? 'Analysing' : 'Analyse CV'}
          </button>
        </div>

        {p.busy && (
          <p className="busy" role="status">
            Waiting for the analysis response. Keep this page open. No automatic retries.
          </p>
        )}
      </form>
    </section>
  )
}
