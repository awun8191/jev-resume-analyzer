"""Explicitly gated, billable image request. Synthetic fixture only, no personal data.

Run with a key in backend/.env and both switches set:

    JEV_RUN_IMAGE_LIVE=1 uv run pytest tests/live/test_image_live.py -s

Nothing here prints image bytes, document text or the API key.
"""

import os
from pathlib import Path
from time import perf_counter

import httpx
import pytest

from app.config import Settings
from app.rubrics.structure_questions_v1 import structure_questions
from app.rubrics.structure_v1 import assessment_from_answers, score_structure
from app.services.image_request import build_image_request, parse_image_response
from app.services.page_render import render_pages

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "two_page_resume.pdf"
ENDPOINT = "https://api.typesafe.ai/v1/systemone"
GATE = os.environ.get("JEV_RUN_IMAGE_LIVE") == "1"


def require(condition, message):
    # Avoid pytest assertion introspection printing a provider body on failure.
    if not condition:
        print(message)
        pytest.fail(message, pytrace=False)


@pytest.mark.live
@pytest.mark.skipif(not GATE, reason="Billable image test is opt-in")
def test_structure_request_returns_boxes_for_a_synthetic_resume():
    settings = Settings()
    require(
        bool(settings.typesafe_api_key.get_secret_value().strip()),
        "TYPESAFE_API_KEY is not set in backend/.env",
    )
    pages = render_pages(FIXTURE.read_bytes(), (1,))
    questions = structure_questions([1])
    request = build_image_request(
        pages,
        questions,
        document_note="One page of one resume, in reading order.",
        model="jev-1.14.0",
        transport="multipart",
    )
    kwargs = request.http_kwargs("jev-live-image-test")
    headers = {
        "Authorization": f"Bearer {settings.typesafe_api_key.get_secret_value().strip()}",
        **kwargs["headers"],
    }
    started = perf_counter()
    with httpx.Client(timeout=settings.typesafe_timeout_seconds, trust_env=False) as client:
        response = client.post(ENDPOINT, content=kwargs["content"], headers=headers)
    elapsed_ms = (perf_counter() - started) * 1000

    require(response.status_code == 200, f"Image request returned HTTP {response.status_code}")
    parsed = parse_image_response(response.json(), set(questions))
    require(parsed.model.startswith("jev-"), "Provider did not report a Jev model")
    require(len(parsed.answers) == len(questions), "Answer count does not match questions")
    boxes = [answer for answer in parsed.answers.values() if answer.type == "box"]
    require(len(boxes) == 13, f"Expected 13 Box answers, got {len(boxes)}")
    for answer in boxes:
        edges = answer.box
        require(edges.left < edges.right and edges.top < edges.bottom, "Unordered box edges")
        require(0 <= edges.left and edges.right <= 1, "Box left or right outside 0 to 1")
        require(0 <= edges.top and edges.bottom <= 1, "Box top or bottom outside 0 to 1")

    report = score_structure(assessment_from_answers(parsed.answers, 1))
    require(report.score is None or 0 <= report.score <= 100, "Score outside 0 to 100")
    require(
        report.reason in ("scored", "page_not_readable", "page_empty", "insufficient_evidence"),
        "Unknown score reason",
    )
    print(
        {
            "model": parsed.model,
            "usage": parsed.usage.model_dump() if parsed.usage else None,
            "elapsed_ms": round(elapsed_ms, 1),
            "image_px": [pages[0].width_px, pages[0].height_px],
            "image_bytes": pages[0].size_bytes,
            "questions": len(questions),
            "boxes": len(boxes),
            "structure_score": report.score,
            "structure_reason": report.reason,
            "findings": len(report.findings),
        }
    )
