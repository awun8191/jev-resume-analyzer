import asyncio
import json

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.errors import AppError
from app.models.questions import ProviderResponse

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
# Live docs say around 32k shared tokens, not an exact account-specific guarantee.
# Conservatively cap UTF-8 serialized bytes below that token count with headroom.
MAX_PROVIDER_BYTES = 28000
MAX_RESPONSE_BYTES = 262144


def invalid_response():
    return AppError(
        502,
        "PROVIDER_RESPONSE_INVALID",
        "Provider returned an invalid or incomplete answer set. No report was created.",
    )


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


class TypeSafeGateway:
    def __init__(self, client: httpx.AsyncClient, settings: Settings):
        self.client, self.settings = client, settings

    async def evaluate(self, state: dict, questions: dict) -> ProviderResponse:
        key = self.settings.typesafe_api_key.get_secret_value().strip()
        if not key:
            raise AppError(503, "PROVIDER_UNAVAILABLE", "Provider is not configured.", True)
        payload = {"model": self.settings.typesafe_model, "state": state, "questions": questions}
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if len(encoded) > MAX_PROVIDER_BYTES:
            raise AppError(
                413,
                "PROVIDER_INPUT_LIMIT",
                "CV, posting and rubric exceed the conservative single-call input budget. "
                "Shorten the submitted text; nothing was truncated or sent.",
            )
        try:
            async with asyncio.timeout(self.settings.typesafe_timeout_seconds):
                # httpx transport retries are disabled; never replay a billable POST.
                async with self.client.stream(
                    "POST",
                    ENDPOINT,
                    content=encoded,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    timeout=self.settings.typesafe_timeout_seconds,
                ) as response:
                    self.check_status(response.status_code)
                    data = bytearray()
                    async for chunk in response.aiter_bytes():
                        data.extend(chunk)
                        if len(data) > MAX_RESPONSE_BYTES:
                            raise invalid_response()
            parsed = json.loads(data, object_pairs_hook=unique_object)
            result = ProviderResponse.model_validate(parsed)
            if set(result.answers) != set(questions) or not result.model.strip():
                raise invalid_response()
            return result
        except (httpx.TimeoutException, TimeoutError):
            raise AppError(
                504,
                "PROVIDER_TIMEOUT",
                "Provider timed out. A manual retry may incur another charge.",
                True,
            ) from None
        except httpx.RequestError:
            raise AppError(
                502,
                "PROVIDER_CONNECTION_ERROR",
                "Provider connection failed. No report was created.",
                True,
            ) from None
        except (ValidationError, ValueError, TypeError, RecursionError):
            raise invalid_response() from None

    @staticmethod
    def check_status(status):
        if status == 200:
            return
        if status in (401, 403):
            raise AppError(
                503,
                "PROVIDER_UNAVAILABLE",
                "Provider authentication is unavailable. Check server configuration.",
            )
        if status == 429:
            raise AppError(
                429,
                "PROVIDER_RATE_LIMIT",
                "Provider rate limit reached. Wait before a manual retry.",
                True,
            )
        if status == 529:
            raise AppError(
                503,
                "PROVIDER_OVERLOADED",
                "Provider temporarily overloaded. Wait before a manual retry.",
                True,
            )
        raise AppError(502, "PROVIDER_FAILURE", "Provider could not complete this request.", True)
