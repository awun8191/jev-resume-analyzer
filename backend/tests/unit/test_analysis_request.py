"""Unit tests for reading the analysis request in both accepted shapes."""

import asyncio
import json

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.config import Settings
from app.errors import AppError
from app.main import app
from app.services.analysis_request import parse_json, read_analysis

BOUNDARY = "----jev-synthetic-boundary"
SETTINGS = Settings(_env_file=None)


def multipart(parts: list[tuple[str, str | None, bytes]]) -> Request:
    body = bytearray()
    for name, filename, data in parts:
        body.extend(f"--{BOUNDARY}\r\n".encode())
        if filename is None:
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        else:
            body.extend(
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\nContent-Type: application/pdf\r\n\r\n'
                ).encode()
            )
        body.extend(data)
        body.extend(b"\r\n")
    body.extend(f"--{BOUNDARY}--\r\n".encode())

    async def receive():
        return {"type": "http.request", "body": bytes(body), "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/analyses",
        "headers": [
            (b"content-type", f"multipart/form-data; boundary={BOUNDARY}".encode()),
            (b"content-length", str(len(body)).encode()),
        ],
    }
    return Request(scope, receive)


def json_request(payload: dict) -> Request:
    body = json.dumps(payload).encode()

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/analyses",
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ],
    }
    return Request(scope, receive)


def read(request: Request):
    return asyncio.run(read_analysis(request, SETTINGS))


def test_json_body_still_works_and_carries_no_file():
    body, upload = read(json_request({"mode": "review", "cv_text": "Synthetic CV."}))
    assert body.cv_text == "Synthetic CV."
    assert body.job_text is None
    assert upload is None


def test_the_request_part_is_read_like_a_json_body():
    payload = json.dumps({"mode": "review", "cv_text": "Synthetic CV."}).encode()
    body, upload = read(multipart([("request", None, payload)]))
    assert body.cv_text == "Synthetic CV."
    assert upload is None


def test_a_file_part_is_returned_untouched():
    payload = json.dumps({"mode": "review", "cv_text": "Synthetic CV."}).encode()
    pdf = b"%PDF-1.4 synthetic"
    body, upload = read(multipart([("request", None, payload), ("file", "cv.pdf", pdf)]))
    assert body.cv_text == "Synthetic CV."
    assert upload == pdf


def test_the_request_part_may_be_sent_as_an_upload():
    payload = json.dumps({"mode": "review", "cv_text": "Synthetic CV."}).encode()
    body, upload = read(multipart([("request", "request.json", payload)]))
    assert body.cv_text == "Synthetic CV."
    assert upload is None


def test_parts_are_order_independent():
    payload = json.dumps({"mode": "review", "cv_text": "Synthetic CV."}).encode()
    body, upload = read(multipart([("file", "cv.pdf", b"%PDF-1.4 x"), ("request", None, payload)]))
    assert upload == b"%PDF-1.4 x"
    assert body.cv_text == "Synthetic CV."


@pytest.mark.parametrize(
    "parts",
    [
        [("request", None, b"{}")],
        [("request", None, b"not json")],
        [("request", None, b'[{"mode": "review"}]')],
        [("request", None, b'{"mode": "review", "cv_text": "  "}')],
        [("request", None, b'{"mode": "review", "cv_text": "x", "extra": 1}')],
        [("request", None, b'{"mode": "review", "cv_text": "x", "job_text": null}')],
        [("other", None, b'{"mode": "review", "cv_text": "x"}')],
    ],
)
def test_a_bad_request_part_is_a_422(parts):
    with pytest.raises(AppError) as caught:
        read(multipart(parts))
    assert caught.value.status == 422
    assert caught.value.code == "INVALID_INPUT"


def test_a_duplicate_part_is_refused():
    payload = json.dumps({"mode": "review", "cv_text": "Synthetic CV."}).encode()
    with pytest.raises(AppError):
        read(multipart([("request", None, payload), ("request", None, payload)]))


def test_an_empty_file_is_refused():
    payload = json.dumps({"mode": "review", "cv_text": "Synthetic CV."}).encode()
    with pytest.raises(AppError) as caught:
        read(multipart([("request", None, payload), ("file", "cv.pdf", b"")]))
    assert caught.value.status == 422


def test_a_lone_surrogate_text_is_refused():
    with pytest.raises(AppError):
        parse_json(b'{"mode":"review","cv_text":"\\ud800"}')


def test_a_text_part_that_is_a_file_must_be_a_file():
    payload = json.dumps({"mode": "review", "cv_text": "Synthetic CV."}).encode()
    with pytest.raises(AppError):
        read(multipart([("request", None, payload), ("file", None, b"%PDF-1.4 x")]))


def test_the_endpoint_refuses_a_multipart_body_without_a_request_part():
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/analyses", files={"file": ("cv.pdf", b"%PDF-1.4 x", "application/pdf")}
        )
    assert response.status_code == 422
    assert set(response.json()) == {"error", "request_id"}
