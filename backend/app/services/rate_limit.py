"""Shared counters and per-IP rate limiting for the public API.

The service is deliberately small: a Counter increments a fixed window key and
reports the remaining TTL, while RateLimiter maps a request to a policy and
turns the counter result into an allow or deny decision.

Raw client IPs are never stored. Every key carries an HMAC-SHA256 digest of the
IP salted with ``RATE_LIMIT_SALT``.
"""

import asyncio
import hashlib
import hmac
import logging
import math
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

# Used only when RATE_LIMIT_SALT is unset. It is public, so operators must set
# a private salt if stored digests should resist offline guessing.
DEFAULT_SALT = "jev-resume-analyzer"

# The longest window any policy uses. Memory keys idle past this are dropped.
MAX_WINDOW_SECONDS = 86400

ANALYSES_SCOPE = "analyses"
EXTRACTS_SCOPE = "extracts"
REQUESTS_SCOPE = "requests"
GLOBAL_ANALYSES_KEY = "rl:global:analyses:day"

ANALYSES_PATH = "/api/v1/analyses"
EXTRACT_PATH = "/api/v1/documents/extract"
HEALTH_PATHS = frozenset({"/health", "/api/v1/health"})

_warned_memory_mode = False


class RateLimitStoreError(RuntimeError):
    """The shared counter store answered with something unusable."""


@runtime_checkable
class Counter(Protocol):
    async def incr(self, key: str, window_seconds: int) -> tuple[int, int]:
        """Increment key for the window and return (count, ttl_seconds)."""


class MemoryCounter:
    """Per-process fixed window counter. Correct for one instance only."""

    def __init__(self, clock: Callable[[], float] = time.monotonic, max_keys: int = 1024):
        self._clock = clock
        self._max_keys = max_keys
        self._hits: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def incr(self, key: str, window_seconds: int) -> tuple[int, int]:
        now = self._clock()
        cutoff = now - window_seconds
        async with self._lock:
            hits = [stamp for stamp in self._hits.get(key, ()) if stamp > cutoff]
            hits.append(now)
            self._hits[key] = hits
            if len(self._hits) > self._max_keys:
                self._prune(now - MAX_WINDOW_SECONDS)
            reset = int(math.ceil(hits[0] + window_seconds - now))
            return len(hits), max(reset, 1)

    def _prune(self, cutoff: float) -> None:
        stale = [key for key, hits in self._hits.items() if not hits or hits[-1] <= cutoff]
        for key in stale:
            del self._hits[key]


class UpstashCounter:
    """Fixed window counter in Upstash Redis over the REST pipeline API."""

    def __init__(
        self,
        url: str,
        token: str,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 2.0,
    ):
        self._token = token
        self._client = client or httpx.AsyncClient(
            base_url=url.rstrip("/"),
            timeout=timeout,
            follow_redirects=False,
        )

    async def incr(self, key: str, window_seconds: int) -> tuple[int, int]:
        # One round trip: increment, set the window once, then read the TTL.
        commands = [
            ["INCR", key],
            ["EXPIRE", key, window_seconds, "NX"],
            ["TTL", key],
        ]
        try:
            response = await self._client.post(
                "/pipeline",
                json=commands,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.HTTPError as exc:
            raise RateLimitStoreError("Upstash request failed.") from exc
        if response.status_code >= 400:
            raise RateLimitStoreError(f"Upstash returned status {response.status_code}.")
        try:
            results = [entry["result"] for entry in response.json()]
        except (TypeError, KeyError, ValueError) as exc:
            raise RateLimitStoreError("Upstash returned an unexpected pipeline payload.") from exc
        if len(results) != len(commands):
            raise RateLimitStoreError("Upstash returned an unexpected pipeline length.")
        count = int(results[0])
        ttl = int(results[2])
        return count, ttl if ttl > 0 else window_seconds

    async def aclose(self) -> None:
        await self._client.aclose()


@dataclass(frozen=True)
class Policy:
    name: str
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class Decision:
    allowed: bool
    limit: int
    remaining: int
    reset_seconds: int
    degraded: bool = False


def resolve_client_ip(headers: Mapping[str, str], client: tuple | None) -> str:
    """Vercel sets x-real-ip and overwrites x-forwarded-for. Trust it first."""
    real = (headers.get("x-real-ip") or "").strip()
    if real:
        return real
    forwarded = headers.get("x-forwarded-for") or ""
    for entry in reversed(forwarded.split(",")):
        value = entry.strip()
        if value:
            return value
    if client:
        return str(client[0])
    return "unknown"


class RateLimiter:
    """Decide one request against the per-IP policy and the global budget."""

    def __init__(self, settings: Settings, counter: Counter | None = None):
        self._settings = settings
        self._store = counter
        self._memory = MemoryCounter()
        self._salt = (settings.rate_limit_salt or DEFAULT_SALT).encode("utf-8")
        self._degraded_logged = False

    @property
    def enabled(self) -> bool:
        return self._settings.rate_limit_enabled

    def policy_for(self, method: str, path: str) -> Policy | None:
        if method == "OPTIONS":
            return None
        normalized = path.rstrip("/") or "/"
        if normalized in HEALTH_PATHS:
            return None
        if method == "POST" and normalized == ANALYSES_PATH:
            return Policy(ANALYSES_SCOPE, self._settings.rate_limit_analyses_per_hour, 3600)
        if method == "POST" and normalized == EXTRACT_PATH:
            return Policy(EXTRACTS_SCOPE, self._settings.rate_limit_extracts_per_hour, 3600)
        return Policy(REQUESTS_SCOPE, self._settings.rate_limit_requests_per_minute, 60)

    def key_for(self, scope: str, ip: str) -> str:
        digest = hmac.new(self._salt, ip.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"rl:{scope}:{digest}"

    async def check(
        self,
        *,
        method: str,
        path: str,
        headers: Mapping[str, str],
        client: tuple | None = None,
    ) -> Decision | None:
        """Return a Decision, or None when the request is exempt."""
        if not self.enabled:
            return None
        policy = self.policy_for(method, path)
        if policy is None:
            return None
        ip = resolve_client_ip(headers, client)
        count, reset, degraded = await self._incr(
            self.key_for(policy.name, ip), policy.window_seconds
        )
        if count > policy.limit:
            return Decision(False, policy.limit, 0, reset, degraded)
        if policy.name == ANALYSES_SCOPE:
            total, global_reset, global_degraded = await self._incr(GLOBAL_ANALYSES_KEY, 86400)
            degraded = degraded or global_degraded
            cap = self._settings.rate_limit_global_analyses_per_day
            if total > cap:
                return Decision(False, cap, 0, global_reset, degraded)
        return Decision(True, policy.limit, policy.limit - count, reset, degraded)

    async def _incr(self, key: str, window_seconds: int) -> tuple[int, int, bool]:
        """Increment through the store, falling back to memory on any store error."""
        if self._store is not None:
            try:
                count, reset = await self._store.incr(key, window_seconds)
                return int(count), int(reset), False
            except Exception:
                if not self._degraded_logged:
                    logger.warning(
                        "Rate limit store unavailable. Falling back to per-instance memory."
                    )
                    self._degraded_logged = True
        count, reset = await self._memory.incr(key, window_seconds)
        return count, reset, self._store is not None

    async def aclose(self) -> None:
        close = getattr(self._store, "aclose", None)
        if close is not None:
            await close()


def build_limiter(settings: Settings) -> RateLimiter:
    """Use Upstash when configured, otherwise a per-instance memory counter."""
    global _warned_memory_mode
    if not settings.rate_limit_enabled:
        return RateLimiter(settings)
    url = settings.upstash_redis_rest_url.strip()
    token = settings.upstash_redis_rest_token.get_secret_value()
    if url and token:
        return RateLimiter(settings, UpstashCounter(url, token))
    if not _warned_memory_mode:
        logger.warning(
            "Upstash is not configured. Rate limits are enforced per instance, "
            "not across instances."
        )
        _warned_memory_mode = True
    return RateLimiter(settings)
