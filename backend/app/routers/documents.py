from fastapi import APIRouter, Depends, Request
from starlette.datastructures import UploadFile

from app.config import Settings
from app.dependencies import get_settings
from app.errors import AppError
from app.models.documents import ExtractionResponse
from app.services.extraction import extract_document, read_bounded

router = APIRouter()


@router.post("/documents/extract", response_model=ExtractionResponse)
async def extract(request: Request, settings: Settings = Depends(get_settings)):
    async with request.form(max_files=2, max_fields=2, max_part_size=1024) as form:
        entries = list(form.multi_items())
        if (
            len(entries) != 1
            or entries[0][0] != "file"
            or not isinstance(entries[0][1], UploadFile)
        ):
            raise AppError(422, "INVALID_INPUT", "Provide exactly one file field named file.")
        upload = entries[0][1]
        data = await read_bounded(upload, settings.max_upload_bytes)
        if not data:
            raise AppError(422, "INVALID_INPUT", "The uploaded file is empty.")
        result = await extract_document(data, upload.filename or "", settings)
    return ExtractionResponse(**result)
