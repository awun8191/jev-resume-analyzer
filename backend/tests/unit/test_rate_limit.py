"""The counters, the policy table and the hashed keys behind the limiter."""

import asyncio
import json

import httpx
import pytest
from starlette.datastructures import Headers

from app.config import Settings
from app.services.rate_limit import (
    ANALYSES_SCOPE,
    EXTRACTS_SCOPE,
    GLOBAL_ANALYSES_KEY,
    REQUESTS_SCOPE,
    MemoryCounter,
    RateLimiter,
    RateLimitStoreError,
    UpstashCounter,
    build_limiter,
    resolve_client_ip,
)

SETTINGS = Settings(_env_file=None, rate_limit_enabled=True, rate_limit_salt="synthetic-salt")


class RecordingCounter:
    def __init__(self, count=1, ttl=120):
        self.count, self.ttl, self.calls = count, ttl, []

    async def incr(self, key, window_seconds):
        self.calls.append((key, window_seconds))
        return self.count, self.ttl


class BrokenCounter:
    def __init__(self):
        self.calls = 0

    async def incr(self, key, window_seconds):
        self.calls += 1
        raise RuntimeError("synthetic store outage")


def upstash(handler):
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://redis.example"
    )
    return UpstashCounter("https://redis.example", "synthetic-token", client=client)


def test_the_pipeline_is_one_call_with_incr_expire_and_ttl():
    seen = {}

    def handle(request):
        seen["method"] = request.method
        seen["path"] = request.url.path
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=[{"result": 1}, {"result": 1}, {"result": 3599}])

    count, ttl = asyncio.run(upstash(handle).incr("rl:analyses:abc", 3600))

    assert (count, ttl) == (1, 3599)
    assert seen["method"] == "POST"
    assert seen["path"] == "/pipeline"
    assert seen["auth"] == "Bearer synthetic-token"
    assert seen["body"] == [
        ["INCR", "rl:analyses:abc"],
        ["EXPIRE", "rl:analyses:abc", 3600, "NX"],
        ["TTL", "rl:analyses:abc"],
    ]


def test_a_missing_ttl_falls_back_to_the_window():
    def handle(request):
        return httpx.Response(200, json=[{"result": 2}, {"result": 0}, {"result": -1}])

    assert asyncio.run(upstash(handle).incr("rl:requests:abc", 60)) == (2, 60)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, json={"error": "synthetic"}),
        httpx.Response(200, json=[{"error": "WRONGTYPE"}]),
        httpx.Response(200, json=[{"result": 1}]),
    ],
)
def test_an_unusable_pipeline_answer_is_a_store_error(response):
    def handle(request):
        return response

    with pytest.raises(RateLimitStoreError):
        asyncio.run(upstash(handle).incr("rl:analyses:abc", 3600))


def test_the_memory_counter_counts_within_the_window_and_resets_after_it():
    now = [1000.0]
    counter = MemoryCounter(clock=lambda: now[0])

    async def scenario():
        first = await counter.incr("rl:analyses:abc", 60)
        now[0] += 30
        second = await counter.incr("rl:analyses:abc", 60)
        now[0] += 61
        return first, second, await counter.incr("rl:analyses:abc", 60)

    assert asyncio.run(scenario()) == ((1, 60), (2, 30), (1, 60))


def test_memory_keys_are_separate():
    counter = MemoryCounter()

    async def scenario():
        await counter.incr("rl:analyses:one", 60)
        return await counter.incr("rl:analyses:two", 60)

    assert asyncio.run(scenario()) == (1, 60)


def test_the_key_is_a_salted_hash_that_never_contains_the_ip():
    limiter = RateLimiter(SETTINGS)
    key = limiter.key_for(ANALYSES_SCOPE, "198.51.100.7")

    assert key.startswith("rl:analyses:")
    assert "198.51.100.7" not in key
    assert len(key.rsplit(":", 1)[1]) == 64
    assert key == limiter.key_for(ANALYSES_SCOPE, "198.51.100.7")
    assert key != limiter.key_for(ANALYSES_SCOPE, "198.51.100.8")


def test_a_different_salt_produces_a_different_key():
    other = Settings(_env_file=None, rate_limit_enabled=True, rate_limit_salt="other-salt")
    assert (
        RateLimiter(SETTINGS).key_for(ANALYSES_SCOPE, "198.51.100.7")
        != RateLimiter(other).key_for(ANALYSES_SCOPE, "198.51.100.7")
    )


@pytest.mark.parametrize(
    "method,path,scope,limit,window",
    [
        ("POST", "/api/v1/analyses", ANALYSES_SCOPE, 10, 3600),
        ("POST", "/api/v1/documents/extract", EXTRACTS_SCOPE, 30, 3600),
        ("GET", "/api/v1/anything", REQUESTS_SCOPE, 120, 60),
        ("POST", "/api/v1/analyses/", ANALYSES_SCOPE, 10, 3600),
    ],
)
def test_the_policy_table(method, path, scope, limit, window):
    policy = RateLimiter(SETTINGS).policy_for(method, path)
    assert (policy.name, policy.limit, policy.window_seconds) == (scope, limit, window)


@pytest.mark.parametrize("path", ["/api/v1/health", "/health"])
def test_health_endpoints_are_exempt(path):
    assert RateLimiter(SETTINGS).policy_for("GET", path) is None


def test_options_is_exempt():
    assert RateLimiter(SETTINGS).policy_for("OPTIONS", "/api/v1/analyses") is None


def test_a_disabled_limiter_never_touches_the_store():
    settings = Settings(_env_file=None, rate_limit_enabled=False)
    counter = BrokenCounter()
    limiter = RateLimiter(settings, counter)

    async def scenario():
        return await limiter.check(
            method="POST",
            path="/api/v1/analyses",
            headers=Headers({"x-real-ip": "198.51.100.7"}),
        )

    assert asyncio.run(scenario()) is None
    assert counter.calls == 0


@pytest.mark.parametrize(
    "headers,client,expected",
    [
        (
            {"x-real-ip": "203.0.113.9", "x-forwarded-for": "10.0.0.1"},
            ("10.0.0.2", 1),
            "203.0.113.9",
        ),
        ({"x-forwarded-for": "10.0.0.1, 10.0.0.2"}, ("10.0.0.3", 1), "10.0.0.2"),
        ({"x-forwarded-for": "10.0.0.1, , 10.0.0.2"}, ("10.0.0.3", 1), "10.0.0.2"),
        ({}, ("10.0.0.3", 1), "10.0.0.3"),
        ({}, None, "unknown"),
    ],
)
def test_the_client_ip_source_order(headers, client, expected):
    assert resolve_client_ip(Headers(headers), client) == expected


def test_the_global_analyses_budget_is_a_separate_key():
    counter = RecordingCounter()
    limiter = RateLimiter(SETTINGS, counter)

    async def scenario():
        return await limiter.check(
            method="POST",
            path="/api/v1/analyses",
            headers=Headers({"x-real-ip": "198.51.100.7"}),
        )

    decision = asyncio.run(scenario())
    assert decision.allowed is True
    assert [key for key, _ in counter.calls] == [
        limiter.key_for(ANALYSES_SCOPE, "198.51.100.7"),
        GLOBAL_ANALYSES_KEY,
    ]
    assert [window for _, window in counter.calls] == [3600, 86400]


def test_build_limiter_uses_memory_when_upstash_is_not_configured():
    limiter = build_limiter(Settings(_env_file=None, rate_limit_enabled=True))
    assert limiter._store is None


def test_build_limiter_uses_upstash_when_configured():
    settings = Settings(
        _env_file=None,
        rate_limit_enabled=True,
        upstash_redis_rest_url="https://redis.example",
        upstash_redis_rest_token="synthetic-token",
    )
    limiter = build_limiter(settings)
    assert isinstance(limiter._store, UpstashCounter)
    asyncio.run(limiter.aclose())


def test_a_url_without_a_token_is_rejected():
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            upstash_redis_rest_url="https://redis.example",
            upstash_redis_rest_token="",
        )
