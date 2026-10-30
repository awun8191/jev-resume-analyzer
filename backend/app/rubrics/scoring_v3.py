"""Deterministic scoring for rubric v3. Pure Python; no network, no model.

The content score is a weighted percentage over the checks that were actually
assessed. Answers of not_applicable and unable_to_assess never become zero:
they leave the denominator and widen a reported range.
"""
from dataclasses import dataclass
from math import floor
from typing import Iterable, Literal, Mapping

from app.rubrics.cv_review_v3 import (
    DIMENSIONS,
    IDS,
    QUESTIONS,
    WEIGHTS,
    Section,
    section_for,
)

ANSWERS = ("present", "absent", "not_applicable", "unable_to_assess")

# A content score needs at least half of the 100 available points to be decidable.
MIN_ASSESSED_WEIGHT = 50

# Content carries the larger share because it is the part the hiring research and
# the product can trace to individual checks. Structure keeps a substantial share
# because layout drives the first scan.
CONTENT_SHARE = 0.7
STRUCTURE_SHARE = 0.3

MAX_FIXES = 3

# One label set for the total and for both sub-scores. Top of range first.
BANDS = (
    (90, "Very strong evidence"),
    (75, "Strong evidence"),
    (60, "Adequate evidence"),
    (40, "Partial evidence"),
    (0, "Thin evidence"),
)

Mode = Literal["combined", "content_only", "structure_only", "unavailable"]


def band_for(score: int | None) -> str | None:
    if score is None:
        return None
    if not 0 <= score <= 100:
        raise ValueError("Score must be between 0 and 100")
    for floor_value, label in BANDS:
        if score >= floor_value:
            return label
    return BANDS[-1][1]


def _round_half_up(value: float) -> int:
    # Python round() is half-to-even, which would make 62.5 depend on parity.
    return int(floor(value + 0.5))


def _dimension_section(dimension: str) -> Section:
    """One section when every question in the dimension agrees, else ``all``."""
    sections: set[Section] = {
        question.section for question in QUESTIONS if question.dimension == dimension
    }
    return sections.pop() if len(sections) == 1 else "all"


@dataclass(frozen=True)
class DimensionScore:
    dimension: str
    section: Section
    weight: int
    assessed_weight: int
    earned_weight: int
    score: int | None


@dataclass(frozen=True)
class Fix:
    dimension: str
    question_id: str
    section: Section
    prompt: str
    lost_points: float


@dataclass(frozen=True)
class ScoreResult:
    content_score: int | None
    content_band: str | None
    structure_score: int | None
    structure_band: str | None
    total_score: int | None
    total_band: str | None
    total_mode: Mode
    dimensions: tuple[DimensionScore, ...]
    coverage: float
    range_low: int | None
    range_high: int | None
    fixes: tuple[Fix, ...]


def _validate_answers(answers: Mapping[str, str], prepared: tuple[str, ...]) -> None:
    allowed = set(prepared)
    for question_id, answer in answers.items():
        if question_id not in WEIGHTS:
            raise ValueError(f"Unknown question id: {question_id}")
        if question_id not in allowed:
            raise ValueError(f"Answer supplied for an unprepared question: {question_id}")
        if answer not in ANSWERS:
            raise ValueError(f"Unknown answer for {question_id}: {answer}")


def _validate_structure(structure_score: int | None) -> None:
    if structure_score is None:
        return
    if isinstance(structure_score, bool) or not isinstance(structure_score, int):
        raise ValueError("structure_score must be an int or None")
    if not 0 <= structure_score <= 100:
        raise ValueError("structure_score must be between 0 and 100")


def score_content(
    answers: Mapping[str, str], prepared: Iterable[str] | None = None
) -> tuple[int | None, int, int, int, tuple[DimensionScore, ...]]:
    """Return score, earned, assessed, applicable weight and dimension rows."""
    prepared_ids = IDS if prepared is None else tuple(prepared)
    if len(set(prepared_ids)) != len(prepared_ids):
        raise ValueError("prepared ids must be unique")
    for question_id in prepared_ids:
        if question_id not in WEIGHTS:
            raise ValueError(f"Unknown prepared question id: {question_id}")
    _validate_answers(answers, prepared_ids)

    earned = 0
    assessed = 0
    applicable = 0
    rows = []
    for dimension in DIMENSIONS:
        dim_earned = 0
        dim_assessed = 0
        dim_weight = 0
        for question in QUESTIONS:
            if question.dimension != dimension or question.id not in prepared_ids:
                continue
            dim_weight += question.weight
            answer = answers.get(question.id, "unable_to_assess")
            if answer == "not_applicable":
                continue
            applicable += question.weight
            if answer == "present":
                dim_earned += question.weight
                dim_assessed += question.weight
            elif answer == "absent":
                dim_assessed += question.weight
        earned += dim_earned
        assessed += dim_assessed
        rows.append(
            DimensionScore(
                dimension=dimension,
                section=_dimension_section(dimension),
                weight=dim_weight,
                assessed_weight=dim_assessed,
                earned_weight=dim_earned,
                score=(
                    _round_half_up(100 * dim_earned / dim_assessed) if dim_assessed else None
                ),
            )
        )

    score = _round_half_up(100 * earned / assessed) if assessed >= MIN_ASSESSED_WEIGHT else None
    return score, earned, assessed, applicable, tuple(rows)


def _fixes(
    answers: Mapping[str, str], rows: tuple[DimensionScore, ...]
) -> tuple[Fix, ...]:
    candidates = []
    for index, row in enumerate(rows):
        if row.score is None or row.score >= 100:
            continue
        lost = row.weight * (1 - row.score / 100)
        absent = [
            question
            for question in QUESTIONS
            if question.dimension == row.dimension and answers.get(question.id) == "absent"
        ]
        if not absent:
            continue
        target = max(absent, key=lambda question: (question.weight, -QUESTIONS.index(question)))
        candidates.append((-lost, -row.weight, index, row.dimension, target))
    candidates.sort(key=lambda item: item[:3])
    return tuple(
        Fix(
            dimension=dimension,
            question_id=question.id,
            section=section_for(question.id),
            prompt=question.prompt,
            lost_points=round(-negative_lost, 2),
        )
        for negative_lost, _, _, dimension, question in candidates[:MAX_FIXES]
    )


def score_report(
    answers: Mapping[str, str],
    structure_score: int | None = None,
    prepared: Iterable[str] | None = None,
) -> ScoreResult:
    """Score one analysis. Answers for prepared questions must be present in the mapping.

    A prepared question with no answer counts as unable_to_assess, never as absent.
    """
    _validate_structure(structure_score)
    content, earned, assessed, applicable, rows = score_content(answers, prepared)
    prepared_weight = sum(row.weight for row in rows)
    coverage = round(assessed / prepared_weight, 4) if prepared_weight else 0.0

    if applicable:
        range_low = _round_half_up(100 * earned / applicable)
        range_high = _round_half_up(100 * (earned + applicable - assessed) / applicable)
    else:
        range_low = range_high = None

    if content is not None and structure_score is not None:
        total = _round_half_up(CONTENT_SHARE * content + STRUCTURE_SHARE * structure_score)
        mode: Mode = "combined"
    elif content is not None:
        total, mode = content, "content_only"
    elif structure_score is not None:
        total, mode = structure_score, "structure_only"
    else:
        total, mode = None, "unavailable"

    return ScoreResult(
        content_score=content,
        content_band=band_for(content),
        structure_score=structure_score,
        structure_band=band_for(structure_score),
        total_score=total,
        total_band=band_for(total),
        total_mode=mode,
        dimensions=rows,
        coverage=coverage,
        range_low=range_low,
        range_high=range_high,
        fixes=_fixes(answers, rows) if content is not None else (),
    )


def as_dict(result: ScoreResult) -> dict:
    """Plain mapping for report assembly and tests."""
    return {
        "content_score": result.content_score,
        "content_band": result.content_band,
        "structure_score": result.structure_score,
        "structure_band": result.structure_band,
        "total_score": result.total_score,
        "total_band": result.total_band,
        "total_mode": result.total_mode,
        "coverage": result.coverage,
        "range_low": result.range_low,
        "range_high": result.range_high,
        "dimensions": [
            {
                "dimension": row.dimension,
                "section": row.section,
                "weight": row.weight,
                "assessed_weight": row.assessed_weight,
                "earned_weight": row.earned_weight,
                "score": row.score,
            }
            for row in result.dimensions
        ],
        "fixes": [
            {
                "dimension": fix.dimension,
                "question_id": fix.question_id,
                "section": fix.section,
                "prompt": fix.prompt,
                "lost_points": fix.lost_points,
            }
            for fix in result.fixes
        ],
    }
