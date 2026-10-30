"""Assemble provider answers and scores into the report contract."""

from app.models.analyses import (
    AnalysisReport,
    ContentScore,
    DimensionRow,
    Finding,
    Metrics,
    Overview,
    RubricExplanation,
    Scores,
    StructureFindingItem,
    StructureScore,
    TotalScore,
)
from app.models.documents import WarningItem
from app.models.questions import ProviderResponse
from app.rubrics.cv_review_v3 import RatedQuestion
from app.rubrics.scoring_v3 import ScoreResult

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


def build_findings(
    result: ProviderResponse, questions: tuple[RatedQuestion, ...]
) -> list[Finding]:
    """One finding per v3 question. A question with no answer is left out, never guessed."""
    findings = []
    for question in questions:
        answer = result.answers.get(question.id)
        if answer is None:
            continue
        findings.append(
            Finding(
                question_id=question.id,
                dimension=question.dimension,
                section=question.section,
                scope=question.scope,
                question=question.instructions,
                criteria=[f"{key}: {value}" for key, value in question.criteria.items()],
                answer=answer.choice,
                probabilities=answer.probabilities,
                confidence=answer.confidence,
                rubric_explanation=RubricExplanation(
                    template_ref=f"v3.{question.id}.{answer.choice}",
                    text=EXPLANATIONS[answer.choice],
                ),
            )
        )
    return findings


def _dimension_key(label: str) -> str:
    return label.strip().lower().replace(" ", "_")


def content_dimensions(content: ScoreResult) -> list[DimensionRow]:
    return [
        DimensionRow(
            key=_dimension_key(row.dimension),
            label=row.dimension,
            owner="content",
            weight=row.weight,
            value=row.score,
            section=row.section,
        )
        for row in content.dimensions
    ]


def assemble_scores(content: ScoreResult, structure: StructureScore) -> Scores:
    assessed = sum(row.assessed_weight for row in content.dimensions)
    content_range = (
        (content.range_low, content.range_high)
        if content.range_low is not None and content.range_high is not None
        else None
    )
    return Scores(
        content=ContentScore(
            value=content.content_score,
            band=content.content_band,
            range=content_range,
            coverage=content.coverage,
            assessed_weight=assessed,
        ),
        structure=structure,
        total=TotalScore(
            value=content.total_score,
            band=content.total_band,
            mode=content.total_mode,
        ),
    )


def build_warnings(
    findings: list[Finding],
    total_questions: int,
    has_job_text: bool,
    structure_warnings: tuple[WarningItem, ...],
) -> list[WarningItem]:
    warnings = [
        WarningItem(
            code="uncalibrated_rubric",
            message="These checks have not been calibrated against human reviews. "
            "No overall rating or hiring prediction is provided.",
        )
    ]
    if any(f.answer == "unable_to_assess" for f in findings):
        warnings.append(
            WarningItem(
                code="unable_to_assess",
                message="Some checks could not be reliably assessed. Review the source text.",
            )
        )
    if len(findings) < total_questions:
        warnings.append(
            WarningItem(
                code="partial_response",
                message="The provider did not answer every question. Missing answers are "
                "excluded from the score, not treated as absent evidence.",
            )
        )
    if has_job_text:
        warnings.append(
            WarningItem(
                code="alignment_scope",
                message="Alignment checks look for some relevant evidence, not exhaustive "
                "requirement coverage or eligibility.",
            )
        )
    warnings.extend(structure_warnings)
    return warnings


def build_report(
    *,
    result: ProviderResponse,
    questions: tuple[RatedQuestion, ...],
    findings: list[Finding],
    scores: Scores,
    dimensions: list[DimensionRow],
    structure_findings: list[StructureFindingItem],
    warnings: list[WarningItem],
    request_id: str,
    duration_ms: float,
    input_tokens: int | None,
    output_tokens: int | None,
) -> AnalysisReport:
    assessable = sum(f.answer in ("present", "absent") for f in findings)
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
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        ),
        scores=scores,
        dimensions=dimensions,
        structure_findings=structure_findings,
    )
