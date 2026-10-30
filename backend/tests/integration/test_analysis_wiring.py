"""Integration tests for the two-call analysis: text content plus image structure.

The gateway is a fake that answers both call kinds. The rasteriser is either the real
pdfium renderer over the committed two page fixture, or a fake that returns fixed
page images so page counts and failures can be exercised without a file.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_gateway, get_settings
from app.errors import AppError
from app.main import app
from app.rubrics.cv_review_v3 import IDS
from app.services import structure_review
from app.services.page_render import RenderError
from tests.fakes import FakeGateway, blank_pdf, page_image

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "two_page_resume.pdf"
DOCX = b"PK\x03\x04synthetic docx bytes"
BODY = {"mode": "review", "cv_text": "Synthetic CV. Built a routing service."}


def payload(**overrides):
    return {**BODY, **overrides}


@pytest.fixture
def harness():
    gateway = FakeGateway()
    settings = Settings(_env_file=None, typesafe_api_key="synthetic-test-key")
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_gateway] = lambda: gateway
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, gateway
    app.dependency_overrides.clear()


def post_with_file(client, body, data, filename="cv.pdf"):
    content_type = "application/pdf" if data.startswith(b"%PDF") else "application/octet-stream"
    return client.post(
        "/api/v1/analyses",
        files={
            "request": (None, json.dumps(body)),
            "file": (filename, data, content_type),
        },
    )


def post_text_only(client, body):
    return client.post("/api/v1/analyses", files={"request": (None, json.dumps(body))})


def test_content_and_structure_are_two_calls_on_one_report(harness):
    client, gateway = harness
    response = post_with_file(client, payload(), FIXTURE.read_bytes())
    assert response.status_code == 200
    report = response.json()

    assert len(gateway.text_calls) == 1
    assert len(gateway.image_calls) == 1
    assert gateway.text_calls[0]["state"]["cv_text"] == BODY["cv_text"]
    assert "job_text" not in gateway.text_calls[0]["state"]
    assert len(gateway.text_calls[0]["questions"]) == len(IDS)
    assert gateway.image_calls[0].body["model"] == "jev-1.14.0"
    assert gateway.image_calls[0].headers == {"TypeSafe-Danger-Zone-Images": "true"}
    assert gateway.image_calls[0].body["state"]["page_count"] == 2

    assert report["rubric_version"] == "v3"
    assert report["scores"]["content"]["value"] == 100
    assert report["scores"]["content"]["band"] == "Very strong evidence"
    assert report["scores"]["structure"] == {
        "value": 100,
        "band": "Very strong evidence",
        "reason": "scored",
        "assessed_weight": 100,
    }
    assert report["scores"]["total"] == {
        "value": 100,
        "band": "Very strong evidence",
        "mode": "combined",
    }
    owners = [row["owner"] for row in report["dimensions"]]
    assert owners.count("content") == 7
    assert owners.count("structure") == 11
    assert sum(row["weight"] for row in report["dimensions"] if row["owner"] == "structure") == 100
    assert len(report["structure_findings"]) == 11
    assert {finding["severity"] for finding in report["structure_findings"]} == {"pass"}
    # Both calls are summed, and the image call is a second billable request.
    assert report["metrics"]["input_tokens"] == 123 + 900
    assert report["metrics"]["output_tokens"] == 45 + 30
    assert report["metrics"]["cost_usd"] is None
    assert report["overview"]["questions_total"] == len(IDS)


def test_a_partial_structure_score_combines_at_the_documented_share(harness):
    client, gateway = harness
    gateway.image_layout = "two_columns"
    report = post_with_file(client, payload(), FIXTURE.read_bytes()).json()
    content = report["scores"]["content"]["value"]
    structure = report["scores"]["structure"]["value"]
    assert structure is not None and structure < content
    assert report["scores"]["total"]["value"] == round(0.7 * content + 0.3 * structure)
    assert report["scores"]["total"]["mode"] == "combined"
    columns = next(row for row in report["dimensions"] if row["key"] == "columns")
    assert columns["owner"] == "structure"
    assert columns["value"] < 100
    defect = next(item for item in report["structure_findings"] if item["id"] == "columns")
    assert defect["severity"] == "major"
    assert defect["points_lost"] == 8


def test_a_structure_provider_failure_keeps_the_content_report(harness):
    client, gateway = harness
    gateway.image_error = AppError(502, "PROVIDER_FAILURE", "Provider could not complete it.")
    response = post_with_file(client, payload(), FIXTURE.read_bytes())
    assert response.status_code == 200
    report = response.json()
    assert report["scores"]["content"]["value"] == 100
    assert report["scores"]["structure"] == {
        "value": None,
        "band": None,
        "reason": "provider_error",
        "assessed_weight": 0,
    }
    assert report["scores"]["total"] == {
        "value": 100,
        "band": "Very strong evidence",
        "mode": "content_only",
    }
    codes = {warning["code"] for warning in report["warnings"]}
    assert "structure_unavailable" in codes
    assert report["structure_findings"] == []
    # The text call still counted toward the metrics.
    assert report["metrics"]["input_tokens"] == 123


def test_a_non_pdf_file_is_refused_for_structure_and_content_still_scores(harness):
    client, gateway = harness
    report = post_with_file(client, payload(), DOCX, filename="cv.docx").json()
    assert report["scores"]["content"]["value"] == 100
    assert report["scores"]["structure"]["reason"] == "unsupported_format"
    assert report["scores"]["structure"]["value"] is None
    assert report["scores"]["total"]["mode"] == "content_only"
    assert gateway.image_calls == []
    warning = next(w for w in report["warnings"] if w["code"] == "structure_unavailable")
    assert "Only a PDF" in warning["message"]


def test_a_rasteriser_failure_never_returns_zero(harness, monkeypatch):
    client, gateway = harness

    def fail(*args, **kwargs):
        raise RenderError("UNREADABLE_PDF", "Page could not be rendered.")

    monkeypatch.setattr(structure_review, "render_pages", fail)
    report = post_with_file(client, payload(), FIXTURE.read_bytes()).json()
    assert report["scores"]["structure"]["value"] is None
    assert report["scores"]["structure"]["reason"] == "render_failed"
    assert report["scores"]["total"]["value"] == 100
    assert report["scores"]["total"]["mode"] == "content_only"


def test_six_pages_are_one_image_call_and_a_seventh_adds_a_warning(harness, monkeypatch):
    client, gateway = harness
    monkeypatch.setattr(structure_review, "page_count", lambda data: 9)
    monkeypatch.setattr(
        structure_review,
        "render_pages",
        lambda data, numbers, **kwargs: [page_image(n) for n in numbers],
    )
    report = post_with_file(client, payload(), blank_pdf(1)).json()
    assert len(gateway.image_calls) == 2
    assert [sorted(call.body["state"]["pages"]) for call in gateway.image_calls] == [
        ["p1", "p2", "p3"],
        ["p4", "p5", "p6"],
    ]
    assert report["scores"]["structure"]["value"] == 100
    warning = next(w for w in report["warnings"] if w["code"] == "structure_page_budget")
    assert "first 6 of 9 pages" in warning["message"]


def test_no_job_text_still_asks_every_question(harness):
    client, gateway = harness
    report = post_text_only(client, payload()).json()
    assert "job_text" not in gateway.text_calls[0]["state"]
    assert len(gateway.text_calls[0]["questions"]) == len(IDS)
    assert "alignment_scope" not in {warning["code"] for warning in report["warnings"]}


def test_a_posting_adds_the_alignment_scope_warning(harness):
    client, gateway = harness
    report = post_text_only(client, payload(job_text="Synthetic posting: build services.")).json()
    assert gateway.text_calls[0]["state"]["job_text"] == "Synthetic posting: build services."
    assert "alignment_scope" in {warning["code"] for warning in report["warnings"]}


def test_an_unassessable_answer_does_not_score_zero(harness):
    client, gateway = harness
    gateway.text_choice = "unable_to_assess"
    report = post_text_only(client, payload()).json()
    assert report["scores"]["content"]["value"] is None
    assert report["scores"]["content"]["assessed_weight"] == 0
    assert report["scores"]["content"]["range"] == [0, 100]
    assert report["scores"]["total"] == {"value": None, "band": None, "mode": "unavailable"}
    assert "unable_to_assess" in {warning["code"] for warning in report["warnings"]}


def test_not_applicable_leaves_the_denominator(harness):
    client, gateway = harness
    gateway.text_choice = "not_applicable"
    report = post_text_only(client, payload(job_text="Synthetic posting.")).json()
    assert report["scores"]["content"]["value"] is None
    assert report["scores"]["content"]["coverage"] == 0.0
    assert report["scores"]["content"]["assessed_weight"] == 0


def test_the_multipart_body_must_hold_the_request_part(harness):
    client, _ = harness
    response = client.post(
        "/api/v1/analyses", files={"file": ("cv.pdf", FIXTURE.read_bytes(), "application/pdf")}
    )
    assert response.status_code == 422
    assert set(response.json()) == {"error", "request_id"}
