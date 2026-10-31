import json
from copy import deepcopy

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_gateway, get_settings
from app.gateways.typesafe import TypeSafeGateway
from app.main import app
from app.rubrics.cv_review_v3 import IDS
from app.services.reader_criteria import plain_criteria

OPTIONS = ["present", "absent", "not_applicable", "unable_to_assess"]


def reply(payload):
    return {
        "model": "jev-latest",
        "answers": {
            key: {
                "type": "choice",
                "choice": "present",
                "probabilities": dict(zip(OPTIONS, [0.7, 0.1, 0.1, 0.1])),
                "confidence": 0.6,
            }
            for key in payload["questions"]
        },
        "usage": {"input_tokens": 123, "output_tokens": 45},
    }


@pytest.fixture
def harness():
    calls = []
    behavior = {"mutate": lambda value: value, "status": 200}

    def handle(request):
        payload = json.loads(request.content)
        calls.append(payload)
        if behavior.get("timeout"):
            raise httpx.ReadTimeout("DO NOT EXPOSE PROVIDER OR APPLICANT DATA")
        return httpx.Response(behavior["status"], json=behavior["mutate"](reply(payload)))

    settings = Settings(_env_file=None, typesafe_api_key="synthetic-test-key")
    provider = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_gateway] = lambda: TypeSafeGateway(provider, settings)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, calls, behavior
    app.dependency_overrides.clear()


@pytest.mark.parametrize("with_job", [False, True])
def test_full_document_one_call(harness, with_job):
    client, calls, _ = harness
    body = {"mode": "review", "cv_text": "Synthetic CV. Built a useful project."}
    if with_job:
        body["job_text"] = "Synthetic role: build useful projects."
    response = client.post("/api/v1/analyses", json=body)
    assert response.status_code == 200
    report = response.json()
    assert len(calls) == 1
    assert calls[0]["state"]["cv_text"] == body["cv_text"]
    # The v3 flow sends the text and nothing else. No bullet preparation.
    expected_state = {"cv_text", "job_text"} if with_job else {"cv_text"}
    assert set(calls[0]["state"]) == expected_state
    assert len(calls[0]["questions"]) == len(IDS)
    for finding in report["findings"]:
        actual = calls[0]["questions"][finding["question_id"]]
        assert actual["type"] == "choice"
        assert set(actual["criteria"]) == set(OPTIONS)
        assert finding["question"] == actual["instructions"]
        # The wire carries the model criteria. The report carries the plain rule.
        assert finding["criteria"] == plain_criteria(finding["question_id"])
        assert finding["criteria"]
        assert finding["assessment_level"] == "full_document"
        assert finding["source"] == "provider"
        assert finding["probabilities"] == dict(zip(OPTIONS, [0.7, 0.1, 0.1, 0.1]))
    assert report["overview"] == {
        "questions_total": len(IDS),
        "questions_answered": len(IDS),
        "questions_assessable": len(IDS),
        "rating": None,
    }
    assert report["rubric_version"] == "v3"
    assert report["scores"]["content"]["value"] == 100
    assert report["scores"]["content"]["band"] == "Very strong evidence"
    assert report["scores"]["content"]["range"] == [100, 100]
    assert report["scores"]["content"]["assessed_weight"] == 100
    assert report["scores"]["content"]["coverage"] == 1.0
    # A JSON call carries no page image, so structure is null, not zero.
    assert report["scores"]["structure"] == {
        "value": None,
        "band": None,
        "reason": "no_file",
        "assessed_weight": 0,
    }
    assert report["scores"]["total"] == {
        "value": 100,
        "band": "Very strong evidence",
        "mode": "content_only",
    }
    assert [row["owner"] for row in report["dimensions"]] == ["content"] * 7
    assert [row["weight"] for row in report["dimensions"]] == [25, 15, 15, 15, 15, 10, 5]
    assert report["structure_findings"] == []
    codes = {warning["code"] for warning in report["warnings"]}
    assert "structure_unavailable" in codes
    assert "bullet_coverage" not in codes
    assert report["metrics"]["cost_usd"] is None
    assert report["metrics"]["input_tokens"] == 123
    assert report["metrics"]["duration_ms"] >= 0


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"mode": "alignment_only", "cv_text": "synthetic"},
        {"mode": "review", "cv_text": "  "},
        {"mode": "review", "cv_text": 1},
        {"mode": "review", "cv_text": "synthetic", "job_text": ""},
        {"mode": "review", "cv_text": "synthetic", "job_text": None},
        {"mode": "review", "cv_text": "synthetic", "extra": "private-marker"},
    ],
)
def test_invalid_input_no_calls(harness, body):
    client, calls, _ = harness
    response = client.post("/api/v1/analyses", json=body)
    assert response.status_code == 422
    assert "private-marker" not in response.text
    assert set(response.json()) == {"error", "request_id"}
    assert not calls


def test_large_text_no_calls(harness):
    client, calls, _ = harness
    result = client.post("/api/v1/analyses", json={"mode": "review", "cv_text": "x" * 40001})
    assert result.status_code == 413
    assert not calls


@pytest.mark.parametrize(
    "status,expected", [(401, 503), (403, 503), (422, 502), (429, 429), (529, 503), (500, 502)]
)
def test_upstream_status_no_retry(harness, status, expected):
    client, calls, behavior = harness
    behavior["status"] = status
    response = client.post("/api/v1/analyses", json={"mode": "review", "cv_text": "synthetic"})
    assert response.status_code == expected
    assert len(calls) == 1
    assert set(response.json()) == {"error", "request_id"}


def test_timeout(harness):
    client, calls, behavior = harness
    behavior["timeout"] = True
    response = client.post("/api/v1/analyses", json={"mode": "review", "cv_text": "synthetic"})
    assert response.status_code == 504
    assert len(calls) == 1
    assert "DO NOT EXPOSE" not in response.text


def mutate_response(value, defect):
    value = deepcopy(value)
    key = next(iter(value["answers"]))
    answer = value["answers"][key]
    if defect == "partial":
        del value["answers"][key]
    elif defect == "extra_id":
        value["answers"]["invented"] = answer
    elif defect == "wrong_type":
        answer["type"] = "noul"
    elif defect == "wrong_choice":
        answer["choice"] = "yes"
    elif defect == "missing_option":
        del answer["probabilities"]["absent"]
    elif defect == "extra_option":
        answer["probabilities"]["other"] = 0
    elif defect == "sum":
        answer["probabilities"]["present"] = 0.2
    elif defect == "numeric_string":
        answer["probabilities"]["present"] = "0.7"
    elif defect == "boolean":
        answer["confidence"] = True
    elif defect == "range":
        answer["confidence"] = 2
    elif defect == "usage":
        value["usage"]["input_tokens"] = -1
    elif defect == "model":
        value["model"] = ""
    elif defect == "not_maximum":
        answer["choice"] = "absent"
    return value


@pytest.mark.parametrize(
    "defect",
    [
        "partial",
        "extra_id",
        "wrong_type",
        "wrong_choice",
        "missing_option",
        "extra_option",
        "sum",
        "numeric_string",
        "boolean",
        "range",
        "usage",
        "model",
        "not_maximum",
    ],
)
def test_invalid_provider_no_report(harness, defect):
    client, calls, behavior = harness
    behavior["mutate"] = lambda value: mutate_response(value, defect)
    response = client.post("/api/v1/analyses", json={"mode": "review", "cv_text": "synthetic"})
    assert response.status_code == 502
    assert "findings" not in response.json()
    assert len(calls) == 1


def test_missing_key_and_health_no_provider():
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, typesafe_api_key="")
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            assert client.get("/api/v1/health").status_code == 200
            response = client.post(
                "/api/v1/analyses", json={"mode": "review", "cv_text": "synthetic"}
            )
        assert response.status_code == 503
    finally:
        app.dependency_overrides.clear()
