"""Run the structure rubric over an uploaded PDF.

This is the wiring layer for the image route. It owns three things the rubric does
not: how many pages are reviewed, how pages are grouped into provider requests, and
what the report shows when the route cannot run. The score itself still comes from
``app.rubrics.structure_v1`` and the rubric weights are never repeated here.

Rules enforced here:

- At most six pages are reviewed; a longer document is scored on the first six and a
  warning says so.
- At most three page images go in one request, as the provider requires.
- The model is pinned to a version that supports Box questions.
- A missing, non-PDF or unrenderable file is a null score with a reason, never 0.
"""

from dataclasses import dataclass
from typing import Literal

from app.errors import AppError
from app.models.analyses import DimensionRow, StructureFindingItem, StructureScore
from app.models.documents import WarningItem
from app.models.image_answers import BoxEdges, ImageAnswer, NoulAnswer
from app.rubrics.scoring_v3 import band_for
from app.rubrics.structure_questions_v1 import structure_questions
from app.rubrics.structure_v1 import (
    CHECKS,
    StructureReport,
    assessment_from_answers,
    score_structure,
)
from app.services.image_request import RequestBuildError, build_image_request
from app.services.page_render import RenderError, page_count, render_pages

IMAGE_MODEL = "jev-1.14.0"
PAGES_PER_REQUEST = 3
MAX_REVIEW_PAGES = 6
PDF_SIGNATURE = b"%PDF-"

CHECK_LABELS = {
    "margins": "Margins",
    "alignment": "Alignment",
    "hierarchy": "Heading hierarchy",
    "spacing": "Vertical spacing",
    "sections": "Required sections",
    "section_order": "Section order",
    "density": "Density",
    "entry_format": "Entry format",
    "page_balance": "Page balance",
    "columns": "Columns",
    "tables": "Tables and text boxes",
    "unreadable": "Page readable",
    "page_empty": "Page content",
}

SEVERITY: dict[str, Literal["minor", "major", "unassessable"]] = {
    "minor": "minor",
    "major": "major",
    "unverified": "unassessable",
}

MISSING = {
    "no_file": (
        "No document was supplied with this analysis, so only content was scored. "
        "Send the PDF as the file part to score structure."
    ),
    "unsupported_format": (
        "Only a PDF can be scored for structure. This upload is not a PDF, so only "
        "content was scored."
    ),
    "render_failed": (
        "The PDF pages could not be rendered, so structure was not scored. Content was "
        "scored from the submitted text."
    ),
    "provider_error": (
        "The structure request did not complete, so structure was not scored. Content "
        "was scored from the submitted text."
    ),
}


@dataclass(frozen=True)
class StructureOutcome:
    """What the report needs from the structure route."""

    score: int | None = None
    band: str | None = None
    reason: str = "no_file"
    assessed_weight: int = 0
    findings: tuple[StructureFindingItem, ...] = ()
    dimensions: tuple[DimensionRow, ...] = ()
    warnings: tuple[WarningItem, ...] = ()
    input_tokens: int | None = None
    output_tokens: int | None = None
    pages_reviewed: int = 0

    def as_score(self) -> StructureScore:
        return StructureScore(
            value=self.score,
            band=self.band,
            reason=self.reason,
            assessed_weight=self.assessed_weight,
        )


def unavailable(reason: str, extra: tuple[WarningItem, ...] = ()) -> StructureOutcome:
    """A null structure score that says why it is null."""
    if reason not in MISSING:
        raise ValueError(f"Unknown structure reason: {reason}")
    warning = WarningItem(code="structure_unavailable", message=MISSING[reason])
    return StructureOutcome(reason=reason, warnings=(warning, *extra))


def _label(key: str) -> str:
    if key in CHECK_LABELS:
        return CHECK_LABELS[key]
    return key.replace("_", " ").capitalize()


def _value(weight: int, points_lost: int) -> int:
    return max(0, min(100, round(100 * (weight - points_lost) / weight)))


def rows(
    report: StructureReport,
) -> tuple[tuple[DimensionRow, ...], tuple[StructureFindingItem, ...]]:
    """Map one structure report to report rows. Weights come from the rubric only."""
    by_key = {finding.key: finding for finding in report.findings}
    dimensions: list[DimensionRow] = []
    findings: list[StructureFindingItem] = []
    scored = report.reason == "scored"
    if scored:
        for key, (weight, description) in CHECKS.items():
            item = by_key.get(key)
            dimensions.append(
                DimensionRow(
                    key=key,
                    label=_label(key),
                    owner="structure",
                    weight=weight,
                    value=_value(weight, item.points_lost) if item else 100,
                    section=None,
                )
            )
            findings.append(
                StructureFindingItem(
                    id=key,
                    label=_label(key),
                    severity=SEVERITY[item.severity] if item else "pass",
                    points_lost=item.points_lost if item else 0,
                    page=item.page if item else None,
                    box=BoxEdges(**item.box) if item else None,
                    confidence=item.box_confidence if item else None,
                    evidence=item.evidence if item else description,
                )
            )
        return tuple(dimensions), tuple(findings)
    for item in report.findings:
        findings.append(
            StructureFindingItem(
                id=item.key,
                label=_label(item.key),
                severity=SEVERITY[item.severity],
                points_lost=item.points_lost,
                page=item.page,
                box=BoxEdges(**item.box),
                confidence=item.box_confidence,
                evidence=item.evidence,
            )
        )
    return (), tuple(findings)


def merge_answers(chunks: list[dict[str, ImageAnswer]]) -> dict[str, ImageAnswer]:
    """Combine answer sets from several page groups into one document assessment.

    Page keys already carry their page number, so they never collide. The three
    document-level answers need a rule: readability and content presence take the
    worst group, because one unreadable page is a real limitation. Layout is read
    from the first group, which holds the first page.
    """
    merged: dict[str, ImageAnswer] = {}
    for answers in chunks:
        for key, answer in answers.items():
            if key in ("readable", "content_present") and isinstance(answer, NoulAnswer):
                previous = merged.get(key)
                if isinstance(previous, NoulAnswer):
                    answer = NoulAnswer(type="noul", noul=min(previous.noul, answer.noul))
            elif key in merged:
                continue
            merged[key] = answer
    return merged


def _sum(first: int | None, second: int | None) -> int | None:
    if first is None:
        return second
    if second is None:
        return first
    return first + second


async def assess(pdf: bytes | None, gateway) -> StructureOutcome:
    """Score structure for one uploaded file. Never raises for a bad upload."""
    if pdf is None:
        return unavailable("no_file")
    if not pdf.startswith(PDF_SIGNATURE):
        return unavailable("unsupported_format")
    try:
        total = page_count(pdf)
    except (RenderError, ValueError):
        return unavailable("render_failed")
    reviewed = min(total, MAX_REVIEW_PAGES)
    warnings: list[WarningItem] = []
    if total > MAX_REVIEW_PAGES:
        warnings.append(
            WarningItem(
                code="structure_page_budget",
                message=(
                    f"Structure was scored from the first {MAX_REVIEW_PAGES} of {total} "
                    "pages. The remaining pages were not reviewed for layout."
                ),
            )
        )
    chunks: list[dict[str, ImageAnswer]] = []
    input_tokens: int | None = None
    output_tokens: int | None = None
    for start in range(1, reviewed + 1, PAGES_PER_REQUEST):
        numbers = tuple(range(start, min(start + PAGES_PER_REQUEST, reviewed + 1)))
        note = (
            f"Pages {numbers[0]} to {numbers[-1]} of {total} of one resume, in reading "
            "order. Judge only the pages supplied."
        )
        try:
            pages = render_pages(pdf, numbers)
            request = build_image_request(
                pages,
                structure_questions(list(numbers)),
                document_note=note,
                model=IMAGE_MODEL,
            )
            response = await gateway.evaluate_image(request)
        except (RenderError, RequestBuildError):
            return unavailable("render_failed", tuple(warnings))
        except (AppError, ValueError, TypeError):
            return unavailable("provider_error", tuple(warnings))
        chunks.append(response.answers)
        if response.usage is not None:
            input_tokens = _sum(input_tokens, response.usage.input_tokens)
            output_tokens = _sum(output_tokens, response.usage.output_tokens)

    report = score_structure(assessment_from_answers(merge_answers(chunks), reviewed))
    dimensions, findings = rows(report)
    if report.score is None:
        warnings.append(
            WarningItem(
                code="structure_unavailable",
                message=report.limitations[0]
                if report.limitations
                else "Structure could not be scored from the page images.",
            )
        )
    return StructureOutcome(
        score=report.score,
        band=band_for(report.score),
        reason=report.reason,
        assessed_weight=report.assessable_weight,
        findings=findings,
        dimensions=dimensions,
        warnings=tuple(warnings),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        pages_reviewed=reviewed,
    )
