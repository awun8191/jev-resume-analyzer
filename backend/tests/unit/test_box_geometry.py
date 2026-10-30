"""Box fraction to pixel and point conversion. No network."""

import pytest

from app.services.box_geometry import (
    GeometryError,
    box_area_fraction,
    box_to_page_pixels,
    box_to_pdf_points,
    expand_box,
    intersects,
    points_to_viewer_pixels,
    validate_box,
)
from app.services.page_render import PageImage

HALF_LEFT = {"top": 0.0, "bottom": 1.0, "left": 0.0, "right": 0.5}
WHOLE = {"top": 0.0, "bottom": 1.0, "left": 0.0, "right": 1.0}


def letter_page(**overrides):
    values = {
        "page_number": 1,
        "page_width_pt": 612.0,
        "page_height_pt": 792.0,
        "scale": 1.9798,
        "content_width_px": 1212,
        "content_height_px": 1568,
        "width_px": 1212,
        "height_px": 1568,
        "offset_x_px": 0,
        "offset_y_px": 0,
        "data": b"",
    }
    values.update(overrides)
    return PageImage(**values)


def padded_page():
    # 236 x 1568 content centred on a 280 x 1568 canvas, as the rasteriser does.
    return letter_page(
        page_width_pt=300.0,
        content_width_px=236,
        width_px=280,
        offset_x_px=22,
        scale=1568 / 2000,
    )


def test_whole_page_maps_to_the_full_canvas():
    assert box_to_page_pixels(WHOLE, letter_page()) == (0, 0, 1212, 1568)


def test_half_width_box_maps_to_half_the_pixels():
    assert box_to_page_pixels(HALF_LEFT, letter_page()) == (0, 0, 606, 1568)


def test_box_maps_back_to_pdf_points():
    left, top, right, bottom = box_to_pdf_points(HALF_LEFT, letter_page())
    assert (round(left), round(top), round(right), round(bottom)) == (0, 0, 306, 792)


def test_offsets_are_removed_for_a_padded_canvas():
    page = padded_page()
    left, top, right, bottom = box_to_page_pixels(WHOLE, page)
    assert (left, top, right, bottom) == (0, 0, 236, 1568)
    # The white padding must not become part of the page coordinates.
    left, _, right, _ = box_to_page_pixels(
        {"top": 0, "bottom": 0.5, "left": 0.5, "right": 1.0}, page
    )
    assert left == 118
    assert right == page.content_width_px


def test_points_are_clipped_to_the_page():
    page = padded_page()
    assert box_to_pdf_points(WHOLE, page)[0] == 0


def test_viewer_zoom_scales_points():
    assert points_to_viewer_pixels((10, 20, 30, 40), 2) == (20.0, 40.0, 60.0, 80.0)


def test_area_and_expansion():
    assert box_area_fraction(HALF_LEFT) == 0.5
    grown = expand_box(HALF_LEFT, 0.1)
    assert grown["left"] == 0.0
    assert grown["right"] == 0.6
    assert grown["top"] == 0.0
    assert grown["bottom"] == 1.0


def test_intersects_counts_overlap_only():
    assert intersects((0, 0, 10, 10), (5, 5, 15, 15))
    assert not intersects((0, 0, 10, 10), (10, 0, 20, 10))


@pytest.mark.parametrize(
    "edges,code",
    [
        ({"top": 0, "bottom": 1, "left": 0}, "BAD_EDGES"),
        ({"top": 0, "bottom": 1, "left": 0, "right": 1, "x": 0}, "BAD_EDGES"),
        ({"top": 0, "bottom": 1, "left": 0, "right": 1.5}, "OUT_OF_RANGE"),
        ({"top": 0, "bottom": 1, "left": 0, "right": float("nan")}, "NOT_FINITE"),
        ({"top": 0, "bottom": 1, "left": 0, "right": True}, "NOT_A_NUMBER"),
        ({"top": 0.5, "bottom": 0.5, "left": 0, "right": 1}, "DEGENERATE"),
        ({"top": 0.5, "bottom": 0.1, "left": 0.6, "right": 0.4}, "DEGENERATE"),
    ],
)
def test_invalid_boxes_are_refused(edges, code):
    with pytest.raises(GeometryError) as error:
        validate_box(edges)
    assert error.value.code == code


def test_pad_must_be_a_fraction():
    with pytest.raises(GeometryError) as error:
        expand_box(WHOLE, 1.5)
    assert error.value.code == "BAD_PAD"


def test_zoom_must_be_positive():
    with pytest.raises(GeometryError) as error:
        points_to_viewer_pixels((0, 0, 1, 1), 0)
    assert error.value.code == "BAD_ZOOM"
