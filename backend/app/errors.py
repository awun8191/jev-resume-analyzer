from uuid import uuid4

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False):
        self.status, self.code, self.message, self.retryable = status, code, message, retryable


def error_response(request: Request, error: AppError):
    return JSONResponse(
        status_code=error.status,
        content={
            "error": {"code": error.code, "message": error.message, "retryable": error.retryable},
            "request_id": getattr(request.state, "request_id", str(uuid4())),
        },
    )


def install_handlers(app):
    @app.exception_handler(AppError)
    async def app_error(request, exc):
        return error_response(request, exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Content-type and multipart-shape failures must also respect the envelope.
        return error_response(
            request,
            AppError(
                422,
                "INVALID_INPUT",
                "Check required fields, types and nonblank text. Only review mode is supported.",
            ),
        )

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error_response(
            request, AppError(exc.status_code, "HTTP_ERROR", "The request could not be processed.")
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        return error_response(
            request, AppError(500, "INTERNAL_ERROR", "The request could not be completed.")
        )
