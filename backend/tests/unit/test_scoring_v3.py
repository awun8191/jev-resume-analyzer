import pytest
from pydantic import ValidationError

from app.models.analyses import Finding
from app.rubrics import cv_review_v3 as rubric
from app.rubrics import scoring_v3 as scoring
from app.rubrics.cv_review_v3 import DIMENSION_WEIGHTS, DIMENSIONS, IDS, WEIGHTS
from app.rubrics.scoring_v3 import band_for, score_content, score_report

ALIGNMENT = tuple(q.id for q in rubric.QUESTIONS if q.scope == "job_alignment")


def answers(value="present", drop=(), **overrides):
    base = {question_id: value for question_id in IDS if question_id not in drop}
    base.update(overrides)
    return base


def test_rubric_shape_and_weights():
    assert len(rubric.QUESTIONS) == 20
    assert len(IDS) == len(set(IDS))
    assert sum(WEIGHTS.values()) == 100
    assert DIMENSIONS == ("Impact", "Scope", "Ownership", "Relevance", "Clarity",
                          "Completeness", "Skills")
    assert DIMENSION_WEIGHTS == {
        "Impact": 25, "Scope": 15, "Ownership": 15, "Relevance": 15,
        "Clarity": 15, "Completeness": 10, "Skills": 5,
    }
    assert WEIGHTS == {
        "impact_outcome": 8,
        "impact_prevalence": 9,
        "impact_magnitude": 4,
        "impact_magnitude_prevalence": 4,
        "scope_actors": 5,
        "scope_prevalence": 6,
        "scope_size": 4,
        "ownership_own_action": 6,
        "ownership_prevalence": 6,
        "ownership_decision": 3,
        "relevance_responsibility": 5,
        "relevance_prevalence": 6,
        "relevance_requirement": 4,
        "clarity_concrete": 5,
        "clarity_prevalence": 5,
        "clarity_self_contained": 5,
        "complete_roles": 4,
        "complete_education": 3,
        "complete_projects": 3,
        "skills_evidence": 5,
    }
    assert all(question.weight > 0 for question in rubric.QUESTIONS)
    assert all(set(question.criteria) == {"present", "absent", "not_applicable",
                                          "unable_to_assess"}
               for question in rubric.QUESTIONS)
    assert all(question.criteria["present"].strip() for question in rubric.QUESTIONS)
    assert all(question.prompt.strip() for question in rubric.QUESTIONS)


def test_every_existential_dimension_has_a_prevalence_twin():
    twins = {
        "impact_outcome": "impact_prevalence",
        "impact_magnitude": "impact_magnitude_prevalence",
        "scope_actors": "scope_prevalence",
        "ownership_own_action": "ownership_prevalence",
        "relevance_responsibility": "relevance_prevalence",
        "clarity_concrete": "clarity_prevalence",
    }
    for existence, prevalence in twins.items():
        assert existence in WEIGHTS and prevalence in WEIGHTS
        assert WEIGHTS[prevalence] > 0
        question = next(q for q in rubric.QUESTIONS if q.id == prevalence)
        # The at-least-half rule is written into the question, including the two-entry case.
        assert "at least half" in question.prompt.lower()
        assert "rounded up" in question.criteria["present"]
        assert "in two" in question.criteria["present"]



def test_all_present_scores_100():
    result = score_report(answers())
    assert result.content_score == 100
    assert result.range_low == result.range_high == 100
    assert result.coverage == 1.0
    assert all(row.score == 100 for row in result.dimensions)
    assert result.fixes == ()


def test_all_absent_scores_zero():
    result = score_report(answers("absent"), structure_score=0)
    assert result.content_score == 0
    assert result.total_score == 0
    assert result.total_mode == "combined"


def test_all_unable_is_unscored_not_zero():
    result = score_report(answers("unable_to_assess"))
    assert result.content_score is None
    assert result.range_low == 0
    assert result.range_high == 100
    assert result.coverage == 0.0
    assert result.fixes == ()


def test_all_not_applicable_is_unscored():
    result = score_report(answers("not_applicable"), structure_score=55)
    assert result.content_score is None
    assert result.range_low is None and result.range_high is None
    assert result.total_score == 55
    assert result.total_mode == "structure_only"


def test_not_applicable_leaves_the_denominator():
    prepared = tuple(q for q in IDS if q not in ALIGNMENT)
    result = score_report(answers(drop=ALIGNMENT), prepared=prepared)
    assert result.content_score == 100
    assert result.coverage == 1.0
    relevance = next(row for row in result.dimensions if row.dimension == "Relevance")
    assert relevance.weight == 0 and relevance.assessed_weight == 0
    assert relevance.score is None


def test_unanswered_alignment_widens_range_without_penalty():
    no_alignment = answers(**{question_id: "unable_to_assess" for question_id in ALIGNMENT})
    result = score_report(no_alignment)
    assert result.content_score == 100
    assert result.coverage == 0.85
    assert (result.range_low, result.range_high) == (85, 100)


def test_missing_answer_is_treated_as_unable():
    missing = answers()
    del missing["impact_magnitude"]
    result = score_report(missing)
    assert result.content_score == 100
    assert result.coverage == 0.96
    assert (result.range_low, result.range_high) == (96, 100)


def test_below_half_decidable_weight_withholds_the_score():
    thin = {question_id: "present" for question_id in
            ("impact_outcome", "impact_prevalence", "impact_magnitude",
             "impact_magnitude_prevalence", "scope_actors", "scope_prevalence",
             "scope_size")}
    result = score_report(thin)
    assert sum(WEIGHTS[q] for q in thin) == 40
    assert result.content_score is None
    assert result.range_low == 40 and result.range_high == 100
    assert result.fixes == ()


def test_exactly_half_decidable_weight_scores():
    # All of Impact, Scope and Completeness is exactly 50 of 100.
    half = {question_id: "present" for question_id in IDS
            if question_id.split("_")[0] in ("impact", "scope", "complete")}
    assert sum(WEIGHTS[q] for q in half) == 50
    result = score_report(half)
    assert result.content_score == 100


def test_combined_total_uses_half_up_rounding():
    # All of Impact, Scope, Ownership and Relevance is exactly 70.
    present = [question_id for question_id in IDS
               if question_id.split("_")[0] in ("impact", "scope", "ownership",
                                                "relevance")]
    assert sum(WEIGHTS[q] for q in present) == 70
    result = score_report(answers("absent", **{q: "present" for q in present}),
                          structure_score=65)
    assert result.content_score == 70
    assert result.structure_score == 65
    # 0.7 * 70 + 0.3 * 65 = 68.5 -> 69, not banker's rounding to 68.
    assert result.total_score == 69
    assert result.total_mode == "combined"


def test_missing_structure_renormalizes_to_content_only():
    result = score_report(answers(), structure_score=None)
    assert result.structure_score is None
    assert result.structure_band is None
    assert result.total_score == 100
    assert result.total_mode == "content_only"


def test_missing_content_renormalizes_to_structure_only():
    result = score_report(answers("unable_to_assess"), structure_score=80)
    assert result.content_score is None
    assert result.total_score == 80
    assert result.total_mode == "structure_only"
    assert result.total_band == "Strong evidence"


def test_both_missing_is_unavailable():
    result = score_report(answers("unable_to_assess"), structure_score=None)
    assert result.total_score is None
    assert result.total_band is None
    assert result.total_mode == "unavailable"


@pytest.mark.parametrize("value", [True, False, 101, -1, 55.0, "55"])
def test_invalid_structure_score_is_rejected(value):
    with pytest.raises(ValueError):
        score_report(answers(), structure_score=value)


@pytest.mark.parametrize("payload", [
    {"not_a_question": "present"},
    {"impact_outcome": "met"},
])
def test_invalid_answers_are_rejected(payload):
    with pytest.raises(ValueError):
        score_report(payload)


def test_answer_for_unprepared_question_is_rejected():
    prepared = tuple(q for q in IDS if q not in ALIGNMENT)
    with pytest.raises(ValueError):
        score_report({"impact_outcome": "present", "relevance_requirement": "present"},
                     prepared=prepared)


def test_duplicate_prepared_ids_are_rejected():
    with pytest.raises(ValueError):
        score_report(answers(), prepared=("impact_outcome", "impact_outcome"))


def test_scoring_is_order_independent_and_reproducible():
    base = answers("absent", impact_outcome="present", scope_actors="present",
                   complete_roles="unable_to_assess")
    first = score_report(base, structure_score=63)
    reordered = {key: base[key] for key in reversed(list(base))}
    second = score_report(reordered, structure_score=63)
    assert first == second == score_report(dict(base), structure_score=63)


def test_range_contains_the_point_score():
    mixed = answers("absent", impact_outcome="present", impact_magnitude="present",
                    ownership_own_action="present", relevance_requirement="unable_to_assess")
    result = score_report(mixed)
    assert result.content_score is not None
    assert result.range_low is not None and result.range_high is not None
    assert result.range_low <= result.content_score <= result.range_high


@pytest.mark.parametrize("score,label", [
    (0, "Thin evidence"), (39, "Thin evidence"), (40, "Partial evidence"),
    (59, "Partial evidence"), (60, "Adequate evidence"), (74, "Adequate evidence"),
    (75, "Strong evidence"), (89, "Strong evidence"), (90, "Very strong evidence"),
    (100, "Very strong evidence"),
])
def test_band_boundaries(score, label):
    assert band_for(score) == label


def test_band_labels_apply_to_every_score():
    result = score_report(answers("absent", impact_outcome="present"), structure_score=39)
    assert result.content_band == band_for(result.content_score)
    assert result.structure_band == "Thin evidence"
    assert result.total_band == band_for(result.total_score)
    assert band_for(None) is None


def test_band_rejects_out_of_range():
    with pytest.raises(ValueError):
        band_for(101)


def test_fixes_rank_lost_points_and_stop_at_three():
    result = score_report(answers("absent", impact_outcome="present",
                                  relevance_requirement="present"))
    assert len(result.fixes) == 3
    lost = [fix.lost_points for fix in result.fixes]
    assert lost == sorted(lost, reverse=True)
    assert [fix.dimension for fix in result.fixes] == ["Impact", "Scope", "Ownership"]
    assert lost == [17.0, 15.0, 15.0]
    # The heaviest absent question in each dimension is the prevalence twin.
    assert [fix.question_id for fix in result.fixes] == [
        "impact_prevalence", "scope_prevalence", "ownership_own_action"
    ]
    assert all(fix.question_id in WEIGHTS for fix in result.fixes)


def test_fixes_skip_dimensions_without_assessed_weight():
    prepared = tuple(q for q in IDS if q not in ALIGNMENT)
    result = score_report(answers("absent", drop=ALIGNMENT), prepared=prepared)
    assert all(fix.dimension != "Relevance" for fix in result.fixes)


def test_dimension_subtotals_renormalize_over_assessed_weight():
    result = score_report(answers("absent", impact_outcome="present",
                                  impact_magnitude="unable_to_assess"))
    impact = next(row for row in result.dimensions if row.dimension == "Impact")
    assert impact.weight == 25
    assert impact.assessed_weight == 21
    assert impact.earned_weight == 8
    assert impact.score == 38


def test_not_applicable_is_excluded_from_coverage():
    # A document with no posting loses no coverage: the relevance weight is inert.
    no_posting = answers(**{question_id: "not_applicable" for question_id in ALIGNMENT})
    result = score_report(no_posting)
    assert result.content_score == 100
    assert result.coverage == 1.0
    assert (result.range_low, result.range_high) == (100, 100)


def test_unable_to_assess_lowers_coverage_but_not_applicable_does_not():
    unable = answers(**{question_id: "unable_to_assess" for question_id in ALIGNMENT})
    na = answers(**{question_id: "not_applicable" for question_id in ALIGNMENT})
    assert score_report(unable).coverage == 0.85
    assert score_report(na).coverage == 1.0
    assert score_report(na).content_score == score_report(unable).content_score


def test_as_dict_is_plain_data():
    payload = scoring.as_dict(score_report(answers(), structure_score=100))
    assert payload["total_score"] == 100
    assert len(payload["dimensions"]) == 7
    assert payload["dimensions"][0]["dimension"] == "Impact"
    assert payload["fixes"] == []


def test_score_content_reports_raw_weights():
    score, earned, assessed, applicable, rows = score_content(answers("absent"))
    assert (score, earned, assessed, applicable) == (0, 0, 100, 100)
    assert len(rows) == len(DIMENSIONS)


# --- Sections: the frontend maps one finding to one resume box by section id. ---

SECTION_BY_ID = {
    "impact_outcome": "all",
    "impact_prevalence": "all",
    "impact_magnitude": "all",
    "impact_magnitude_prevalence": "all",
    "scope_actors": "all",
    "scope_prevalence": "all",
    "scope_size": "all",
    "ownership_own_action": "all",
    "ownership_prevalence": "all",
    "ownership_decision": "all",
    "relevance_responsibility": "all",
    "relevance_prevalence": "all",
    "relevance_requirement": "all",
    "clarity_concrete": "all",
    "clarity_prevalence": "all",
    "clarity_self_contained": "all",
    "complete_roles": "experience",
    "complete_education": "education",
    "complete_projects": "projects",
    "skills_evidence": "skills",
}


def test_section_values_are_the_documented_set():
    assert rubric.SECTION_VALUES == (
        "header", "summary", "experience", "education", "skills", "projects", "all"
    )


def test_every_question_has_a_valid_section():
    assert len(rubric.QUESTIONS) == 20
    assert all(question.section in rubric.SECTION_VALUES for question in rubric.QUESTIONS)


def test_section_map_covers_every_question_id():
    assert len(rubric.SECTIONS) == len(IDS) == 20
    assert set(rubric.SECTIONS) == set(IDS)
    assert all(rubric.section_for(question_id) == rubric.SECTIONS[question_id]
               for question_id in IDS)


def test_section_map_matches_the_expected_contract():
    assert rubric.SECTIONS == SECTION_BY_ID


def test_section_for_unknown_id_raises():
    with pytest.raises(KeyError):
        rubric.section_for("not_a_question")


def test_single_section_questions_use_that_section_only():
    # A question that names one section must not fall back to all.
    assert rubric.section_for("skills_evidence") == "skills"
    assert rubric.section_for("complete_roles") == "experience"
    assert rubric.section_for("complete_education") == "education"
    assert rubric.section_for("complete_projects") == "projects"


def test_as_dict_serializes_section_on_fixes():
    payload = scoring.as_dict(score_report(answers("absent")))
    assert payload["fixes"]
    for fix in payload["fixes"]:
        assert fix["section"] == SECTION_BY_ID[fix["question_id"]]


def test_as_dict_serializes_section_on_dimension_rows():
    payload = scoring.as_dict(score_report(answers()))
    rows = {row["dimension"]: row for row in payload["dimensions"]}
    assert all(row["section"] in rubric.SECTION_VALUES for row in rows.values())
    assert rows["Skills"]["section"] == "skills"
    # Completeness reads roles, education and projects, so it has no single box.
    assert rows["Completeness"]["section"] == "all"
    assert rows["Impact"]["section"] == "all"


def test_fix_object_carries_section():
    result = score_report(answers("absent"))
    assert all(fix.section == SECTION_BY_ID[fix.question_id] for fix in result.fixes)
    assert all(row.section in rubric.SECTION_VALUES for row in result.dimensions)


def _finding(**overrides):
    payload = {
        "question_id": "skills_evidence",
        "dimension": "Skills",
        "scope": "general_review",
        "question": "question text",
        "criteria": ["present: yes"],
        "answer": "present",
        "probabilities": None,
        "confidence": None,
        "rubric_explanation": None,
    }
    payload.update(overrides)
    return Finding(**payload)


def test_finding_section_is_optional_and_validated():
    assert _finding().section is None
    assert _finding(section="skills").model_dump()["section"] == "skills"
    with pytest.raises(ValidationError):
        _finding(section="hobbies")
