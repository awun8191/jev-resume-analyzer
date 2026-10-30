"""The limiter as the middleware sees it: headers, 429s and fallbacks."""

import asyncio
import json
import logging
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.datastructures import Headers

from app.config import Settings
from app.middleware import RateLimitMiddleware
from app.services.rate_limit import MemoryCounter, RateLimiter

IP = "198.51.100.7"


class BrokenCounter:
    def __init__(self):
        self.calls = 0

    async def incr(self, key, window_seconds):
        self.calls += 1
        raise RuntimeError("synthetic store outage")


def build_app(limiter):
    app = FastAPI()
    app.state.rate_limiter = limiter
    app.add_middleware(RateLimitMiddleware)

    @app.post("/api/v1/analyses")
    async def analyses():
        return {"scored": True}

    @app.post("/api/v1/documents/extract")
    async def extract():
        return {"extracted": True}

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok"}

    @app.get("/api/v1/other")
    async def other():
        return {"ok": True}

    return app


def limiter_for(**overrides) -> RateLimiter:
    settings = Settings(
        _env_file=None, rate_limit_enabled=True, rate_limit_salt="test-salt", **overrides
    )
    return RateLimiter(settings, MemoryCounter())


def client_for(limiter) -> TestClient:
    return TestClient(build_app(limiter))


def test_the_boundary_allows_then_denies():
    client = client_for(limiter_for(rate_limit_analyses_per_hour=2))
    headers = {"x-real-ip": IP}

    first = client.post("/api/v1/analyses", headers=headers)
    second = client.post("/api/v1/analyses", headers=headers)
    third = client.post("/api/v1/analyses", headers=headers)

    assert [r.status_code for r in (first, second, third)] == [200, 200, 429]
    assert first.headers["RateLimit-Limit"] == "2"
    assert first.headers["RateLimit-Remaining"] == "1"
    assert second.headers["RateLimit-Remaining"] == "0"
    assert int(third.headers["Retry-After"]) >= 1
    assert third.headers["RateLimit-Limit"] == "2"
    assert third.headers["RateLimit-Remaining"] == "0"
    assert int(third.headers["RateLimit-Reset"]) >= 1


def test_an_allowed_response_carries_the_reset_hint():
    client = client_for(limiter_for(rate_limit_extracts_per_hour=5))

    response = client.post("/api/v1/documents/extract", headers={"x-real-ip": IP})

    assert response.status_code == 200
    assert response.headers["RateLimit-Limit"] == "5"
    assert response.headers["RateLimit-Remaining"] == "4"
    assert 1 <= int(response.headers["RateLimit-Reset"]) <= 3600


def test_the_429_body_matches_the_error_envelope():
    client = client_for(limiter_for(rate_limit_analyses_per_hour=1))
    client.post("/api/v1/analyses", headers={"x-real-ip": IP})

    response = client.post("/api/v1/analyses", headers={"x-real-ip": IP})
    body = response.json()

    assert response.status_code == 429
    assert body["error"] == {
        "code": "RATE_LIMITED",
        "message": "Too many requests. Try again later.",
        "retryable": True,
    }
    assert isinstance(body["request_id"], str) and body["request_id"]


def test_the_two_post_policies_do_not_share_a_counter():
    client = client_for(
        limiter_for(rate_limit_analyses_per_hour=1, rate_limit_extracts_per_hour=1)
    )
    headers = {"x-real-ip": IP}

    assert client.post("/api/v1/analyses", headers=headers).status_code == 200
    assert client.post("/api/v1/documents/extract", headers=headers).status_code == 200
    assert client.post("/api/v1/analyses", headers=headers).status_code == 429
    assert client.post("/api/v1/documents/extract", headers=headers).status_code == 429


def test_other_routes_use_the_minute_policy():
    client = client_for(limiter_for(rate_limit_requests_per_minute=2))

    responses = [client.get("/api/v1/other", headers={"x-real-ip": IP}) for _ in range(3)]

    assert [r.status_code for r in responses] == [200, 200, 429]
    assert responses[-1].headers["RateLimit-Limit"] == "2"


def test_the_daily_analyses_cap_is_global_across_ips():
    client = client_for(
        limiter_for(rate_limit_analyses_per_hour=100, rate_limit_global_analyses_per_day=3)
    )

    responses = [
        client.post("/api/v1/analyses", headers={"x-real-ip": f"203.0.113.{number}"})
        for number in range(1, 5)
    ]

    assert [r.status_code for r in responses] == [200, 200, 200, 429]
    assert responses[-1].headers["RateLimit-Limit"] == "3"
    assert int(responses[-1].headers["Retry-After"]) >= 1


def test_health_is_exempt_and_gets_no_limit_headers():
    client = client_for(limiter_for(rate_limit_requests_per_minute=1))

    responses = [client.get("/api/v1/health") for _ in range(3)]

    assert [r.status_code for r in responses] == [200, 200, 200]
    assert all("RateLimit-Limit" not in r.headers for r in responses)


def test_options_is_exempt():
    client = client_for(limiter_for(rate_limit_analyses_per_hour=1))

    responses = [client.options("/api/v1/analyses") for _ in range(3)]

    assert all(r.status_code != 429 for r in responses)
    assert all("RateLimit-Limit" not in r.headers for r in responses)


def test_a_spoofed_forwarded_for_is_ignored_when_real_ip_is_present():
    client = client_for(limiter_for(rate_limit_analyses_per_hour=1))

    first = client.post(
        "/api/v1/analyses",
        headers={"x-real-ip": IP, "x-forwarded-for": "10.0.0.1"},
    )
    second = client.post(
        "/api/v1/analyses",
        headers={"x-real-ip": IP, "x-forwarded-for": "10.0.0.2"},
    )

    assert (first.status_code, second.status_code) == (200, 429)


def test_the_last_forwarded_for_entry_is_the_client():
    client = client_for(limiter_for(rate_limit_analyses_per_hour=1))

    first = client.post("/api/v1/analyses", headers={"x-forwarded-for": "10.0.0.1, 10.0.0.2"})
    same_client = client.post(
        "/api/v1/analyses", headers={"x-forwarded-for": "10.0.0.3, 10.0.0.2"}
    )
    other_client = client.post(
        "/api/v1/analyses", headers={"x-forwarded-for": "10.0.0.1, 10.0.0.4"}
    )

    assert (first.status_code, same_client.status_code) == (200, 429)
    assert other_client.status_code == 200


def test_a_store_failure_falls_back_to_memory_and_says_so(caplog):
    settings = Settings(
        _env_file=None, rate_limit_enabled=True, rate_limit_analyses_per_hour=1
    )
    limiter = RateLimiter(settings, BrokenCounter())
    client = client_for(limiter)
    headers = {"x-real-ip": IP}

    with caplog.at_level(logging.WARNING, logger="app.services.rate_limit"):
        first = client.post("/api/v1/analyses", headers=headers)
        second = client.post("/api/v1/analyses", headers=headers)
        third = client.post("/api/v1/analyses", headers=headers)

    assert (first.status_code, second.status_code) == (200, 429)
    assert first.headers["X-RateLimit-Degraded"] == "1"
    assert second.headers["X-RateLimit-Degraded"] == "1"
    assert second.headers["Retry-After"] == "3600"
    assert third.status_code == 429
    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 1


def test_disabled_mode_passes_everything_through_without_headers():
    settings = Settings(_env_file=None, rate_limit_enabled=False)
    counter = BrokenCounter()
    limiter = RateLimiter(settings, counter)
    client = client_for(limiter)

    responses = [client.post("/api/v1/analyses", headers={"x-real-ip": IP}) for _ in range(3)]

    assert [r.status_code for r in responses] == [200, 200, 200]
    assert all("RateLimit-Limit" not in r.headers for r in responses)
    assert counter.calls == 0


def test_a_denied_request_never_reaches_the_body():
    settings = Settings(_env_file=None, rate_limit_enabled=True, rate_limit_analyses_per_hour=1)
    limiter = RateLimiter(settings, MemoryCounter())

    async def scenario():
        await limiter.check(
            method="POST",
            path="/api/v1/analyses",
            headers=Headers({"x-real-ip": IP}),
            client=("10.0.0.1", 1234),
        )
        seen = []

        async def inner(scope, receive, send):
            seen.append("app")

        async def receive():
            seen.append("body")
            return {"type": "http.request", "body": b"", "more_body": False}

        sent = []

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/analyses",
            "headers": [(b"x-real-ip", IP.encode())],
            "client": ("10.0.0.1", 1234),
            "app": SimpleNamespace(state=SimpleNamespace(rate_limiter=limiter)),
        }
        await RateLimitMiddleware(inner)(scope, receive, send)
        return sent, seen

    sent, seen = asyncio.run(scenario())
    assert sent[0]["status"] == 429
    assert "retry-after" in {key.decode() for key, _ in sent[0]["headers"]}
    assert seen == []


def test_the_counter_only_sees_hashed_keys():
    from app.services.rate_limit import ANALYSES_SCOPE

    recording = []
    settings = Settings(
        _env_file=None,
        rate_limit_enabled=True,
        rate_limit_analyses_per_hour=5,
        rate_limit_salt="test-salt",
    )

    class Recorder:
        async def incr(self, key, window_seconds):
            recording.append(key)
            return 1, 60

    limiter = RateLimiter(settings, Recorder())
    client = client_for(limiter)

    client.post("/api/v1/analyses", headers={"x-real-ip": IP})

    assert recording[0] == limiter.key_for(ANALYSES_SCOPE, IP)
    assert IP not in recording[0]
    assert len(recording[0].rsplit(":", 1)[1]) == 64


def test_the_response_body_survives_the_header_injection():
    client = client_for(limiter_for())

    response = client.post("/api/v1/analyses", headers={"x-real-ip": IP})

    assert json.loads(response.text) == {"scored": True}


def test_an_exempt_request_never_touches_the_counter():
    recording = []

    class Recorder:
        async def incr(self, key, window_seconds):
            recording.append(key)
            return 1, 60

    settings = Settings(_env_file=None, rate_limit_enabled=True, rate_limit_requests_per_minute=1)
    client = client_for(RateLimiter(settings, Recorder()))

    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/health").status_code == 200
    assert recording == []
