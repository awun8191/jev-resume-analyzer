"""The real gateway sends an image request as documented multipart."""

import asyncio
import json

import httpx
import pytest

from app.config import Settings
from app.errors import AppError
from app.gateways.typesafe import TypeSafeGateway
from app.rubrics.structure_questions_v1 import structure_questions
from app.services.image_request import build_image_request
from tests.fakes import page_image, perfect_structure_answers

SETTINGS = Settings(_env_file=None, typesafe_api_key="synthetic-test-key")


def built(pages=(1,)):
    return build_image_request(
        [page_image(number) for number in pages],
        structure_questions(list(pages)),
        document_note="Synthetic page",
        model="jev-1.14.0",
    )


def gateway(handler):
    return TypeSafeGateway(httpx.AsyncClient(transport=httpx.MockTransport(handler)), SETTINGS)


def test_the_image_call_is_multipart_with_the_danger_zone_header():
    seen = {}

    def handle(request):
        assert request.method == "POST"
        seen["content_type"] = request.headers["content-type"]
        seen["danger"] = request.headers.get("typesafe-danger-zone-images")
        seen["auth"] = request.headers["authorization"]
        body = request.content
        head, rest = body.split(b"\r\n\r\n", 1)
        assert b'name="request"' in head
        payload = json.loads(rest.split(b"\r\n--", 1)[0])
        seen["payload"] = payload
        answers = perfect_structure_answers(payload["questions"])
        return httpx.Response(
            200,
            json={
                "model": "jev-1.14.0",
                "answers": {key: answer.model_dump() for key, answer in answers.items()},
            },
        )

    request = built()
    result = asyncio.run(gateway(handle).evaluate_image(request))
    assert seen["danger"] == "true"
    assert seen["content_type"].startswith("multipart/form-data; boundary=")
    assert seen["auth"] == "Bearer synthetic-test-key"
    assert seen["payload"]["model"] == "jev-1.14.0"
    assert len(result.answers) == len(request.body["questions"])


def test_a_partial_image_answer_set_is_a_failure():
    def handle(request):
        payload = json.loads(request.content.split(b"\r\n\r\n", 1)[1].split(b"\r\n--", 1)[0])
        answers = perfect_structure_answers(payload["questions"])
        answers.pop(next(iter(answers)))
        return httpx.Response(
            200,
            json={
                "model": "jev-1.14.0",
                "answers": {key: answer.model_dump() for key, answer in answers.items()},
            },
        )

    with pytest.raises(AppError) as caught:
        asyncio.run(gateway(handle).evaluate_image(built()))
    assert caught.value.status == 502


@pytest.mark.parametrize("status,expected", [(429, 429), (529, 503), (401, 503), (500, 502)])
def test_image_call_status_mapping(status, expected):
    def handle(request):
        return httpx.Response(status, json={"error": "synthetic"})

    with pytest.raises(AppError) as caught:
        asyncio.run(gateway(handle).evaluate_image(built()))
    assert caught.value.status == expected


def test_an_image_call_is_never_replayed():
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(500, json={"error": "synthetic"})

    with pytest.raises(AppError):
        asyncio.run(gateway(handle).evaluate_image(built()))
    assert len(calls) == 1
