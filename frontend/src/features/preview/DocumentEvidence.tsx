import type { Extraction } from '../../api/schema'

export default function DocumentEvidence({ extraction, edited }: { extraction: Extraction; edited: boolean }) {
  const e = extraction.document_evidence
  if (!e) return <p className="field-help">Document metadata: Not assessed.</p>
  return <details className="job-disclosure">
    <summary>Document evidence <span>{e.links.length} links · {e.spans.length} text spans</span></summary>
    {edited && <p role="status">Text was edited. Original metadata will not be used for this analysis.</p>}
    <p>Coordinates and dimensions are in points. PDF coordinates use a top-left origin.
      DOCX records describe sections, not rendered pages. Links below are displayed, never opened automatically.</p>
    <h3>Links</h3>
    {e.links.length ? <ul>{e.links.map((link, i) => <li key={i}>
      {link.label || 'Unlabelled link'}: <span style={{ overflowWrap: 'anywhere' }}>{link.target || 'Not assessed'}</span> ({link.kind})
    </li>)}</ul> : <p>No links recovered. Clickability: Not assessed.</p>}
    <h3>Page or section measurements</h3>
    <ul>{e.pages.map(page => <li key={page.number}>
      {e.source_format === 'pdf' ? 'Page' : 'Section'} {page.number}: {page.width_pt ?? 'Unknown'} × {page.height_pt ?? 'Unknown'} pt.
      {' '}Margins ({page.margin_kind.replace(/_/g, ' ')}): {page.margins_pt?.map(n => n.toFixed(1)).join(', ') ?? 'Not assessed'}.
      {' '}Order: left, top, right, bottom.
    </li>)}</ul>
    <p>Recovered font sizes: {[...new Set(e.spans.map(s => s.font_size_pt).filter(n => n !== null))].sort((a, b) => a - b).join(', ') || 'Not assessed'} pt.</p>
    <h3>Extraction limitations</h3><ul>{e.limitations.map((item, i) => <li key={i}>{item}</li>)}</ul>
  </details>
}
