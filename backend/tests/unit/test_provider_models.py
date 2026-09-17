import asyncio

import httpx
import pytest
from pydantic import ValidationError

from app.config import Settings
from app.errors import AppError
from app.gateways.typesafe import TypeSafeGateway
from app.models.questions import ChoiceAnswer


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 1.1, True, "0.4"])
def test_invalid_confidence(value):
    with pytest.raises(ValidationError):
        ChoiceAnswer.model_validate({"type": "choice", "choice": "present", "confidence": value})


def test_missing_distribution_not_fabricated():
    answer = ChoiceAnswer.model_validate({"type": "choice", "choice": "not_applicable"})
    assert answer.probabilities is None
    assert answer.confidence is None


@pytest.mark.parametrize(
    "content",
    [
        b"not json",
        b'{"answers":{},"answers":{}}',
        b'{"model":"jev-latest","answers":{"q":{"type":"choice","choice":"present",'
        b'"confidence":NaN}}}',
        b"x" * 262145,
    ],
)
def test_wire_corruption_safe(content):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, content=content))
        ) as client:
            gateway = TypeSafeGateway(client, Settings(_env_file=None, typesafe_api_key="fake"))
            with pytest.raises(AppError) as error:
                await gateway.evaluate({"cv_text": "synthetic"}, {"q": {}})
            assert error.value.status == 502

    asyncio.run(run())


def test_utf8_budget_rejects_before_call():
    calls = []

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: calls.append(request))
        ) as client:
            gateway = TypeSafeGateway(client, Settings(_env_file=None, typesafe_api_key="fake"))
            with pytest.raises(AppError) as error:
                await gateway.evaluate({"cv_text": "字" * 10000}, {"q": {}})
            assert error.value.status == 413

    asyncio.run(run())
    assert not calls


def test_distribution_tolerance():
    answer = {
        "type": "choice",
        "choice": "present",
        "probabilities": {
            "present": 0.7005,
            "absent": 0.1,
            "not_applicable": 0.1,
            "unable_to_assess": 0.1,
        },
    }
    assert ChoiceAnswer.model_validate(answer).probabilities.present == 0.7005
    answer["probabilities"]["present"] = 0.702
    with pytest.raises(ValidationError):
        ChoiceAnswer.model_validate(answer)
