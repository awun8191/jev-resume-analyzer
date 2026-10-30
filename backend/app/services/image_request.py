"""Build a TypeSafe System One request that carries PDF page images.

Spike only. The production gateway keeps its text-only JSON path and its 100,000 byte
cap; an image request needs a separate 32 MiB body budget. See
docs/research/image-structure.md for the verified request shape.

Documented rules enforced here, from https://docs.typesafe.ai/images:

- Images live in a top-level `assets` map keyed by a reference string.
- Every asset must be referenced somewhere in `state`, `instructions` or `criteria`.
- The `TypeSafe-Danger-Zone-Images: true` header is required for images and Box.
- Multipart is recommended. The JSON body is the first part, named `request`.
- Part names are unique. `request` is reserved.
- 32 MiB for the request body and 32 MiB for all images together.
- A reference is at most 1,024 bytes, and all references at most 65,536 bytes.
"""

import base64
import json
import uuid
from dataclasses import dataclass

from app.models.image_answers import ImageResponse
from app.services.page_render import PageImage, image_limit_problems

DANGER_ZONE_IMAGES_HEADER = "TypeSafe-Danger-Zone-Images"
REQUEST_PART_NAME = "request"
MAX_REQUEST_BYTES = 32 * 1024 * 1024
MAX_TOTAL_IMAGE_BYTES = 32 * 1024 * 1024
MAX_REFERENCE_BYTES = 1024
MAX_TOTAL_REFERENCE_BYTES = 65_536
MAX_PAGES = 3
MULTIPART = "multipart"
BASE64 = "base64"
CONTENT_TYPES = {"png": "image/png", "jpg": "image/jpeg"}
QUESTION_TYPES = {"box", "noul", "choice", "score"}


class RequestBuildError(ValueError):
    """The request would break a documented provider rule."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ImageAsset:
    reference: str
    part_name: str
    content_type: str
    data: bytes


@dataclass(frozen=True)
class BuiltImageRequest:
    body: dict
    assets: tuple[ImageAsset, ...]
    headers: dict
    transport: str
    reference_uses: dict[str, int]

    def json_bytes(self) -> bytes:
        return json.dumps(self.body, ensure_ascii=False).encode("utf-8")

    def multipart(self, boundary: str) -> tuple[bytes, str]:
        """Encode the documented multipart form. The JSON body is the first part."""
        if not boundary or '"' in boundary or "\r" in boundary or "\n" in boundary:
            raise RequestBuildError("BAD_BOUNDARY", "Boundary must be a plain token.")
        head = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{REQUEST_PART_NAME}"\r\n'
            "Content-Type: application/json\r\n\r\n"
        ).encode()
        chunks = [head, self.json_bytes(), b"\r\n"]
        for asset in self.assets:
            chunks.append(
                (
                    f"--{boundary}\r\n"
                    f'Content-Disposition: form-data; name="{asset.part_name}"; '
                    f'filename="{asset.part_name}.png"\r\n'
                    f"Content-Type: {asset.content_type}\r\n\r\n"
                ).encode()
            )
            chunks.append(asset.data)
            chunks.append(b"\r\n")
        chunks.append(f"--{boundary}--\r\n".encode())
        return b"".join(chunks), f"multipart/form-data; boundary={boundary}"

    def http_kwargs(self, boundary: str) -> dict:
        """Arguments for httpx: content, headers and the documented opt-in header."""
        if self.transport == MULTIPART:
            content, content_type = self.multipart(boundary)
        else:
            content, content_type = self.json_bytes(), "application/json"
        headers = dict(self.headers)
        headers["Content-Type"] = content_type
        return {"content": content, "headers": headers}

    def describe(self) -> dict:
        """Redacted request for logs and evidence files. Contains no image bytes."""
        body = json.loads(json.dumps(self.body))
        for entry in (body.get("assets") or {}).values():
            if "data_base64" in entry:
                entry["data_base64"] = f"<{len(entry['data_base64'])} base64 chars>"
        return {
            "transport": self.transport,
            "headers": {k: v for k, v in self.headers.items() if k == DANGER_ZONE_IMAGES_HEADER},
            "body": body,
            "assets": [
                {
                    "reference": asset.reference,
                    "part": asset.part_name,
                    "content_type": asset.content_type,
                    "bytes": len(asset.data),
                }
                for asset in self.assets
            ],
            "reference_uses": self.reference_uses,
            "json_bytes": len(self.json_bytes()),
            "total_image_bytes": sum(len(asset.data) for asset in self.assets),
        }


def page_key(page_number: int) -> str:
    """State key for one page image."""
    return f"p{page_number}"


def page_path(page_number: int) -> str:
    """State path for one page image, ready to paste into instructions."""
    return f"`pages.{page_key(page_number)}`"


def _default_references(count: int) -> list[str]:
    # The provider matches references as plain text, so short keys can collide with
    # ordinary words. A fresh UUID per image per request avoids that.
    return [str(uuid.uuid4()) for _ in range(count)]


def _check_pages(pages: list[PageImage], max_pages: int) -> list[PageImage]:
    if not pages:
        raise RequestBuildError("NO_PAGES", "Send at least one page image.")
    if len(pages) > max_pages:
        raise RequestBuildError("PAGE_BUDGET", f"At most {max_pages} pages per request.")
    numbers = [page.page_number for page in pages]
    if len(set(numbers)) != len(numbers):
        raise RequestBuildError("DUPLICATE_PAGE", "Each page may appear once.")
    for page in pages:
        problems = image_limit_problems(page.width_px, page.height_px, page.size_bytes)
        if problems:
            raise RequestBuildError("IMAGE_LIMIT", f"Page {page.page_number}: {problems}")
    total = sum(page.size_bytes for page in pages)
    if total > MAX_TOTAL_IMAGE_BYTES:
        raise RequestBuildError("IMAGE_TOTAL_LIMIT", "Images exceed 32 MiB together.")
    return pages


def _check_questions(questions: dict, references: list[str], paths: list[str]) -> None:
    if not questions:
        raise RequestBuildError("NO_QUESTIONS", "Send at least one question.")
    for key, question in questions.items():
        if not isinstance(question, dict) or "type" not in question:
            raise RequestBuildError("BAD_QUESTION", f"Question {key} has no type.")
        if question["type"] not in QUESTION_TYPES:
            raise RequestBuildError("BAD_QUESTION", f"Question {key} has an unknown type.")
        if question["type"] == "box":
            if "criteria" in question:
                raise RequestBuildError("BOX_CRITERIA", f"Box question {key} takes no criteria.")
            instructions = question.get("instructions")
            if not isinstance(instructions, str) or not instructions.strip():
                raise RequestBuildError("BOX_INSTRUCTIONS", f"Box question {key} is empty.")
            # A Box question must name its image, either by reference or by the
            # state path that holds it, as the Box documentation requires.
            if not any(
                marker in instructions for marker in [*references, *paths]
            ):
                raise RequestBuildError(
                    "BOX_NO_IMAGE", f"Box question {key} does not name an image."
                )
        elif not isinstance(question.get("instructions"), str):
            raise RequestBuildError("BAD_QUESTION", f"Question {key} has no instructions.")


def _reference_uses(body: dict, references: list[str]) -> dict[str, int]:
    # Object keys are never replaced, so the assets map itself does not count as a
    # use. Only state, instructions and criteria do.
    text = json.dumps(
        {"state": body["state"], "questions": body["questions"]}, ensure_ascii=False
    )
    return {reference: text.count(reference) for reference in references}


def build_image_request(
    pages: list[PageImage],
    questions: dict,
    *,
    document_note: str,
    model: str,
    transport: str = MULTIPART,
    references: list[str] | None = None,
    max_pages: int = MAX_PAGES,
) -> BuiltImageRequest:
    """Assemble the body, assets and headers for one image request."""
    _check_pages(pages, max_pages)
    if transport not in (MULTIPART, BASE64):
        raise RequestBuildError("BAD_TRANSPORT", "Use multipart or base64.")
    refs = references or _default_references(len(pages))
    if len(refs) != len(pages):
        raise RequestBuildError("REFERENCE_COUNT", "One reference per page image is required.")
    for reference in refs:
        if not reference or not reference.strip():
            raise RequestBuildError("BAD_REFERENCE", "A reference cannot be empty.")
        if len(reference.encode("utf-8")) > MAX_REFERENCE_BYTES:
            raise RequestBuildError("BAD_REFERENCE", "A reference exceeds 1,024 bytes.")
    if sum(len(reference.encode("utf-8")) for reference in refs) > MAX_TOTAL_REFERENCE_BYTES:
        raise RequestBuildError("BAD_REFERENCE", "References exceed 65,536 bytes together.")
    if len(set(refs)) != len(refs):
        raise RequestBuildError("DUPLICATE_REFERENCE", "References must be unique.")

    assets, entries, parts = [], {}, set()
    for page, reference in zip(pages, refs, strict=True):
        part_name = f"page-{page.page_number}"
        if part_name in parts or part_name == REQUEST_PART_NAME:
            raise RequestBuildError("DUPLICATE_PART", f"Part {part_name} is not unique.")
        parts.add(part_name)
        assets.append(ImageAsset(reference, part_name, CONTENT_TYPES["png"], page.data))
        if transport == MULTIPART:
            entries[reference] = {"type": "image", "part": part_name}
        else:
            entries[reference] = {
                "type": "image",
                "format": "png",
                "data_base64": base64.b64encode(page.data).decode("ascii"),
            }

    body = {
        "model": model,
        "state": {
            "document": document_note,
            "page_count": len(pages),
            "pages": {
                page_key(page.page_number): reference
                for page, reference in zip(pages, refs, strict=True)
            },
        },
        "assets": entries,
        "questions": questions,
    }
    paths = [page_path(page.page_number) for page in pages]
    _check_questions(questions, refs, paths)
    uses = _reference_uses(body, refs)
    missing = [reference for reference, count in uses.items() if count == 0]
    if missing:
        raise RequestBuildError("UNREFERENCED_ASSET", "Every asset must be referenced.")
    if transport == MULTIPART:
        request_size = len(json.dumps(body, ensure_ascii=False).encode("utf-8")) + sum(
            len(asset.data) for asset in assets
        )
    else:
        request_size = len(json.dumps(body, ensure_ascii=False).encode("utf-8"))
    if request_size > MAX_REQUEST_BYTES:
        raise RequestBuildError("REQUEST_LIMIT", "Request body exceeds 32 MiB.")
    return BuiltImageRequest(
        body=body,
        assets=tuple(assets),
        headers={DANGER_ZONE_IMAGES_HEADER: "true"},
        transport=transport,
        reference_uses=uses,
    )


def parse_image_response(payload: dict, expected: set[str]) -> ImageResponse:
    """Validate an answer set. A partial or unknown answer set is a failure."""
    result = ImageResponse.model_validate(payload)
    if set(result.answers) != set(expected):
        raise RequestBuildError("ANSWER_SET", "Answer ids do not match the question ids.")
    return result
