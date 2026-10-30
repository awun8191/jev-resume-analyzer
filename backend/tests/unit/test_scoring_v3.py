import pytest

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
    assert len(rubric.QUESTIONS) == 14
    assert len(IDS) == len(set(IDS))
    assert sum(WEIGHTS.values()) == 100
    assert DIMENSIONS == ("Impact", "Scope", "Ownership", "Relevance", "Clarity",
                          "Completeness", "Skills")
    assert DIMENSION_WEIGHTS == {
        "Impact": 25, "Scope": 15, "Ownership": 15, "Relevance": 15,
        "Clarity": 15, "Completeness": 10, "Skills": 5,
    }
    assert all(question.weight > 0 for question in rubric.QUESTIONS)
    assert all(set(question.criteria) == {"present", "absent", "not_applicable",
                                          "unable_to_assess"}
               for question in rubric.QUESTIONS)
    assert all(question.criteria["present"].strip() for question in rubric.QUESTIONS)
    assert all(question.prompt.strip() for question in rubric.QUESTIONS)


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
    assert result.coverage == 0.9
    assert (result.range_low, result.range_high) == (90, 100)


def test_below_half_decidable_weight_withholds_the_score():
    thin = {question_id: "present" for question_id in
            ("impact_outcome", "impact_magnitude", "scope_actors", "scope_size")}
    result = score_report(thin)
    assert sum(WEIGHTS[q] for q in thin) == 40
    assert result.content_score is None
    assert result.range_low == 40 and result.range_high == 100
    assert result.fixes == ()


def test_exactly_half_decidable_weight_scores():
    half = {question_id: "present" for question_id in
            ("impact_outcome", "impact_magnitude", "scope_actors", "scope_size",
             "ownership_own_action")}
    assert sum(WEIGHTS[q] for q in half) == 49
    half["complete_projects"] = "present"
    result = score_report(half)
    assert sum(WEIGHTS[q] for q in half) == 52
    assert result.content_score == 100


def test_combined_total_uses_half_up_rounding():
    present = ("impact_outcome", "impact_magnitude", "scope_actors", "scope_size",
               "ownership_own_action", "ownership_decision", "relevance_responsibility",
               "relevance_requirement")
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
    assert [fix.dimension for fix in result.fixes] == ["Scope", "Ownership", "Clarity"]
    assert all(fix.lost_points == 15.0 for fix in result.fixes)
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
    assert impact.assessed_weight == 15
    assert impact.earned_weight == 15
    assert impact.score == 100


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
