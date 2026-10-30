import asyncio
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request

from app.dependencies import get_settings
from app.errors import AppError, error_response
from app.services.rate_limit import RateLimiter, build_limiter

RATE_LIMITED_MESSAGE = "Too many requests. Try again later."


class RateLimitMiddleware:
    """Refuse an over-limit caller before any request body is read."""

    def __init__(self, app):
        self.app = app

    def limiter(self, scope) -> RateLimiter:
        state = getattr(scope.get("app"), "state", None)
        limiter = getattr(state, "rate_limiter", None)
        if limiter is None:
            limiter = build_limiter(get_settings())
            if state is not None:
                state.rate_limiter = limiter
        return limiter

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        limiter = self.limiter(scope)
        if not limiter.enabled:
            return await self.app(scope, receive, send)
        decision = await limiter.check(
            method=scope["method"],
            path=scope["path"],
            headers=Headers(scope=scope),
            client=scope.get("client"),
        )
        if decision is None:
            return await self.app(scope, receive, send)
        headers = {
            "RateLimit-Limit": str(decision.limit),
            "RateLimit-Remaining": str(max(decision.remaining, 0)),
            "RateLimit-Reset": str(max(decision.reset_seconds, 0)),
        }
        if decision.degraded:
            headers["X-RateLimit-Degraded"] = "1"
        if not decision.allowed:
            headers["Retry-After"] = str(max(decision.reset_seconds, 1))
            response = error_response(
                Request(scope), AppError(429, "RATE_LIMITED", RATE_LIMITED_MESSAGE, True)
            )
            response.headers.update(headers)
            return await response(scope, receive, send)

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                target = MutableHeaders(scope=message)
                for name, value in headers.items():
                    target[name] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)

# Vercel rejects a request body over 4.5 MB before the app runs. Stay under it:
# 4 MB of content plus room for the multipart envelope Starlette has to parse.
MAX_UPLOAD_BYTES = 4000000
MULTIPART_OVERHEAD_BYTES = 65536


class RequestBoundary:
    """Bound body bytes before multipart spooling; admit at most two POSTs per process."""

    def __init__(self, app):
        self.app = app
        self.active = 0

    async def safe_dispatch(self, scope, receive, send):
        started = False

        async def tracked_send(message):
            nonlocal started
            if message['type'] == 'http.response.start':
                started = True
            await send(message)

        try:
            await self.app(scope, receive, tracked_send)
        except Exception:
            # Starlette's generic handler re-raises to the server logger. Intercept
            # before that boundary so exception strings cannot leak private data.
            if not started:
                await error_response(Request(scope), AppError(
                    500, 'INTERNAL_ERROR', 'The request could not be completed.'
                ))(scope, receive, send)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        scope.setdefault("state", {})["request_id"] = str(uuid4())
        request = Request(scope)
        if scope["method"] != "POST":
            return await self.safe_dispatch(scope, receive, send)
        if self.active >= 2:
            response = error_response(
                request, AppError(429, "CAPACITY_LIMIT", "Server busy. Try again later.", True)
            )
            return await response(scope, receive, send)
        self.active += 1
        if scope["path"].endswith(("/documents/extract", "/analyses")):
            limit = MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD_BYTES
        else:
            limit = 512000
        try:
            # Prebuffering is bounded and avoids partial multipart temporary-file leaks.
            body = bytearray()
            async with asyncio.timeout(30):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > limit:
                        raise AppError(413, "REQUEST_TOO_LARGE", "Request exceeds the size limit.")
                    if not message.get("more_body", False):
                        break
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            await self.safe_dispatch(scope, bounded_receive, send)
        except AppError as exc:
            await error_response(request, exc)(scope, receive, send)
        except TimeoutError:
            await error_response(
                request, AppError(408, "UPLOAD_TIMEOUT", "Request upload timed out.")
            )(scope, receive, send)
        finally:
            self.active -= 1
