"""Unit tests for the v3 answer to finding and score mapping."""

import pytest

from app.models.questions import ChoiceAnswer, Distribution, ProviderResponse, Usage
from app.rubrics import cv_review_v3 as rubric
from app.rubrics.cv_review_v3 import IDS, QUESTIONS
from app.services.reporting import (
    build_findings,
    build_warnings,
    content_dimensions,
)

OPTIONS = ("present", "absent", "not_applicable", "unable_to_assess")


def distribution(choice: str) -> Distribution:
    return Distribution(**{key: 0.7 if key == choice else 0.1 for key in OPTIONS})


def provider(chosen: dict[str, str]) -> ProviderResponse:
    answers = {
        question_id: ChoiceAnswer(
            type="choice",
            choice=choice,
            probabilities=distribution(choice),
            confidence=0.6,
        )
        for question_id, choice in chosen.items()
    }
    return ProviderResponse(
        model="jev-1.14.0", answers=answers, usage=Usage(input_tokens=11, output_tokens=7)
    )


def every(choice: str) -> dict[str, str]:
    return {question_id: choice for question_id in IDS}


def test_one_finding_per_v3_question_in_rubric_order():
    findings = build_findings(provider(every("present")), QUESTIONS)
    assert [finding.question_id for finding in findings] == list(IDS)
    assert len(findings) == 14
    for finding, question in zip(findings, QUESTIONS, strict=True):
        assert finding.dimension == question.dimension
        assert finding.section == question.section
        assert finding.scope == question.scope
        assert finding.question == question.instructions
        assert finding.criteria == [f"{k}: {v}" for k, v in question.criteria.items()]
        assert finding.assessment_level == "full_document"
        assert finding.source == "provider"
        assert finding.source_text is None


def test_explanations_are_versioned_rubric_text():
    findings = build_findings(provider(every("absent")), QUESTIONS)
    for finding in findings:
        assert finding.rubric_explanation is not None
        assert finding.rubric_explanation.kind == "rubric"
        assert finding.rubric_explanation.template_ref == f"v3.{finding.question_id}.absent"
        assert "not evidence of inability" in finding.rubric_explanation.text


@pytest.mark.parametrize("choice", ["not_applicable", "unable_to_assess"])
def test_non_answers_are_kept_as_they_are(choice):
    findings = build_findings(provider(every(choice)), QUESTIONS)
    assert {finding.answer for finding in findings} == {choice}
    assert all(f.probabilities is not None for f in findings)


def test_a_question_with_no_answer_is_left_out_not_guessed():
    chosen = every("present")
    del chosen["impact_outcome"]
    findings = build_findings(provider(chosen), QUESTIONS)
    assert len(findings) == 13
    assert "impact_outcome" not in {finding.question_id for finding in findings}


def test_dimension_rows_match_the_rubric_weights():
    from app.rubrics.scoring_v3 import score_report

    rows = content_dimensions(score_report(every("present")))
    assert [(row.key, row.label, row.weight) for row in rows] == [
        ("impact", "Impact", 25),
        ("scope", "Scope", 15),
        ("ownership", "Ownership", 15),
        ("relevance", "Relevance", 15),
        ("clarity", "Clarity", 15),
        ("completeness", "Completeness", 10),
        ("skills", "Skills", 5),
    ]
    assert all(row.owner == "content" for row in rows)
    assert sum(row.weight for row in rows) == 100


def test_dimension_sections_follow_the_questions():
    from app.rubrics.scoring_v3 import score_report

    rows = content_dimensions(score_report(every("present")))
    sections = {row.label: row.section for row in rows}
    assert sections["Impact"] == "all"
    assert sections["Completeness"] == "all"
    assert sections["Skills"] == "skills"


def test_warnings_name_the_alignment_scope_only_when_a_posting_exists():
    findings = build_findings(provider(every("present")), QUESTIONS)
    without = build_warnings(findings, 14, False, ())
    with_job = build_warnings(findings, 14, True, ())
    assert "alignment_scope" not in {warning.code for warning in without}
    assert "alignment_scope" in {warning.code for warning in with_job}


def test_unable_to_assess_is_reported_not_hidden():
    chosen = {**every("present"), "impact_outcome": "unable_to_assess"}
    findings = build_findings(provider(chosen), QUESTIONS)
    warnings = build_warnings(findings, 14, False, ())
    assert "unable_to_assess" in {warning.code for warning in warnings}


def test_a_short_answer_set_warns_about_a_partial_response():
    chosen = every("present")
    del chosen["skills_evidence"]
    findings = build_findings(provider(chosen), QUESTIONS)
    warnings = build_warnings(findings, 14, False, ())
    assert "partial_response" in {warning.code for warning in warnings}


def test_structure_warnings_are_carried_through_unchanged():
    from app.models.documents import WarningItem

    warning = WarningItem(code="structure_unavailable", message="No file was supplied.")
    warnings = build_warnings([], 14, False, (warning,))
    assert warnings[-1] == warning


def test_rubric_section_map_is_unchanged_by_the_wiring():
    assert rubric.section_for("impact_outcome") == "all"
    assert rubric.section_for("complete_roles") == "experience"
    assert rubric.section_for("complete_education") == "education"
    assert rubric.section_for("complete_projects") == "projects"
    assert rubric.section_for("skills_evidence") == "skills"


def scores_for(answer: str, structure: int | None = None):
    from app.rubrics.scoring_v3 import score_report
    from app.services.reporting import assemble_scores
    from app.services.structure_review import StructureOutcome

    outcome = StructureOutcome(
        score=structure,
        band=None if structure is None else "test band",
        reason="scored" if structure is not None else "no_file",
        assessed_weight=100 if structure is not None else 0,
    )
    return assemble_scores(score_report(every(answer), structure), outcome)


def test_the_total_follows_the_seventy_thirty_rule():
    scores = scores_for("present", 94)
    assert scores.total.value == 98
    assert scores.total.mode == "combined"
    assert scores.content.value == 100
    assert scores.structure.value == 94


def test_a_missing_structure_score_renormalises_to_content():
    scores = scores_for("present", None)
    assert scores.total.mode == "content_only"
    assert scores.total.value == scores.content.value


def test_a_missing_content_score_renormalises_to_structure():
    scores = scores_for("unable_to_assess", 80)
    assert scores.content.value is None
    assert scores.content.band is None
    assert scores.content.assessed_weight == 0
    assert scores.total.mode == "structure_only"
    assert scores.total.value == 80


def test_two_missing_scores_are_unavailable_not_zero():
    scores = scores_for("unable_to_assess", None)
    assert scores.total.mode == "unavailable"
    assert scores.total.value is None
    assert scores.content.value is None
    assert scores.structure.value is None


def test_not_applicable_answers_never_become_zero():
    scores = scores_for("not_applicable", None)
    assert scores.content.value is None
    assert scores.content.assessed_weight == 0
    assert scores.content.coverage == 0.0
    assert scores.total.mode == "unavailable"


def test_the_content_range_is_a_pair_or_null():
    scores = scores_for("present", None)
    assert scores.content.range == (100, 100)
    missing = scores_for("not_applicable", None)
    assert missing.content.range is None


def test_content_coverage_counts_only_the_decided_weight():
    from app.rubrics.scoring_v3 import score_report
    from app.services.reporting import assemble_scores
    from app.services.structure_review import StructureOutcome

    answers = every("present") | {"impact_outcome": "unable_to_assess"}
    scores = assemble_scores(score_report(answers), StructureOutcome())
    assert scores.content.assessed_weight == 85
    assert scores.content.coverage == 0.85
    assert scores.content.range == (85, 100)
