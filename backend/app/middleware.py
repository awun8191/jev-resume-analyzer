import asyncio
from uuid import uuid4

from starlette.requests import Request

from app.errors import AppError, error_response


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
        limit = 10485760 + 65536 if scope["path"].endswith("/documents/extract") else 512000
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
