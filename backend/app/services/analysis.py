from time import perf_counter

from app.config import Settings
from app.errors import AppError
from app.gateways.typesafe import TypeSafeGateway
from app.models.analyses import AnalysisRequest
from app.rubrics.cv_review_v1 import QUESTIONS as REVIEW
from app.rubrics.job_alignment_v1 import QUESTIONS as ALIGNMENT
from app.services.reporting import build_report


async def analyse(
    body: AnalysisRequest, gateway: TypeSafeGateway, settings: Settings, request_id: str
):
    start = perf_counter()
    if len(body.cv_text) + len(body.job_text or "") > settings.max_analysis_chars:
        raise AppError(
            413, "TEXT_TOO_LARGE", "Combined CV and posting exceed the analysis character limit."
        )
    questions = REVIEW + (ALIGNMENT if body.job_text else ())
    state = {"cv_text": body.cv_text}
    if body.job_text:
        state["job_text"] = body.job_text
    result = await gateway.evaluate(state, {q.id: q.wire() for q in questions})
    return build_report(result, questions, request_id, (perf_counter() - start) * 1000)
