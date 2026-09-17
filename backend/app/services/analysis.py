from hashlib import sha256
from time import perf_counter

from app.config import Settings
from app.errors import AppError
from app.gateways.typesafe import TypeSafeGateway
from app.models.analyses import AnalysisRequest
from app.models.documents import WarningItem
from app.rubrics.cv_review_v2 import POLICY, prepare
from app.rubrics.job_alignment_v1 import QUESTIONS as ALIGNMENT
from app.services.layout_checks import layout_findings
from app.services.reporting import build_report


async def analyse(
    body: AnalysisRequest, gateway: TypeSafeGateway, settings: Settings, request_id: str
):
    start = perf_counter()
    if len(body.cv_text) + len(body.job_text or "") > settings.max_analysis_chars:
        raise AppError(413, "TEXT_TOO_LARGE", "Combined CV and posting exceed the analysis limit.")
    spans = None
    if body.document_evidence is not None and body.document_evidence.source_text_sha256 == sha256(
            body.cv_text.strip().encode()).hexdigest():
        spans = [s.model_dump() for s in body.document_evidence.spans]
    review, bullets = prepare(body.cv_text, spans)
    questions = review + (ALIGNMENT if body.job_text else ())
    state = {"cv_text": body.cv_text, "review_policy": POLICY, "bullets": bullets}
    if body.job_text:
        state["job_text"] = body.job_text
    result = await gateway.evaluate(state, {q.id: q.wire() for q in questions})
    report = build_report(result, questions, request_id, (perf_counter() - start) * 1000)
    for finding in report.findings:
        for bullet in bullets:
            if finding.question_id.startswith(bullet["id"] + "_"):
                finding.assessment_level = "bullet"
                finding.source_text = bullet["text"]
                break
    metadata = layout_findings(body.document_evidence, body.cv_text)
    for finding in metadata:
        finding.source = "document_metadata"
    report.findings.extend(metadata)
    report.overview.questions_total = len(report.findings)
    report.overview.questions_answered = len(report.findings)
    report.overview.questions_assessable = sum(
        f.answer in ("present", "absent") for f in report.findings)
    report.warnings.append(WarningItem(
        code="bullet_coverage", message=f"{len(bullets)} explicit bullet candidates reviewed. "
        "Unmarked tasks may not be separated. Check quoted passages for boundary errors; "
        "whole-document checks do not certify every bullet."))
    return report
