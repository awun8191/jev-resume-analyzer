"""Convert Box answers to page pixels and PDF points.

A Box answer gives four edges as fractions of the image that was sent. To draw that
box on the document, or to compare it with extracted text spans, convert the edges
back through the transform stored on PageImage.

Coordinate conventions:

- Box fractions: origin top-left, 0 to 1, measured on the canvas actually sent.
- Page pixels: origin top-left of the page content, in rendered pixels.
- PDF points: origin top-left of the page, matching the existing document evidence
  contract in app/models/evidence.py.
"""

from collections.abc import Mapping
from math import isfinite

from app.services.page_render import PageImage

EDGES = ("left", "top", "right", "bottom")


class GeometryError(ValueError):
    """A box cannot be interpreted as a rectangle."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _fraction(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GeometryError("NOT_A_NUMBER", f"{name} must be a number.")
    number = float(value)
    if not isfinite(number):
        raise GeometryError("NOT_FINITE", f"{name} must be finite.")
    if not 0.0 <= number <= 1.0:
        raise GeometryError("OUT_OF_RANGE", f"{name} must be between 0 and 1.")
    return number


def validate_box(edges: Mapping[str, float]) -> dict[str, float]:
    """Return the four edges as floats, refusing anything that is not a rectangle."""
    if not isinstance(edges, Mapping):
        raise GeometryError("NOT_A_BOX", "A box must be a mapping of four edges.")
    extra = set(edges) - set(EDGES)
    missing = set(EDGES) - set(edges)
    if extra or missing:
        raise GeometryError(
            "BAD_EDGES", f"A box needs exactly left, top, right and bottom. Got {sorted(edges)}."
        )
    box = {name: _fraction(edges[name], name) for name in EDGES}
    if not (box["left"] < box["right"] and box["top"] < box["bottom"]):
        raise GeometryError("DEGENERATE", "left must be less than right and top less than bottom.")
    return box


def expand_box(edges: Mapping[str, float], pad: float) -> dict[str, float]:
    """Grow a box by a fraction of the image on every side, kept inside the image."""
    box = validate_box(edges)
    if not 0.0 <= pad <= 1.0:
        raise GeometryError("BAD_PAD", "pad must be between 0 and 1.")
    return {
        "left": max(0.0, box["left"] - pad),
        "top": max(0.0, box["top"] - pad),
        "right": min(1.0, box["right"] + pad),
        "bottom": min(1.0, box["bottom"] + pad),
    }


def box_area_fraction(edges: Mapping[str, float]) -> float:
    box = validate_box(edges)
    return (box["right"] - box["left"]) * (box["bottom"] - box["top"])


def box_to_page_pixels(
    edges: Mapping[str, float], image: PageImage
) -> tuple[int, int, int, int]:
    """Left, top, right, bottom in rendered page pixels, clipped to the page content."""
    box = validate_box(edges)
    x0 = box["left"] * image.width_px - image.offset_x_px
    x1 = box["right"] * image.width_px - image.offset_x_px
    y0 = box["top"] * image.height_px - image.offset_y_px
    y1 = box["bottom"] * image.height_px - image.offset_y_px
    return (
        _clip(round(x0), image.content_width_px),
        _clip(round(y0), image.content_height_px),
        _clip(round(x1), image.content_width_px),
        _clip(round(y1), image.content_height_px),
    )


def box_to_pdf_points(
    edges: Mapping[str, float], image: PageImage
) -> tuple[float, float, float, float]:
    """Left, top, right, bottom in PDF points, origin top-left.

    These are the same units as the bbox on a Span in the document evidence payload,
    so a box can be compared with extracted text without a second transform.
    """
    if image.scale <= 0:
        raise GeometryError("BAD_SCALE", "Page scale must be positive.")
    x0, y0, x1, y1 = box_to_page_pixels(edges, image)
    return (x0 / image.scale, y0 / image.scale, x1 / image.scale, y1 / image.scale)


def points_to_viewer_pixels(
    bbox_points: tuple[float, float, float, float], zoom: float
) -> tuple[float, float, float, float]:
    """Scale a point-space box for a viewer rendered at `zoom` CSS pixels per point.

    A PDF viewer that renders page 1 at 2x draws 1 point as 2 pixels. Pass that
    factor here; no page offset is applied, so the viewer adds its own page origin.
    """
    if not isfinite(zoom) or zoom <= 0:
        raise GeometryError("BAD_ZOOM", "zoom must be a positive number.")
    return tuple(round(value * zoom, 2) for value in bbox_points)  # type: ignore[return-value]


def intersects(
    a: tuple[float, float, float, float], b: tuple[float, float, float, float]
) -> bool:
    """True when two point or pixel boxes overlap. Touching edges do not count."""
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def _clip(value: int, limit: int) -> int:
    return max(0, min(value, limit))
