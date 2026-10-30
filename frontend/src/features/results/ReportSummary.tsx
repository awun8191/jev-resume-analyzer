import type { AnalysisReport } from '../../api/schema'
import ScoreBlock from './ScoreBlock'
import { ANSWER_TEXT, contentReasonText, rangeText, structureReasonText, topFixes } from './summary'

function SubScores({ report }: { report: AnalysisReport }) {
  const { scores } = report
  const structureReason = structureReasonText(scores.structure)
  const contentReason = contentReasonText(scores)

  return (
    <section className="subscores-section" aria-labelledby="subscores-title">
      <h2 className="sr-only" id="subscores-title">Sub-scores</h2>
      <ul className="subscores">
        <li className="subscore" data-owner="structure">
          <h3 className="label subscore__label">Structure</h3>
          {scores.structure.value === null ? (
            <span className="score__none">Not scored</span>
          ) : (
            <p className="subscore__value">
              <span>{scores.structure.value}</span>
              <small>/ 100</small>
            </p>
          )}
          {scores.structure.value !== null && (
            <p className="subscore__band">{scores.structure.band ?? 'No band reported'}</p>
          )}
          {structureReason && <p className="subscore__reason">{structureReason}</p>}
        </li>
        <li className="subscore" data-owner="content">
          <h3 className="label subscore__label">Content</h3>
          {scores.content.value === null ? (
            <span className="score__none">Not scored</span>
          ) : (
            <p className="subscore__value">
              <span>{scores.content.value}</span>
              <small>/ 100</small>
            </p>
          )}
          {scores.content.value !== null && (
            <p className="subscore__band">{scores.content.band ?? 'No band reported'}</p>
          )}
          {scores.content.range && scores.content.value !== null && (
            <p className="subscore__reason">Range {rangeText(scores.content.range)}</p>
          )}
          {contentReason && <p className="subscore__reason">{contentReason}</p>}
        </li>
      </ul>
    </section>
  )
}

/* The head of the report: title, total, the two tiles, the three absent
 * answers, and the one jump path. It sits above the document on a phone, so the
 * number is the first thing on the screen. */
export default function ReportSummary({
  report,
  selectedId,
  onSelect,
  onStartOver,
}: {
  report: AnalysisReport
  selectedId: string | null
  onSelect: (id: string) => void
  onStartOver: () => void
}) {
  const fixes = topFixes(report.findings)

  function jump() {
    const target = selectedId
      ? document.getElementById(`finding-row-${selectedId}`)
      : document.getElementById('findings-title')
    target?.scrollIntoView?.({ block: 'start' })
    ;(target as HTMLElement | null)?.focus?.()
  }

  return (
    <section aria-labelledby="report-title">
      <header className="stage__head">
        <div className="stage__head-row">
          <h1 className="stage__title" tabIndex={-1} id="report-title">The report.</h1>
          <button type="button" className="startover" onClick={onStartOver}>Start over</button>
        </div>
        <p className="stage__lead">Scores first. Every finding links to its page.</p>
      </header>

      <ScoreBlock scores={report.scores} overview={report.overview} />
      <SubScores report={report} />

      <section className="section" aria-labelledby="fixes-title">
        <div className="section__head">
          <h2 className="section__title" id="fixes-title">Top fixes</h2>
          <p className="section__note">{fixes.length} absent</p>
        </div>
        {fixes.length ? (
          <ul className="fixes">
            {fixes.map((finding, index) => {
              const located = finding.page != null
              return (
                <li className="fix" key={finding.question_id}>
                  <button
                    type="button"
                    className="fix__row"
                    aria-label={`Jump to finding: ${finding.dimension}. ${
                      located ? `Page ${finding.page! + 1}.` : 'No page location.'
                    } ${ANSWER_TEXT[finding.answer]}.`}
                    onClick={() => onSelect(finding.question_id)}
                    onFocus={() => onSelect(finding.question_id)}
                  >
                    <span className="fix__n" aria-hidden="true">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <span className="fix__name">{finding.dimension}</span>
                    <span className="fix__page" data-empty={!located}>
                      {located ? `Page ${finding.page! + 1}` : 'No location'}
                    </span>
                    <span className="fix__go" aria-hidden="true">Jump</span>
                  </button>
                </li>
              )
            })}
          </ul>
        ) : (
          <p className="fixes__none">No absent answers.</p>
        )}
        <button type="button" className="jump" onClick={jump}>Jump to finding</button>
      </section>
    </section>
  )
}
