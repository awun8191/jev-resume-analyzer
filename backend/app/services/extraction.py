import asyncio
import json
import os
import sys

from fastapi import UploadFile

from app.config import ROOT, Settings
from app.errors import AppError

SIGNATURES = {".pdf": b"%PDF-", ".docx": b"PK\x03\x04"}


async def read_bounded(upload: UploadFile, limit: int) -> bytes:
    chunks, size = [], 0
    while chunk := await upload.read(512 * 1024):
        size += len(chunk)
        if size > limit:
            raise AppError(413, "FILE_TOO_LARGE", "File exceeds the upload limit of 10 MiB.")
        chunks.append(chunk)
    return b"".join(chunks)


def detect_format(filename: str, data: bytes) -> str:
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in SIGNATURES or not data.startswith(SIGNATURES[extension]):
        raise AppError(415, "UNSUPPORTED_FORMAT", "Upload a PDF or DOCX with matching content.")
    return extension.lstrip(".")


async def extract_document(data: bytes, filename: str, settings: Settings) -> dict:
    kind = detect_format(filename, data)
    params = (
        {"max_pages": settings.max_document_pages}
        if kind == "pdf"
        else {"max_uncompressed_bytes": settings.max_docx_uncompressed_bytes}
    )
    params["max_chars"] = settings.max_extracted_chars
    # No inherited API secrets, shell, applicant paths or persistent upload files.
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "app.parsers.worker",
        kind,
        json.dumps(params),
        cwd=ROOT,
        env={"PATH": os.defpath},
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        stdout, _ = await asyncio.wait_for(
            process.communicate(data), timeout=settings.parser_timeout_seconds
        )
    except TimeoutError:
        raise AppError(
            422,
            "PARSER_TIMEOUT",
            "Document processing timed out. Export a simpler text-based file.",
        ) from None
    finally:
        if process.returncode is None:
            process.kill()
        await process.wait()
    if process.returncode != 0:
        raise AppError(
            422, "UNREADABLE_DOCUMENT", "Document exceeded processing resources or is unreadable."
        )
    output = json.loads(stdout)
    if "result" not in output:
        raise AppError(
            output["status"],
            "DOCUMENT_LIMIT" if output["status"] == 413 else "UNREADABLE_DOCUMENT",
            output["message"],
        )
    return {**output["result"], "source_format": kind}
