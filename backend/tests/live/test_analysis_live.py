"""Explicitly gated live test: one analysis, two billable calls, synthetic fixture.

Run with a key in backend/.env and a local API on 127.0.0.1:8017:

    JEV_RUN_LIVE=1 uv run pytest tests/live/test_analysis_live.py -s

The fixture is the committed synthetic two page resume. Nothing here prints the key,
the document text or the answer set.
"""

import json
import os
from pathlib import Path
from time import perf_counter

import httpx
import pytest

from app.rubrics.cv_review_v3 import IDS
from app.rubrics.scoring_v3 import band_for

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "two_page_resume.pdf"
BASE_URL = "http://127.0.0.1:8017"
POSTING = (
    "Synthetic verification posting: build and maintain Python APIs. "
    "Qualification: Python programming experience."
)


def require(condition, message):
    # Avoid pytest assertion introspection printing a provider body on failure.
    if not condition:
        print(message)
        pytest.fail(message, pytrace=False)


@pytest.mark.live
@pytest.mark.skipif(os.environ.get("JEV_RUN_LIVE") != "1", reason="Billable live test is opt-in")
def test_the_two_page_fixture_returns_a_combined_score():
    pdf = FIXTURE.read_bytes()
    with httpx.Client(base_url=BASE_URL, timeout=115, trust_env=False) as client:
        health = client.get("/api/v1/health")
        require(health.status_code == 200, "Local backend health failed")
        extraction = client.post(
            "/api/v1/documents/extract",
            files={"file": ("synthetic-two-page.pdf", pdf, "application/pdf")},
        )
        require(
            extraction.status_code == 200,
            f"Fixture extraction returned HTTP {extraction.status_code}",
        )
        text = extraction.json()["text"]
        require(text.strip(), "Fixture extraction returned no text")
        request = {"mode": "review", "cv_text": text, "job_text": POSTING}
        started = perf_counter()
        response = client.post(
            "/api/v1/analyses",
            files={
                "request": (None, json.dumps(request)),
                "file": ("synthetic-two-page.pdf", pdf, "application/pdf"),
            },
        )
        elapsed_ms = (perf_counter() - started) * 1000

    require(response.status_code == 200, f"Analysis returned HTTP {response.status_code}")
    body = response.json()
    scores = body["scores"]
    content = scores["content"]["value"]
    structure = scores["structure"]["value"]
    total = scores["total"]["value"]

    require(body["rubric_version"] == "v3", "Rubric version is not v3")
    require(content is not None, "Content score is null")
    require(
        structure is not None,
        f"Structure score is null for a PDF upload: {scores['structure']['reason']}",
    )
    require(scores["total"]["mode"] == "combined", "Total is not a combined score")
    require(total is not None, "Total score is null")
    require(
        total == round(0.7 * content + 0.3 * structure),
        "Total does not follow the 0.7 content and 0.3 structure rule",
    )
    require(len(body["findings"]) == len(IDS), "Expected one finding per rubric question")
    require(
        scores["content"]["band"] == band_for(content),
        "Content band does not follow the reported content score",
    )
    require(
        scores["total"]["band"] == band_for(total),
        "Total band does not follow the reported total score",
    )
    require(len(body["structure_findings"]) == 11, "Expected eleven structure checks")
    require(body["overview"]["rating"] is None, "Rating must remain null")
    require(body["metrics"]["cost_usd"] is None, "Cost must remain null")
    require(
        body["metrics"]["input_tokens"] is None or body["metrics"]["input_tokens"] > 0,
        "Unexpected token count",
    )
    severities = {}
    for finding in body["structure_findings"]:
        severities[finding["severity"]] = severities.get(finding["severity"], 0) + 1
    print(
        json.dumps(
            {
                "model": body["model"],
                "rubric_version": body["rubric_version"],
                "content": scores["content"],
                "structure": scores["structure"],
                "total": scores["total"],
                "dimensions": len(body["dimensions"]),
                "structure_severities": severities,
                "warnings": [warning["code"] for warning in body["warnings"]],
                "metrics": body["metrics"],
                "http_elapsed_ms": round(elapsed_ms, 1),
            }
        )
    )
