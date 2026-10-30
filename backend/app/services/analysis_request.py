"""Read the analysis request in either accepted shape.

Two shapes are supported:

- ``application/json``: the plain ``AnalysisRequest`` body. This is the original
  contract and stays for callers that have text only.
- ``multipart/form-data``: a part named ``request`` holding the same JSON, plus an
  optional part named ``file`` holding the uploaded PDF. The structure route needs
  the bytes; the text route never does.

Parsing happens here rather than in the FastAPI signature so that a multipart body
and a JSON body can share one endpoint and one error envelope.
"""

import json

from fastapi import Request
from pydantic import ValidationError
from starlette.datastructures import UploadFile
from starlette.formparsers import MultiPartException

from app.config import Settings
from app.errors import AppError
from app.models.analyses import AnalysisRequest
from app.services.extraction import read_bounded

REQUEST_PART = "request"
FILE_PART = "file"
INVALID = "INVALID_INPUT"


def _invalid(message: str) -> AppError:
    return AppError(422, INVALID, message)


def parse_json(data: bytes | str) -> AnalysisRequest:
    """Decode and validate one AnalysisRequest. Every failure is a 422 envelope."""
    try:
        raw = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
        raise _invalid("The request part is not valid JSON.") from None
    if not isinstance(raw, dict):
        raise _invalid("The request must be a JSON object.")
    try:
        return AnalysisRequest.model_validate(raw)
    except ValidationError:
        raise _invalid(
            "Check required fields, types and nonblank text. Only review mode is supported."
        ) from None


async def _multipart(request: Request, settings: Settings) -> tuple[AnalysisRequest, bytes | None]:
    # Spooled upload parts are closed when the form context exits, so every part is
    # read inside it.
    try:
        async with request.form(
            max_files=2, max_fields=2, max_part_size=settings.max_upload_bytes
        ) as form:
            entries = list(form.multi_items())
            names = [name for name, _ in entries]
            if len(names) != len(set(names)):
                raise _invalid("Each part may appear once.")
            unknown = set(names) - {REQUEST_PART, FILE_PART}
            if unknown:
                raise _invalid("Only the request and file parts are accepted.")
            parts = dict(entries)
            if REQUEST_PART not in parts:
                raise _invalid("A part named request is required.")
            payload = parts[REQUEST_PART]
            raw = await payload.read() if isinstance(payload, UploadFile) else payload
            body = parse_json(raw)
            upload = parts.get(FILE_PART)
            if upload is None:
                return body, None
            if not isinstance(upload, UploadFile):
                raise _invalid("The file part must be an uploaded file.")
            data = await read_bounded(upload, settings.max_upload_bytes)
            if not data:
                raise _invalid("The uploaded file is empty.")
            return body, data
    except (MultiPartException, RuntimeError):
        raise _invalid("Send one request part and at most one file part.") from None


async def read_analysis(
    request: Request, settings: Settings
) -> tuple[AnalysisRequest, bytes | None]:
    """Return the validated request and the uploaded bytes, if any."""
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith("multipart/form-data"):
        return await _multipart(request, settings)
    try:
        raw = await request.body()
    except Exception:
        raise _invalid("The request body could not be read.") from None
    if not raw:
        raise _invalid("A JSON body or a multipart request part is required.")
    return parse_json(raw), None
