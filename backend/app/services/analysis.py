"""One analysis: the content score comes from one text call over rubric v3."""

from time import perf_counter

from app.config import Settings
from app.errors import AppError
from app.gateways.typesafe import TypeSafeGateway
from app.models.analyses import AnalysisRequest, DimensionRow, StructureScore
from app.models.documents import WarningItem
from app.rubrics.cv_review_v3 import IDS, QUESTIONS
from app.rubrics.scoring_v3 import score_report
from app.services.reporting import (
    assemble_scores,
    build_findings,
    build_report,
    build_warnings,
    content_dimensions,
)


async def analyse(
    body: AnalysisRequest, gateway: TypeSafeGateway, settings: Settings, request_id: str
):
    start = perf_counter()
    if len(body.cv_text) + len(body.job_text or "") > settings.max_analysis_chars:
        raise AppError(413, "TEXT_TOO_LARGE", "Combined CV and posting exceed the analysis limit.")
    state = {"cv_text": body.cv_text}
    if body.job_text:
        state["job_text"] = body.job_text
    result = await gateway.evaluate(state, {q.id: q.wire() for q in QUESTIONS})
    answers = {
        question_id: result.answers[question_id].choice
        for question_id in IDS
        if question_id in result.answers
    }
    content = score_report(answers, None, prepared=IDS)
    findings = build_findings(result, QUESTIONS)
    structure = StructureScore(reason="no_file")
    warnings = build_warnings(
        findings,
        len(QUESTIONS),
        bool(body.job_text),
        (
            WarningItem(
                code="structure_unavailable",
                message="No document was supplied with this analysis, so only content was "
                "scored. Send the PDF as the file part to score structure.",
            ),
        ),
    )
    dimensions: list[DimensionRow] = content_dimensions(content)
    usage = result.usage
    return build_report(
        result=result,
        questions=QUESTIONS,
        findings=findings,
        scores=assemble_scores(content, structure),
        dimensions=dimensions,
        structure_findings=[],
        warnings=warnings,
        request_id=request_id,
        duration_ms=(perf_counter() - start) * 1000,
        input_tokens=usage.input_tokens if usage else None,
        output_tokens=usage.output_tokens if usage else None,
    )
