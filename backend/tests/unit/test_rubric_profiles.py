"""Compare three scripted profiles against the v3.1 weight table.

No model and no network. The answers are fixed, so the scores are arithmetic. The
point of the comparison is the middle profile: a CV with several entries where one
entry is strong. Under v3 every existence check passed there and the document was
indistinguishable from a strong CV at 100 of 100. Under v3.1 the prevalence twins
fail, because fewer than half of the entries carry the evidence.
"""

import pytest

from app.rubrics.cv_review_v3 import IDS, WEIGHTS
from app.rubrics.scoring_v3 import score_report


def profile(default="absent", present=(), not_applicable=()):
    answers = {question_id: default for question_id in IDS}
    answers.update({question_id: "present" for question_id in present})
    answers.update({question_id: "not_applicable" for question_id in not_applicable})
    return answers


# Six entries: two roles, three projects, one volunteer position. Every entry names
# an action. One entry also states a quantified result, its audience, the author's
# decision and a concrete object. The other five are duty lists.
ONE_STRONG_ENTRY = profile(
    present=(
        # The existence checks all pass on the one strong entry.
        "impact_outcome",
        "impact_magnitude",
        "scope_actors",
        "scope_size",
        "ownership_own_action",
        "ownership_decision",
        "relevance_responsibility",
        "relevance_requirement",
        "clarity_concrete",
        "clarity_self_contained",
        "complete_roles",
        "complete_education",
        "complete_projects",
        "skills_evidence",
        # The prevalence twins fail: one of six entries, well under half.
    ),
)

# Six entries of duties, team attribution, and tool lists. Roles are dated and the
# skills list is echoed in the text, so those two checks still pass.
WEAK = profile(
    present=("complete_roles", "complete_education", "skills_evidence"),
    not_applicable=("impact_magnitude_prevalence",),
)

STRONG = profile(default="present")


@pytest.mark.parametrize(
    "answers,expected",
    [
        (STRONG, 100),
        (ONE_STRONG_ENTRY, 64),
        (WEAK, 13),
    ],
)
def test_profile_content_scores(answers, expected):
    result = score_report(answers)
    assert result.content_score == expected


def test_a_strong_profile_scores_in_the_top_band():
    result = score_report(STRONG)
    assert result.content_score == 100
    assert result.content_band == "Very strong evidence"
    assert all(row.score == 100 for row in result.dimensions)


def test_one_strong_entry_cannot_reach_the_full_impact_weight():
    result = score_report(ONE_STRONG_ENTRY)
    impact = next(row for row in result.dimensions if row.dimension == "Impact")

    # The existence checks earn their points, the prevalence twins earn none.
    assert impact.weight == 25
    assert impact.assessed_weight == 25
    assert impact.earned_weight == 12
    assert impact.score == 48
    assert result.content_score == 64

    # The old invariant, one entry earning 25 of 25, is gone.
    assert impact.earned_weight < impact.weight


def test_one_strong_entry_is_at_least_fifteen_points_below_a_strong_cv():
    strong = score_report(STRONG).content_score
    mixed = score_report(ONE_STRONG_ENTRY).content_score
    assert strong is not None and mixed is not None
    assert strong - mixed >= 15
    assert strong - mixed == 36


def test_the_middle_profile_passes_every_existence_check_and_no_prevalence_check():
    existence = {
        "impact_outcome",
        "impact_magnitude",
        "scope_actors",
        "scope_size",
        "ownership_own_action",
        "ownership_decision",
        "relevance_responsibility",
        "relevance_requirement",
        "clarity_concrete",
        "clarity_self_contained",
        "complete_roles",
        "complete_education",
        "complete_projects",
        "skills_evidence",
    }
    prevalence = {question_id for question_id in IDS if "prevalence" in question_id}
    assert existence | prevalence == set(IDS)
    assert sum(WEIGHTS[q] for q in existence) == 64
    assert sum(WEIGHTS[q] for q in prevalence) == 36
    assert all(ONE_STRONG_ENTRY[q] == "present" for q in existence)
    assert all(ONE_STRONG_ENTRY[q] == "absent" for q in prevalence)


def test_a_weak_profile_scores_low_and_below_the_middle_profile():
    weak = score_report(WEAK)
    mixed = score_report(ONE_STRONG_ENTRY)
    # 12 earned of 96 applicable: 12.5 rounds half up to 13.
    assert weak.content_score == 13
    assert weak.content_score is not None and mixed.content_score is not None
    assert weak.content_score < 40
    assert weak.content_band == "Thin evidence"
    assert weak.content_score < mixed.content_score


def test_a_single_entry_document_still_passes_prevalence():
    # Known limitation: at-least-half over one entry is one of one. The rubric text
    # says so explicitly, and the score cannot detect a thin document by itself.
    result = score_report(STRONG)
    assert result.content_score == 100
    impact = next(row for row in result.dimensions if row.dimension == "Impact")
    assert impact.earned_weight == 25
