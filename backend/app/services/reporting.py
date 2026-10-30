from app.models.analyses import AnalysisReport, Finding, Metrics, Overview, RubricExplanation
from app.models.questions import ProviderResponse
from app.rubrics.cv_review_v1 import Question

EXPLANATIONS = {
    "present": "The provider selected evidence present under this question's stated threshold. "
    "This concerns only the stated scope, not actual ability.",
    "absent": "The provider selected evidence absent under this question's stated threshold. "
    "Missing written evidence is not evidence of inability.",
    "not_applicable": "This check was judged not applicable under its stated criteria. "
    "It is excluded from assessable coverage and is not a negative score.",
    "unable_to_assess": "The provider could not reliably interpret this check. "
    "It is excluded from assessable coverage, not treated as absent evidence.",
}


def build_report(
    result: ProviderResponse, questions: tuple[Question, ...], request_id: str, duration_ms: float
) -> AnalysisReport:
    findings = []
    for question in questions:
        answer = result.answers[question.id]
        findings.append(
            Finding(
                question_id=question.id,
                dimension=question.dimension,
                section=getattr(question, "section", None),
                scope=question.scope,
                question=question.instructions,
                criteria=[f"{key}: {value}" for key, value in question.criteria.items()],
                answer=answer.choice,
                probabilities=answer.probabilities,
                confidence=answer.confidence,
                rubric_explanation=RubricExplanation(
                    template_ref=f"v2.{question.id}.{answer.choice}",
                    text=EXPLANATIONS[answer.choice],
                ),
            )
        )
    assessable = sum(f.answer in ("present", "absent") for f in findings)
    warnings = [
        {
            "code": "uncalibrated_rubric",
            "message": "These checks have not been calibrated against human reviews. "
            "No overall rating or hiring prediction is provided.",
        }
    ]
    if any(f.answer == "unable_to_assess" for f in findings):
        warnings.append(
            {
                "code": "unable_to_assess",
                "message": "Some checks could not be reliably assessed. Review the source text.",
            }
        )
    if any(q.scope == "job_alignment" for q in questions):
        warnings.append(
            {
                "code": "alignment_scope",
                "message": "Alignment checks look for some relevant evidence, not exhaustive "
                "requirement coverage or eligibility.",
            }
        )
    return AnalysisReport(
        analysis_id=request_id,
        model=result.model,
        findings=findings,
        overview=Overview(
            questions_total=len(questions),
            questions_answered=len(findings),
            questions_assessable=assessable,
        ),
        warnings=warnings,
        metrics=Metrics(
            duration_ms=duration_ms,
            input_tokens=result.usage.input_tokens if result.usage else None,
            output_tokens=result.usage.output_tokens if result.usage else None,
        ),
    )
