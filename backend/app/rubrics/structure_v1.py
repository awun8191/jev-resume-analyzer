"""Structure and formatting rubric for the image route. Version 1.

This rubric scores only what a page image shows: layout, whitespace, typography,
section order and entry consistency. It never scores content quality, and it never
reads or rewrites the CV text.

Determinism rules:

- Each check has a fixed weight. The weights sum to 100.
- A pass removes nothing. A minor defect removes half of the weight. A major defect
  removes all of it.
- A check that cannot be assessed is removed from the denominator, so an unclear page
  is neither perfect nor zero.
- A page that is not readable scores nothing at all (score is None), never 0 and never 100.
- A readable but empty page is a real defect and scores 0.

No network call, no model and no randomness happens in this module.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.image_answers import BoxAnswer, ImageAnswer, NoulAnswer, OptionAnswer
from app.services.box_geometry import validate_box

RUBRIC_VERSION = "structure-1"
MIN_ASSESSABLE_WEIGHT = 60
MIN_BOX_CONFIDENCE = 0.5
FULL_PAGE = {"top": 0.0, "bottom": 1.0, "left": 0.0, "right": 1.0}
EVIDENCE_CHARS = 160

CheckKey = Literal[
    "margins",
    "alignment",
    "hierarchy",
    "spacing",
    "sections",
    "section_order",
    "density",
    "entry_format",
    "page_balance",
    "columns",
    "tables",
]
Outcome = Literal["pass", "minor", "major", "unable_to_assess"]

# key: (weight, weight rationale, evidence sentence used when the check fails)
CHECKS: dict[str, tuple[int, str]] = {
    "margins": (10, "Page margins are consistent and no content sits against an edge."),
    "alignment": (8, "Text blocks share a small number of left edges and align on a grid."),
    "hierarchy": (
        14,
        "Section headings are clearly larger or heavier than body text and are used "
        "consistently.",
    ),
    "spacing": (8, "Vertical spacing between sections and entries follows a repeatable rhythm."),
    "sections": (
        10,
        "The expected sections are present, and none of them is empty or unlabelled.",
    ),
    "section_order": (6, "Sections follow the conventional order for a CV."),
    "density": (
        12,
        "Line length, line count and white space keep the page readable without crowding.",
    ),
    "entry_format": (
        10,
        "Entries inside one section use the same title, date and bullet format.",
    ),
    "page_balance": (6, "Content fills each page without a large empty tail or a crowded top."),
    "columns": (8, "Body text uses one reading column, so extraction order is unambiguous."),
    "tables": (8, "Body text is not placed in table cells or floating text boxes."),
}

SECTION_KEYS = ("header", "summary", "experience", "education", "skills", "projects")
# A CV without a summary or a projects list is not a formatting defect.
REQUIRED_SECTIONS = ("header", "experience", "education", "skills")
EXPECTED_SECTION_ORDER = ("header", "summary", "experience", "education", "skills", "projects")
SECTION_LABELS = {
    "header": "header",
    "summary": "summary",
    "experience": "experience",
    "education": "education",
    "skills": "skills",
    "projects": "projects",
}

LAYOUT_OPTIONS = {
    "one_column": "All body text sits in one vertical column.",
    "two_columns": "Body text is arranged in two vertical columns.",
    "three_or_more_columns": "Body text is arranged in three or more vertical columns.",
    "table": "Body text sits in ruled or aligned table cells.",
    "mixed": "The page mixes columns, tables or full-width blocks.",
}

DEDUCTIONS = {"pass": 0.0, "minor": 0.5, "major": 1.0, "unable_to_assess": None}
SEVERITY = {"minor": "minor", "major": "major", "unable_to_assess": "unverified"}

if sum(weight for weight, _ in CHECKS.values()) != 100:  # pragma: no cover - import guard
    raise RuntimeError("Structure weights must sum to 100")


class AssessmentError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class Observation(BaseModel):
    """One answered check, with the region that evidences it."""

    model_config = ConfigDict(extra="forbid")
    check: str
    page: int = Field(ge=0)
    answer: Outcome
    box: dict[str, float] | None = None
    box_confidence: float | None = Field(default=None, ge=0, le=1)
    note: str = ""

    @field_validator("check")
    @classmethod
    def known_check(cls, value: str) -> str:
        if value not in CHECKS:
            raise ValueError(f"Unknown structure check: {value}")
        return value

    @field_validator("box")
    @classmethod
    def valid_box(cls, value: dict[str, float] | None) -> dict[str, float] | None:
        return None if value is None else validate_box(value)


class StructureAssessment(BaseModel):
    """Everything the rubric needs. Assembled from answers, or by hand in a test."""

    model_config = ConfigDict(extra="forbid")
    pages: int = Field(ge=1, le=100)
    readable: bool = True
    content_present: bool = True
    observations: list[Observation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class StructureFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    page: int = Field(ge=0)
    box: dict[str, float]
    severity: Literal["minor", "major", "unverified"]
    points_lost: int = Field(ge=0, le=100)
    evidence: str = Field(min_length=1, max_length=300)
    box_confidence: float | None = None

    @field_validator("box")
    @classmethod
    def valid_box(cls, value: dict[str, float]) -> dict[str, float]:
        return validate_box(value)


class StructureReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rubric_version: Literal["structure-1"] = RUBRIC_VERSION
    score: int | None = Field(default=None, ge=0, le=100)
    reason: Literal["scored", "page_not_readable", "page_empty", "insufficient_evidence"]
    assessable_weight: int = Field(ge=0, le=100)
    lost_points: int = Field(ge=0, le=100)
    findings: list[StructureFinding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


def _clean(text: str) -> str:
    flat = " ".join(str(text).split())
    return flat[:EVIDENCE_CHARS].rstrip()


def _evidence(check: str, note: str) -> str:
    base = CHECKS[check][1]
    note = _clean(note)
    return f"{base} {note}".strip() if note else base


def _display_box(observation: Observation) -> tuple[dict[str, float], float | None]:
    """Show the provider box only when its confidence meets the display threshold."""
    if observation.box is None or observation.box_confidence is None:
        return dict(FULL_PAGE), None
    if observation.box_confidence < MIN_BOX_CONFIDENCE:
        return dict(FULL_PAGE), observation.box_confidence
    return dict(observation.box), observation.box_confidence


def score_structure(assessment: StructureAssessment) -> StructureReport:
    """Deterministic 0 to 100 structure score with per-finding coordinates."""
    if not assessment.readable:
        return StructureReport(
            score=None,
            reason="page_not_readable",
            assessable_weight=0,
            lost_points=0,
            findings=[
                StructureFinding(
                    key="unreadable",
                    page=0,
                    box=dict(FULL_PAGE),
                    severity="unverified",
                    points_lost=0,
                    evidence=(
                        "The page image could not be read, so no structure points were "
                        "awarded or removed. Check the original file."
                    ),
                )
            ],
            limitations=[
                "Structure not scored: the page image was unreadable or too low resolution.",
                *assessment.limitations,
            ],
        )
    if not assessment.content_present:
        return StructureReport(
            score=0,
            reason="page_empty",
            assessable_weight=100,
            lost_points=100,
            findings=[
                StructureFinding(
                    key="page_empty",
                    page=0,
                    box=dict(FULL_PAGE),
                    severity="major",
                    points_lost=100,
                    evidence="The page image shows no visible resume content.",
                )
            ],
            limitations=[
                "Structure scored 0: the page is empty, not unreadable.",
                *assessment.limitations,
            ],
        )

    # A check is judged once for the document. When several pages answer the same
    # check, the worst answer wins, so a poor page cannot hide behind a good one.
    rank = {"unable_to_assess": 0, "pass": 1, "minor": 2, "major": 3}
    worst: dict[str, Observation] = {}
    for observation in assessment.observations:
        current = worst.get(observation.check)
        if current is None or rank[observation.answer] > rank[current.answer]:
            worst[observation.check] = observation

    assessable, lost, findings = 0, 0, []
    for check, (weight, _) in CHECKS.items():
        observation = worst.get(check)
        if observation is None or observation.answer == "unable_to_assess":
            findings.append(
                StructureFinding(
                    key=check,
                    page=observation.page if observation else 0,
                    box=_display_box(observation)[0] if observation else dict(FULL_PAGE),
                    severity="unverified",
                    points_lost=0,
                    evidence=_evidence(check, observation.note if observation else "")
                    + " Not assessed: no usable answer for this check.",
                    box_confidence=observation.box_confidence if observation else None,
                )
            )
            continue
        assessable += weight
        share = DEDUCTIONS[observation.answer]
        box, confidence = _display_box(observation)
        if share == 0:
            continue
        points = round(weight * share)
        lost += points
        findings.append(
            StructureFinding(
                key=check,
                page=observation.page,
                box=box,
                severity=SEVERITY[observation.answer],
                points_lost=points,
                evidence=_evidence(check, observation.note),
                box_confidence=confidence,
            )
        )

    if assessable < MIN_ASSESSABLE_WEIGHT:
        return StructureReport(
            score=None,
            reason="insufficient_evidence",
            assessable_weight=assessable,
            lost_points=lost,
            findings=findings,
            limitations=[
                f"Structure not scored: only {assessable} of 100 points could be assessed.",
                *assessment.limitations,
            ],
        )
    score = max(0, min(100, round(100 * (assessable - lost) / assessable)))
    limitations = list(assessment.limitations)
    low_confidence = [f for f in findings if f.box_confidence is not None
                      and f.box_confidence < MIN_BOX_CONFIDENCE]
    if low_confidence:
        limitations.append(
            f"{len(low_confidence)} finding boxes were below the "
            f"{MIN_BOX_CONFIDENCE:.1f} confidence threshold, so they are shown as the "
            "whole page."
        )
    return StructureReport(
        score=score,
        reason="scored",
        assessable_weight=assessable,
        lost_points=lost,
        findings=findings,
        limitations=limitations,
    )


def _outcome(answer: ImageAnswer) -> Outcome:
    if isinstance(answer, OptionAnswer):
        return answer.choice if answer.choice in ("pass", "minor", "major") else "unable_to_assess"
    return "unable_to_assess"


def _boxed(answers: dict[str, ImageAnswer], key: str) -> tuple[dict | None, float | None]:
    answer = answers.get(key)
    if isinstance(answer, BoxAnswer):
        return answer.box.model_dump(), answer.confidence
    return None, None


def _yes(answers: dict[str, ImageAnswer], key: str) -> bool | None:
    answer = answers.get(key)
    return answer.noul >= 0.5 if isinstance(answer, NoulAnswer) else None


def assessment_from_answers(
    answers: dict[str, ImageAnswer], pages: int, limitations: list[str] | None = None
) -> StructureAssessment:
    """Build an assessment from one structure request's answers."""
    readable = _yes(answers, "readable")
    content = _yes(answers, "content_present")
    observations: list[Observation] = []
    layout = answers.get("layout")

    found: dict[str, tuple[int, dict | None, float | None]] = {}
    for page in range(1, pages + 1):
        prefix = f"p{page}_"
        for check in CHECKS:
            answer = answers.get(f"{prefix}{check}")
            if not isinstance(answer, OptionAnswer):
                continue
            box, confidence = _boxed(answers, f"{prefix}{check}_box")
            observations.append(
                Observation(
                    check=check,
                    page=page - 1,
                    answer=_outcome(answer),
                    box=box,
                    box_confidence=confidence,
                )
            )
        for section in SECTION_KEYS:
            if _yes(answers, f"{prefix}{section}_present") and section not in found:
                box, confidence = _boxed(answers, f"{prefix}{section}_box")
                found[section] = (page - 1, box, confidence)

    # Presence and order are document-level. A two-page CV is not a defect because
    # page two has no header.
    missing_required = [name for name in REQUIRED_SECTIONS if name not in found]
    observations.append(
        Observation(
            check="sections",
            page=found.get(missing_required[0], (0,))[0] if missing_required else 0,
            answer="pass" if not missing_required else (
                "minor" if len(missing_required) == 1 else "major"
            ),
            note=(
                "Missing required sections: " + ", ".join(missing_required) + "."
                if missing_required
                else ""
            ),
        )
    )
    observations.append(_order_observation(found))

    if isinstance(layout, OptionAnswer):
        columns = "pass" if layout.choice in ("one_column", "table") else "major"
        tables = "pass" if layout.choice == "one_column" else (
            "major" if layout.choice == "table" else
            "minor" if layout.choice == "mixed" else "pass"
        )
        observations.append(Observation(check="columns", page=0, answer=columns,
                                        note=f"Layout reported as {layout.choice}."))
        observations.append(Observation(check="tables", page=0, answer=tables,
                                        note=f"Layout reported as {layout.choice}."))
    notes = list(limitations or [])
    if readable is None:
        notes.append("The model did not report whether the page was readable.")
    return StructureAssessment(
        pages=pages,
        readable=True if readable is None else readable,
        content_present=True if content is None else content,
        observations=observations,
        limitations=notes,
    )


def _order_observation(
    found: dict[str, tuple[int, dict | None, float | None]]
) -> Observation:
    """Section order needs reliable boxes; without them the check is unverified."""
    ordered = [(name, page, box, confidence) for name, (page, box, confidence) in found.items()]
    if len(ordered) < 2:
        return Observation(check="section_order", page=0, answer="unable_to_assess")
    if any(box is None or confidence is None or confidence < MIN_BOX_CONFIDENCE
           for _, _, box, confidence in ordered):
        return Observation(
            check="section_order",
            page=0,
            answer="unable_to_assess",
            note="Section boxes were below the confidence threshold.",
        )
    order = [name for name, _, _, _ in sorted(ordered, key=lambda item: (item[1], item[2]["top"]))]
    expected = [name for name in EXPECTED_SECTION_ORDER if name in order]
    return Observation(
        check="section_order",
        page=0,
        answer="pass" if order == expected else "minor",
        note="" if order == expected else "Observed order: " + ", ".join(order) + ".",
    )
