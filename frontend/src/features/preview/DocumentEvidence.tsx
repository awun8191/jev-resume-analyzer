import type { Extraction } from '../../api/schema'

export default function DocumentEvidence({ extraction, edited }: { extraction: Extraction; edited: boolean }) {
  const e = extraction.document_evidence
  if (!e) {
    return <p className="help evidence">Document metadata: not assessed.</p>
  }
  const sizes = [...new Set(e.spans.map(span => span.font_size_pt).filter(n => n !== null))].sort((a, b) => a - b)

  return (
    <div className="evidence">
      <h2 className="label">Document evidence</h2>
      <details className="disclosure">
        <summary>
          <span>Original extraction detail</span>
          <span className="summary-note">{e.links.length} links / {e.spans.length} text spans</span>
          <span className="disclosure__mark" aria-hidden="true" />
        </summary>
        <div className="disclosure__body">
          {edited && (
            <p className="evidence__warning" role="status">
              Text was edited. Original metadata will not be used for this analysis.
            </p>
          )}
          <p>
            Coordinates and dimensions are in points. PDF coordinates use a top-left origin. DOCX
            records describe sections, not rendered pages. Links are displayed, never opened
            automatically.
          </p>

          <h3>Links</h3>
          {e.links.length ? (
            <ul>
              {e.links.map((link, i) => (
                <li key={i}>
                  <span>
                    {link.label || 'Unlabelled link'}: {link.target || 'Not assessed'} ({link.kind})
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p>No links recovered. Clickability: not assessed.</p>
          )}

          <h3>Page or section measurements</h3>
          <ul>
            {e.pages.map(page => (
              <li key={page.number}>
                <span>
                  {e.source_format === 'pdf' ? 'Page' : 'Section'} {page.number}:{' '}
                  {page.width_pt ?? 'Unknown'} x {page.height_pt ?? 'Unknown'} pt. Margins (
                  {page.margin_kind.replace(/_/g, ' ')}):{' '}
                  {page.margins_pt?.map(n => n.toFixed(1)).join(', ') ?? 'Not assessed'}. Order:
                  left, top, right, bottom.
                </span>
              </li>
            ))}
          </ul>

          <p>Recovered font sizes: {sizes.join(', ') || 'Not assessed'} pt.</p>

          <h3>Extraction limitations</h3>
          <ul>
            {e.limitations.map((item, i) => (
              <li key={i}><span>{item}</span></li>
            ))}
          </ul>
        </div>
      </details>
    </div>
  )
}
