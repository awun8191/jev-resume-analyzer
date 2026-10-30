"""Structure rubric: deterministic scoring, edge cases and answer mapping. No network."""

import pytest
from pydantic import ValidationError

from app.models.image_answers import BoxAnswer, NoulAnswer, OptionAnswer
from app.rubrics.structure_v1 import (
    CHECKS,
    FULL_PAGE,
    MIN_ASSESSABLE_WEIGHT,
    MIN_BOX_CONFIDENCE,
    Observation,
    StructureAssessment,
    StructureFinding,
    assessment_from_answers,
    score_structure,
)

BOX = {"top": 0.1, "bottom": 0.2, "left": 0.1, "right": 0.5}


def passing(check="margins", page=0, **extra):
    return Observation(check=check, page=page, answer="pass", **extra)


def full_pass():
    return [Observation(check=check, page=0, answer="pass") for check in CHECKS]


def test_weights_sum_to_one_hundred():
    assert sum(weight for weight, _ in CHECKS.values()) == 100
    assert len(CHECKS) == 11


def test_a_perfect_page_scores_one_hundred():
    report = score_structure(StructureAssessment(pages=1, observations=full_pass()))
    assert report.score == 100
    assert report.reason == "scored"
    assert report.assessable_weight == 100
    assert report.lost_points == 0
    assert report.findings == []
    assert report.limitations == []


def test_an_unreadable_page_is_not_scored_as_perfect_or_zero():
    report = score_structure(StructureAssessment(pages=1, readable=False))
    assert report.score is None
    assert report.reason == "page_not_readable"
    assert report.assessable_weight == 0
    assert [finding.key for finding in report.findings] == ["unreadable"]
    assert report.findings[0].points_lost == 0
    assert report.findings[0].severity == "unverified"
    assert any("not scored" in note.lower() for note in report.limitations)


def test_an_empty_page_scores_zero():
    report = score_structure(StructureAssessment(pages=1, content_present=False))
    assert report.score == 0
    assert report.reason == "page_empty"
    assert report.findings[0].key == "page_empty"
    assert report.findings[0].points_lost == 100


@pytest.mark.parametrize(
    "answer,share", [("minor", 0.5), ("major", 1.0)]
)
def test_deductions_follow_the_declared_weight(answer, share):
    observations = [Observation(check=check, page=0, answer="pass") for check in CHECKS]
    observations[0] = Observation(check="margins", page=0, answer=answer)
    report = score_structure(StructureAssessment(pages=1, observations=observations))
    weight = CHECKS["margins"][0]
    assert report.lost_points == round(weight * share)
    assert report.score == round(100 * (100 - round(weight * share)) / 100)
    assert report.findings[0].severity == answer


def test_an_unassessed_check_leaves_the_denominator():
    observations = [Observation(check=c, page=0, answer="pass") for c in CHECKS if c != "density"]
    report = score_structure(StructureAssessment(pages=1, observations=observations))
    assert report.assessable_weight == 100 - CHECKS["density"][0]
    assert report.score == 100
    unverified = [f for f in report.findings if f.key == "density"]
    assert unverified and unverified[0].severity == "unverified"
    assert unverified[0].points_lost == 0


def test_too_little_evidence_gives_no_score():
    report = score_structure(
        StructureAssessment(
            pages=1,
            observations=[
                Observation(check="margins", page=0, answer="major"),
                Observation(check="alignment", page=0, answer="pass"),
            ],
        )
    )
    assert report.score is None
    assert report.reason == "insufficient_evidence"
    assert report.assessable_weight < MIN_ASSESSABLE_WEIGHT


def test_the_worst_page_decides_a_shared_check():
    observations = full_pass() + [
        Observation(check="page_balance", page=1, answer="major"),
    ]
    report = score_structure(StructureAssessment(pages=2, observations=observations))
    assert report.score == 100 - CHECKS["page_balance"][0]
    finding = next(f for f in report.findings if f.key == "page_balance")
    assert finding.page == 1
    assert finding.severity == "major"


def test_a_low_confidence_box_is_replaced_by_the_whole_page():
    report = score_structure(
        StructureAssessment(
            pages=1,
            observations=[*full_pass(), Observation(
                check="alignment",
                page=0,
                answer="major",
                box=BOX,
                box_confidence=MIN_BOX_CONFIDENCE - 0.01,
            )],
        )
    )
    finding = next(f for f in report.findings if f.key == "alignment")
    assert finding.box == FULL_PAGE
    assert finding.box_confidence == pytest.approx(MIN_BOX_CONFIDENCE - 0.01)
    assert any("confidence threshold" in note for note in report.limitations)


def test_a_confident_box_is_kept_for_the_viewer():
    report = score_structure(
        StructureAssessment(
            pages=1,
            observations=[*full_pass(), Observation(
                check="alignment", page=0, answer="minor", box=BOX, box_confidence=0.82
            )],
        )
    )
    finding = next(f for f in report.findings if f.key == "alignment")
    assert finding.box == BOX
    assert finding.box_confidence == 0.82


def test_evidence_is_short_and_never_echoes_long_text():
    report = score_structure(
        StructureAssessment(
            pages=1,
            observations=[*full_pass(), Observation(
                check="density", page=0, answer="major", note="x" * 500
            )],
        )
    )
    finding = next(f for f in report.findings if f.key == "density")
    assert len(finding.evidence) <= 300
    assert "x" * 300 not in finding.evidence


def test_findings_carry_a_zero_based_page_and_fraction_box():
    report = score_structure(
        StructureAssessment(
            pages=2,
            observations=[*full_pass(), Observation(
                check="spacing", page=1, answer="major", box=BOX, box_confidence=0.9
            )],
        )
    )
    finding = report.findings[0]
    assert finding.page == 1
    assert set(finding.box) == {"top", "bottom", "left", "right"}
    assert all(0.0 <= value <= 1.0 for value in finding.box.values())


def test_scoring_is_deterministic():
    assessment = StructureAssessment(
        pages=1,
        observations=[*full_pass(), Observation(check="columns", page=0, answer="major")],
    )
    first = score_structure(assessment).model_dump()
    second = score_structure(assessment).model_dump()
    assert first == second


def test_an_unknown_check_is_refused():
    with pytest.raises(ValidationError):
        Observation(check="vibes", page=0, answer="pass")


def test_a_finding_cannot_hold_an_invalid_box():
    with pytest.raises(ValidationError):
        StructureFinding(
            key="margins", page=0, box={"top": 0, "bottom": 0, "left": 0, "right": 1},
            severity="minor", points_lost=1, evidence="x",
        )


# ---- answer mapping -------------------------------------------------------


def choice(value):
    return OptionAnswer(type="choice", choice=value)


def noul(value):
    return NoulAnswer(type="noul", noul=value)


def box(confidence=0.8, top=0.1):
    return BoxAnswer(
        type="box",
        box={"top": top, "bottom": top + 0.1, "left": 0.1, "right": 0.9},
        confidence=confidence,
    )


def structure_answers(page=1, outcome="pass", sections=("header", "experience", "education",
                                                       "skills"), layout="one_column",
                      confidence=0.8, tops=None):
    prefix = f"p{page}_"
    answers = {
        "readable": noul(0.97),
        "content_present": noul(0.99),
        "layout": choice(layout),
    }
    for check in ("margins", "alignment", "hierarchy", "spacing", "density",
                  "entry_format", "page_balance"):
        answers[f"{prefix}{check}"] = choice(outcome)
        answers[f"{prefix}{check}_box"] = box(confidence)
    for index, section in enumerate(("header", "summary", "experience", "education",
                                     "skills", "projects")):
        present = section in sections
        answers[f"{prefix}{section}_present"] = noul(0.99 if present else 0.01)
        answers[f"{prefix}{section}_box"] = box(
            confidence if present else 0.05,
            top=(tops or {}).get(section, 0.1 + index * 0.1),
        ) if present else box(0.05)
    return answers


def test_mapping_produces_a_high_score_for_a_clean_single_column_page():
    assessment = assessment_from_answers(structure_answers(), 1)
    report = score_structure(assessment)
    assert report.score == 100
    assert report.reason == "scored"
    assert report.findings == []


def test_two_columns_is_a_major_columns_defect():
    report = score_structure(assessment_from_answers(structure_answers(layout="two_columns"), 1))
    finding = next(f for f in report.findings if f.key == "columns")
    assert finding.severity == "major"
    assert finding.points_lost == CHECKS["columns"][0]


def test_a_table_layout_hits_the_tables_check():
    report = score_structure(assessment_from_answers(structure_answers(layout="table"), 1))
    keys = {f.key for f in report.findings}
    assert "tables" in keys
    assert "columns" not in keys


def test_sections_are_judged_across_the_document_not_per_page():
    first = structure_answers(page=1, sections=("header", "experience"))
    second = structure_answers(page=2, sections=("education", "skills"))
    assessment = assessment_from_answers({**first, **second}, 2)
    report = score_structure(assessment)
    assert not any(f.key == "sections" for f in report.findings)


def test_a_missing_required_section_loses_half_the_section_weight():
    assessment = assessment_from_answers(structure_answers(sections=("header", "experience",
                                                                    "education")), 1)
    report = score_structure(assessment)
    finding = next(f for f in report.findings if f.key == "sections")
    assert finding.severity == "minor"
    assert finding.points_lost == CHECKS["sections"][0] // 2
    assert "skills" in finding.evidence


def test_section_order_is_unverified_when_boxes_are_not_confident():
    assessment = assessment_from_answers(structure_answers(confidence=0.2), 1)
    report = score_structure(assessment)
    finding = next(f for f in report.findings if f.key == "section_order")
    assert finding.severity == "unverified"
    assert finding.points_lost == 0


def test_section_order_passes_when_boxes_are_confident_and_ordered():
    tops = {"header": 0.05, "summary": 0.15, "experience": 0.25, "education": 0.60,
            "skills": 0.70, "projects": 0.80}
    assessment = assessment_from_answers(structure_answers(tops=tops), 1)
    report = score_structure(assessment)
    assert not any(f.key == "section_order" for f in report.findings)


def test_section_order_fails_when_education_sits_above_experience():
    tops = {"header": 0.05, "summary": 0.15, "experience": 0.60, "education": 0.25,
            "skills": 0.70, "projects": 0.80}
    assessment = assessment_from_answers(structure_answers(tops=tops), 1)
    report = score_structure(assessment)
    finding = next(f for f in report.findings if f.key == "section_order")
    assert finding.severity == "minor"
    assert "education" in finding.evidence


def test_an_unreadable_answer_blocks_the_score():
    answers = structure_answers()
    answers["readable"] = noul(0.2)
    report = score_structure(assessment_from_answers(answers, 1))
    assert report.score is None
    assert report.reason == "page_not_readable"
