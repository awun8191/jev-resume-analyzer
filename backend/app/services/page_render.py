"""Rasterise one PDF page to a PNG that the TypeSafe image route accepts.

Spike only. No router, service or gateway imports this module. The live analysis
path stays text-only until the design in docs/research/image-structure.md is approved.

The provider limits are copied here from https://docs.typesafe.ai/images so that a
bad image is refused before it reaches the network:

- PNG or JPEG, at most 16 MiB per image.
- Each side from 280 to 1568 pixels.
- Total pixels from 78,400 to 2,458,624.
"""

from dataclasses import dataclass
from io import BytesIO

import pypdfium2 as pdfium
from PIL import Image

MIN_SIDE_PX = 280
MAX_SIDE_PX = 1568
MIN_TOTAL_PX = 78_400
MAX_TOTAL_PX = 2_458_624
MAX_IMAGE_BYTES = 16 * 1024 * 1024
TARGET_SIDE_PX = MAX_SIDE_PX
MAX_RENDER_ATTEMPTS = 3


class RenderError(ValueError):
    """A page could not be rasterised into a provider-acceptable image."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PageImage:
    """One rendered page plus the transform needed to map answers back.

    Fractions in a Box answer are measured against the image actually sent, which
    may be a white canvas larger than the page content. offset_x_px and offset_y_px
    give the top-left corner of the page content inside that canvas.
    """

    page_number: int
    page_width_pt: float
    page_height_pt: float
    scale: float
    content_width_px: int
    content_height_px: int
    width_px: int
    height_px: int
    offset_x_px: int
    offset_y_px: int
    data: bytes

    @property
    def padded(self) -> bool:
        return (self.width_px, self.height_px) != (
            self.content_width_px,
            self.content_height_px,
        )

    @property
    def size_bytes(self) -> int:
        return len(self.data)

    def summary(self) -> dict:
        """Safe diagnostics. Never contains image bytes or page text."""
        return {
            "page": self.page_number,
            "page_size_pt": [round(self.page_width_pt, 2), round(self.page_height_pt, 2)],
            "image_px": [self.width_px, self.height_px],
            "content_px": [self.content_width_px, self.content_height_px],
            "offset_px": [self.offset_x_px, self.offset_y_px],
            "scale_px_per_pt": round(self.scale, 4),
            "padded": self.padded,
            "bytes": self.size_bytes,
        }


def image_limit_problems(width: int, height: int, size_bytes: int) -> list[str]:
    """Return every documented limit the image breaks. Empty list means accepted."""
    problems = []
    if size_bytes > MAX_IMAGE_BYTES:
        problems.append("image exceeds 16 MiB")
    if width < MIN_SIDE_PX or height < MIN_SIDE_PX:
        problems.append(f"a side is under {MIN_SIDE_PX} px")
    if width > MAX_SIDE_PX or height > MAX_SIDE_PX:
        problems.append(f"a side is over {MAX_SIDE_PX} px")
    if not MIN_TOTAL_PX <= width * height <= MAX_TOTAL_PX:
        problems.append("total pixels outside the accepted range")
    return problems


def ensure_image_limits(width: int, height: int, size_bytes: int) -> None:
    problems = image_limit_problems(width, height, size_bytes)
    if problems:
        raise RenderError("IMAGE_LIMIT", "; ".join(problems))


def page_size(data: bytes) -> tuple[float, float]:
    """Width and height of page 1 in points, after rotation."""
    document = _open(data)
    try:
        page = document[0]
        width, height = page.get_size()
    finally:
        document.close()
    if width <= 0 or height <= 0:
        raise RenderError("UNREADABLE_PDF", "Page has no usable area.")
    return float(width), float(height)


def page_count(data: bytes) -> int:
    document = _open(data)
    try:
        return len(document)
    finally:
        document.close()


def _open(data: bytes):
    if not data:
        raise RenderError("UNREADABLE_PDF", "Empty document.")
    try:
        return pdfium.PdfDocument(data)
    except pdfium.PdfiumError as error:
        raise RenderError("UNREADABLE_PDF", "PDF could not be opened.") from error


def _target_side(target_side_px: int) -> int:
    if not MIN_SIDE_PX <= target_side_px <= MAX_SIDE_PX:
        raise RenderError(
            "TARGET_OUT_OF_RANGE",
            f"target_side_px must be between {MIN_SIDE_PX} and {MAX_SIDE_PX}.",
        )
    return target_side_px


def _pad_to_minimum(image: Image.Image) -> tuple[Image.Image, int, int]:
    """Centre the page on a white canvas when a side is below the 280 px minimum."""
    width, height = image.size
    canvas_width, canvas_height = max(width, MIN_SIDE_PX), max(height, MIN_SIDE_PX)
    if (canvas_width, canvas_height) == (width, height):
        return image, 0, 0
    canvas = Image.new("RGB", (canvas_width, canvas_height), "white")
    offset_x, offset_y = (canvas_width - width) // 2, (canvas_height - height) // 2
    canvas.paste(image, (offset_x, offset_y))
    return canvas, offset_x, offset_y


def render_page(data: bytes, number: int = 1, target_side_px: int = TARGET_SIDE_PX) -> PageImage:
    """Render one page. The longest side is at most target_side_px, never above 1568."""
    target = _target_side(target_side_px)
    document = _open(data)
    try:
        total = len(document)
        if not 1 <= number <= total:
            raise RenderError(
                "PAGE_OUT_OF_RANGE", f"Page {number} is outside 1 to {total}."
            )
        page = document[number - 1]
        width_pt, height_pt = page.get_size()
        if width_pt <= 0 or height_pt <= 0:
            raise RenderError("UNREADABLE_PDF", "Page has no usable area.")
        scale = target / max(width_pt, height_pt)
        bitmap = page.render(scale=scale)
        # PDFium rounds each side up, so a scale computed from the points can land
        # one pixel above the limit. Re-render with a corrected scale instead of
        # resampling, which would blur small text.
        for _ in range(MAX_RENDER_ATTEMPTS):
            longest = max(bitmap.width, bitmap.height)
            if longest <= MAX_SIDE_PX:
                break
            scale *= MAX_SIDE_PX / longest
            bitmap.close()
            bitmap = page.render(scale=scale)
        try:
            image = bitmap.to_pil()
            content_width, content_height = image.size
        finally:
            bitmap.close()
    finally:
        document.close()
    image, offset_x, offset_y = _pad_to_minimum(image)
    buffer = BytesIO()
    image.save(buffer, "PNG", optimize=True)
    payload = buffer.getvalue()
    ensure_image_limits(image.width, image.height, len(payload))
    return PageImage(
        page_number=number,
        page_width_pt=float(width_pt),
        page_height_pt=float(height_pt),
        scale=scale,
        content_width_px=content_width,
        content_height_px=content_height,
        width_px=image.width,
        height_px=image.height,
        offset_x_px=offset_x,
        offset_y_px=offset_y,
        data=payload,
    )


def render_pages(
    data: bytes,
    numbers: tuple[int, ...] = (1,),
    target_side_px: int = TARGET_SIDE_PX,
    max_pages: int = 3,
) -> list[PageImage]:
    """Render the requested pages, refusing more than max_pages in one call."""
    if not numbers:
        raise RenderError("NO_PAGES", "Select at least one page.")
    if len(numbers) > max_pages:
        raise RenderError(
            "PAGE_BUDGET", f"At most {max_pages} pages are rendered in one request."
        )
    if len(set(numbers)) != len(numbers):
        raise RenderError("DUPLICATE_PAGE", "Each page may appear once per request.")
    return [render_page(data, number, target_side_px) for number in numbers]
