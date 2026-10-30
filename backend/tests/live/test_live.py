"""Explicitly gated, one billable POST. No personal text/report is printed or persisted."""

import json
import os
import subprocess
from pathlib import Path
from time import perf_counter

import httpx
import pytest

from tests.integration.test_documents import docx_bytes

ROOT = Path(__file__).resolve().parents[2]


def require(condition, message):
    # Avoid pytest assertion introspection printing personal response bodies on failure.
    if not condition:
        print(message)
        pytest.fail(message, pytrace=False)


@pytest.mark.live
@pytest.mark.skipif(os.environ.get("JEV_RUN_LIVE") != "1", reason="Billable live test is opt-in")
def test_authorized_resume_through_running_api():
    with httpx.Client(base_url="http://127.0.0.1:8017", timeout=115, trust_env=False) as client:
        health = client.get("/api/v1/health")
        require(health.status_code == 200, "Local backend health failed")
        docx = client.post(
            "/api/v1/documents/extract", files={"file": ("synthetic.docx", docx_bytes())}
        )
        require(docx.status_code == 200, "Synthetic DOCX extraction failed")
        with Path("/home/admin/Downloads/Dauda Nasir Resume.pdf").open("rb") as source:
            extraction = client.post(
                "/api/v1/documents/extract",
                files={"file": ("authorized.pdf", source, "application/pdf")},
            )
        require(extraction.status_code == 200, "Authorized PDF extraction failed")
        start = perf_counter()
        report = client.post(
            "/api/v1/analyses",
            json={
                "mode": "review",
                "cv_text": extraction.json()["text"],
                "job_text": "Synthetic verification posting: develop and maintain Python APIs. "
                "Qualification: Python programming experience.",
            },
        )
        elapsed = (perf_counter() - start) * 1000
        require(report.status_code == 200, f"Analysis returned HTTP {report.status_code}")
        body = report.json()
        require(len(body["findings"]) == 14, "Expected fourteen real provider findings")
        require(body["rubric_version"] == "v3", "Rubric version is not v3")
        require(
            body["scores"]["total"]["mode"] == "content_only",
            "A JSON analysis without a file must be content only",
        )
        require(body["overview"]["rating"] is None, "Rating must remain null")
        require(body["metrics"]["cost_usd"] is None, "Cost must remain null")
        validation = subprocess.run(
            ["node", str(ROOT / "scripts/validate_contract.mjs")],
            input=json.dumps(
                [
                    {"schema": "HealthSchema", "data": health.json()},
                    {"schema": "ExtractionSchema", "data": docx.json()},
                    {"schema": "ExtractionSchema", "data": extraction.json()},
                    {"schema": "AnalysisReportSchema", "data": body},
                ]
            ),
            text=True,
            capture_output=True,
            timeout=20,
        )
        require(validation.returncode == 0, "Actual backend responses failed Zod validation")
        print(
            json.dumps(
                {
                    "model": body["model"],
                    "findings": len(body["findings"]),
                    "metrics": body["metrics"],
                    "http_elapsed_ms": round(elapsed, 2),
                    "pdf_pages": extraction.json()["page_count"],
                    "pdf_characters": len(extraction.json()["text"]),
                    "zod": json.loads(validation.stdout),
                }
            )
        )
