import type { AnalysisReport } from '../../api/schema'
import ScoreBlock from './ScoreBlock'

/* The head of the report: the title, the one escape hatch, and the score. It
 * sits above the document on a phone, so the number is the first thing on the
 * screen. */
export default function ReportSummary({
  report,
  onStartOver,
}: {
  report: AnalysisReport
  onStartOver: () => void
}) {
  return (
    <section aria-labelledby="report-title">
      <header className="stage__head">
        <div className="stage__head-row">
          <h1 className="stage__title" tabIndex={-1} id="report-title">Report</h1>
          <button type="button" className="startover" onClick={onStartOver}>Start over</button>
        </div>
      </header>

      <ScoreBlock scores={report.scores} />
    </section>
  )
}
