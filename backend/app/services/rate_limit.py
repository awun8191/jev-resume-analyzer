"""Shared counters and per-IP rate limiting for the public API.

The service is deliberately small: a Counter increments a fixed window key and
reports the remaining TTL, while RateLimiter maps a request to a policy and
turns the counter result into an allow or deny decision.

Raw client IPs are never stored. Every key carries an HMAC-SHA256 digest of the
IP salted with ``RATE_LIMIT_SALT``.
"""

import asyncio
import logging
import math
import time
from typing import Callable, Protocol, runtime_checkable

import httpx

logger = logging.getLogger(__name__)

# Used only when RATE_LIMIT_SALT is unset. It is public, so operators must set
# a private salt if stored digests should resist offline guessing.
DEFAULT_SALT = "jev-resume-analyzer"

# The longest window any policy uses. Memory keys idle past this are dropped.
MAX_WINDOW_SECONDS = 86400


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
        self._client = client or httpx.AsyncClient(
            base_url=url.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
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
            response = await self._client.post("/pipeline", json=commands)
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
