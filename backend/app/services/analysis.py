"""One analysis: content from the text call, structure from the image call.

Two provider calls run here, not one. The text call asks the twenty rubric v3.1
questions. The image call scores layout from up to six rasterised pages, in groups of
at most three. A missing structure score never blocks the content report.
"""

from time import perf_counter

from app.config import Settings
from app.errors import AppError
from app.gateways.typesafe import TypeSafeGateway
from app.models.analyses import AnalysisRequest, DimensionRow
from app.rubrics.cv_review_v3 import IDS, QUESTIONS
from app.rubrics.scoring_v3 import score_report
from app.services.reporting import (
    assemble_scores,
    build_findings,
    build_report,
    build_warnings,
    content_dimensions,
)
from app.services.structure_review import assess


def _sum(first: int | None, second: int | None) -> int | None:
    if first is None:
        return second
    if second is None:
        return first
    return first + second


async def analyse(
    body: AnalysisRequest,
    gateway: TypeSafeGateway,
    settings: Settings,
    request_id: str,
    upload: bytes | None = None,
):
    start = perf_counter()
    if len(body.cv_text) + len(body.job_text or "") > settings.max_analysis_chars:
        raise AppError(413, "TEXT_TOO_LARGE", "Combined CV and posting exceed the analysis limit.")
    state = {"cv_text": body.cv_text}
    if body.job_text:
        state["job_text"] = body.job_text
    result = await gateway.evaluate(state, {q.id: q.wire() for q in QUESTIONS})
    structure = await assess(upload, gateway)
    answers = {
        question_id: result.answers[question_id].choice
        for question_id in IDS
        if question_id in result.answers
    }
    content = score_report(answers, structure.score, prepared=IDS)
    findings = build_findings(result, QUESTIONS)
    warnings = build_warnings(findings, len(QUESTIONS), bool(body.job_text), structure.warnings)
    dimensions: list[DimensionRow] = [*content_dimensions(content), *structure.dimensions]
    usage = result.usage
    return build_report(
        result=result,
        questions=QUESTIONS,
        findings=findings,
        scores=assemble_scores(content, structure),
        dimensions=dimensions,
        structure_findings=list(structure.findings),
        warnings=warnings,
        request_id=request_id,
        duration_ms=(perf_counter() - start) * 1000,
        input_tokens=_sum(usage.input_tokens if usage else None, structure.input_tokens),
        output_tokens=_sum(usage.output_tokens if usage else None, structure.output_tokens),
    )
