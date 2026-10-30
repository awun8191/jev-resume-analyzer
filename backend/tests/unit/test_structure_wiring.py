"""Unit tests for the structure route wiring: rows, merging, page budget, failure."""

from io import BytesIO

import pytest
from pypdf import PdfWriter

from app.errors import AppError
from app.models.image_answers import BoxAnswer, BoxEdges, ImageResponse, NoulAnswer, OptionAnswer
from app.models.questions import Usage
from app.rubrics.structure_v1 import CHECKS, StructureReport
from app.services import structure_review as wiring
from app.services.page_render import RenderError

SECTION_TOPS = {
    "header": 0.05,
    "summary": 0.15,
    "experience": 0.25,
    "education": 0.55,
    "skills": 0.75,
    "projects": 0.85,
}


def blank_pdf(pages: int) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def option(choice: str) -> OptionAnswer:
    return OptionAnswer(type="choice", choice=choice, probabilities=None, confidence=0.9)


def noul(value: float) -> NoulAnswer:
    return NoulAnswer(type="noul", noul=value)


def box(top: float) -> BoxAnswer:
    return BoxAnswer(
        type="box",
        box=BoxEdges(top=top, bottom=min(0.99, top + 0.08), left=0.1, right=0.9),
        confidence=0.9,
    )


def perfect_answers(questions: dict) -> dict:
    answers = {}
    for key in questions:
        if key == "layout":
            answers[key] = option("one_column")
        elif key in ("readable", "content_present"):
            answers[key] = noul(1.0)
        elif key.endswith("_present"):
            answers[key] = noul(1.0)
        elif key.endswith("_box"):
            section = key.split("_", 1)[1].removesuffix("_box")
            answers[key] = box(SECTION_TOPS.get(section, 0.5))
        else:
            answers[key] = option("pass")
    return answers


class FakeImageGateway:
    def __init__(self):
        self.requests = []
        self.error = None

    async def evaluate_image(self, request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return ImageResponse(
            model="jev-1.14.0",
            answers=perfect_answers(request.body["questions"]),
            usage=Usage(input_tokens=100, output_tokens=20),
        )


def test_a_clean_page_scores_one_hundred_with_eleven_rows():
    gateway = FakeImageGateway()
    outcome = run(wiring.assess(blank_pdf(1), gateway))
    assert outcome.score == 100
    assert outcome.reason == "scored"
    assert outcome.assessed_weight == 100
    assert len(outcome.dimensions) == 11
    assert sum(row.weight for row in outcome.dimensions) == 100
    assert {row.value for row in outcome.dimensions} == {100}
    assert all(row.owner == "structure" for row in outcome.dimensions)
    assert {finding.severity for finding in outcome.findings} == {"pass"}
    assert len(outcome.findings) == 11
    assert outcome.input_tokens == 100
    assert outcome.output_tokens == 20
    assert outcome.warnings == ()


def test_the_request_pins_the_model_and_sends_the_danger_zone_header():
    gateway = FakeImageGateway()
    run(wiring.assess(blank_pdf(1), gateway))
    request = gateway.requests[0]
    assert request.body["model"] == "jev-1.14.0"
    assert request.body["state"]["page_count"] == 1
    assert request.headers == {"TypeSafe-Danger-Zone-Images": "true"}
    assert request.transport == "multipart"


def test_chunks_are_three_pages_and_answers_are_merged_per_document():
    gateway = FakeImageGateway()
    outcome = run(wiring.assess(blank_pdf(6), gateway))
    assert len(gateway.requests) == 2
    assert [sorted(request.body["state"]["pages"]) for request in gateway.requests] == [
        ["p1", "p2", "p3"],
        ["p4", "p5", "p6"],
    ]
    assert outcome.score == 100
    assert outcome.input_tokens == 200
    assert outcome.output_tokens == 40


def test_a_seven_page_document_is_scored_on_six_pages_with_a_warning():
    gateway = FakeImageGateway()
    outcome = run(wiring.assess(blank_pdf(7), gateway))
    assert len(gateway.requests) == 2
    codes = [warning.code for warning in outcome.warnings]
    assert "structure_page_budget" in codes
    warning = next(w for w in outcome.warnings if w.code == "structure_page_budget")
    assert "first 6 of 7 pages" in warning.message
    assert outcome.score == 100


def test_a_missing_file_is_a_null_score_with_a_reason():
    outcome = run(wiring.assess(None, FakeImageGateway()))
    assert outcome.score is None
    assert outcome.reason == "no_file"
    assert outcome.dimensions == ()
    assert outcome.findings == ()
    assert outcome.warnings[0].code == "structure_unavailable"
    assert "only content was scored" in outcome.warnings[0].message


def test_a_non_pdf_file_is_refused_for_the_structure_route():
    outcome = run(wiring.assess(b"PK\x03\x04synthetic docx bytes", FakeImageGateway()))
    assert outcome.score is None
    assert outcome.reason == "unsupported_format"
    assert outcome.warnings[0].code == "structure_unavailable"
    assert "Only a PDF" in outcome.warnings[0].message


def test_an_unreadable_pdf_never_scores_zero():
    outcome = run(wiring.assess(b"%PDF-1.7 broken", FakeImageGateway()))
    assert outcome.score is None
    assert outcome.reason == "render_failed"


def test_a_render_failure_keeps_the_page_budget_warning(monkeypatch):
    def fail(*args, **kwargs):
        raise RenderError("UNREADABLE_PDF", "Page could not be rendered.")

    monkeypatch.setattr(wiring, "render_pages", fail)
    outcome = run(wiring.assess(blank_pdf(7), FakeImageGateway()))
    assert outcome.score is None
    assert outcome.reason == "render_failed"
    codes = {warning.code for warning in outcome.warnings}
    assert codes == {"structure_page_budget", "structure_unavailable"}


def test_a_provider_failure_degrades_to_content_only():
    gateway = FakeImageGateway()
    gateway.error = AppError(502, "PROVIDER_FAILURE", "Provider could not complete.")
    outcome = run(wiring.assess(blank_pdf(2), gateway))
    assert outcome.score is None
    assert outcome.reason == "provider_error"
    assert outcome.input_tokens is None


def test_merge_keeps_the_worst_readability_and_the_first_layout():
    chunks = [
        {
            "readable": noul(1.0),
            "content_present": noul(1.0),
            "layout": option("one_column"),
            "p1_margins": option("pass"),
        },
        {
            "readable": noul(0.1),
            "content_present": noul(0.0),
            "layout": option("two_columns"),
            "p4_margins": option("major"),
        },
    ]
    merged = wiring.merge_answers(chunks)
    assert merged["readable"].noul == 0.1
    assert merged["content_present"].noul == 0.0
    assert merged["layout"].choice == "one_column"
    assert merged["p1_margins"].choice == "pass"
    assert merged["p4_margins"].choice == "major"


def test_rows_of_a_perfect_report_use_the_rubric_weights():
    report = StructureReport(
        score=100, reason="scored", assessable_weight=100, lost_points=0, findings=[]
    )
    dimensions, findings = wiring.rows(report)
    assert [row.key for row in dimensions] == list(CHECKS)
    assert [row.weight for row in dimensions] == [weight for weight, _ in CHECKS.values()]
    assert all(finding.severity == "pass" for finding in findings)
    assert all(finding.points_lost == 0 for finding in findings)


def test_a_minor_defect_halves_its_own_row():
    from app.rubrics.structure_v1 import StructureFinding

    report = StructureReport(
        score=95,
        reason="scored",
        assessable_weight=100,
        lost_points=5,
        findings=[
            StructureFinding(
                key="margins",
                page=0,
                box={"top": 0.0, "bottom": 1.0, "left": 0.0, "right": 1.0},
                severity="minor",
                points_lost=5,
                evidence="One margin is tight.",
            )
        ],
    )
    dimensions, findings = wiring.rows(report)
    margins = next(row for row in dimensions if row.key == "margins")
    assert margins.weight == 10
    assert margins.value == 50
    defect = next(finding for finding in findings if finding.id == "margins")
    assert defect.severity == "minor"
    assert defect.points_lost == 5
    assert defect.page == 0
    assert defect.box is not None


def test_a_page_not_readable_has_no_pass_rows():
    from app.rubrics.structure_v1 import StructureFinding

    report = StructureReport(
        score=None,
        reason="page_not_readable",
        assessable_weight=0,
        lost_points=0,
        findings=[
            StructureFinding(
                key="unreadable",
                page=0,
                box={"top": 0.0, "bottom": 1.0, "left": 0.0, "right": 1.0},
                severity="unverified",
                points_lost=0,
                evidence="The page image could not be read.",
            )
        ],
    )
    dimensions, findings = wiring.rows(report)
    assert dimensions == ()
    assert [finding.id for finding in findings] == ["unreadable"]
    assert findings[0].severity == "unassessable"
    assert findings[0].label == "Page readable"


@pytest.mark.parametrize(
    "reason", ["no_file", "unsupported_format", "render_failed", "provider_error"]
)
def test_unavailable_reasons_are_the_documented_set(reason):
    outcome = wiring.unavailable(reason)
    assert outcome.score is None
    assert outcome.reason == reason
    assert outcome.warnings[0].code == "structure_unavailable"


def run(coroutine):
    import asyncio

    return asyncio.run(coroutine)
