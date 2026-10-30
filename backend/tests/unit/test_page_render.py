"""Rasteriser checks. Synthetic PDFs only, no network, no personal documents."""

from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import NameObject, NumberObject

from app.services.page_render import (
    MAX_IMAGE_BYTES,
    MAX_SIDE_PX,
    MAX_TOTAL_PX,
    MIN_SIDE_PX,
    MIN_TOTAL_PX,
    RenderError,
    image_limit_problems,
    page_count,
    page_size,
    render_page,
    render_pages,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "two_page_resume.pdf"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def synthetic_pdf(width=612, height=792, pages=1, rotation=None):
    writer = PdfWriter()
    for _ in range(pages):
        page = writer.add_blank_page(width=width, height=height)
        if rotation:
            page[NameObject("/Rotate")] = NumberObject(rotation)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def test_fixture_pages_respect_provider_limits():
    pages = render_pages(FIXTURE.read_bytes(), (1, 2))
    assert [page.page_number for page in pages] == [1, 2]
    for page in pages:
        assert page.data.startswith(PNG_MAGIC)
        assert MIN_SIDE_PX <= page.width_px <= MAX_SIDE_PX
        assert MIN_SIDE_PX <= page.height_px <= MAX_SIDE_PX
        assert MIN_TOTAL_PX <= page.width_px * page.height_px <= MAX_TOTAL_PX
        assert len(page.data) < MAX_IMAGE_BYTES
        assert image_limit_problems(page.width_px, page.height_px, page.size_bytes) == []


def test_longest_side_is_pinned_to_the_limit():
    page = render_page(synthetic_pdf(), 1)
    assert page.height_px == MAX_SIDE_PX
    assert page.width_px < page.height_px
    assert not page.padded


def test_aspect_ratio_is_preserved():
    page = render_page(synthetic_pdf(612, 792), 1)
    source_ratio = 612 / 792
    rendered_ratio = page.width_px / page.height_px
    assert abs(rendered_ratio - source_ratio) < 0.01
    assert page.page_width_pt == 612
    assert page.page_height_pt == 792


def test_tall_narrow_page_is_centred_on_a_white_canvas():
    page = render_page(synthetic_pdf(300, 2000), 1)
    assert page.width_px == MIN_SIDE_PX
    assert page.content_width_px < MIN_SIDE_PX
    assert page.offset_x_px == (MIN_SIDE_PX - page.content_width_px) // 2
    assert page.padded
    from PIL import Image

    with Image.open(BytesIO(page.data)) as image:
        assert image.getpixel((0, 800)) == (255, 255, 255)
        assert image.getpixel((page.width_px - 1, 800)) == (255, 255, 255)


def test_rotation_is_applied_before_sizing():
    page = render_page(synthetic_pdf(612, 792, rotation=90), 1)
    assert page.width_px > page.height_px
    assert page.width_px == MAX_SIDE_PX


def test_page_size_and_count():
    data = synthetic_pdf(pages=3)
    assert page_count(data) == 3
    assert page_size(data) == (612.0, 792.0)


@pytest.mark.parametrize("target", [0, 100, 279, 1569, 4000])
def test_target_side_must_stay_inside_the_provider_range(target):
    with pytest.raises(RenderError) as error:
        render_page(synthetic_pdf(), 1, target)
    assert error.value.code == "TARGET_OUT_OF_RANGE"


@pytest.mark.parametrize("number", [0, 2, 99])
def test_page_number_must_exist(number):
    with pytest.raises(RenderError) as error:
        render_page(synthetic_pdf(pages=1), number)
    assert error.value.code == "PAGE_OUT_OF_RANGE"


@pytest.mark.parametrize("data", [b"", b"not a pdf", b"%PDF-1.7\nbroken"])
def test_unreadable_input_is_refused(data):
    with pytest.raises(RenderError) as error:
        render_page(data, 1)
    assert error.value.code == "UNREADABLE_PDF"


def test_render_pages_enforces_budget_and_uniqueness():
    data = synthetic_pdf(pages=3)
    with pytest.raises(RenderError) as error:
        render_pages(data, (1, 2, 3), max_pages=2)
    assert error.value.code == "PAGE_BUDGET"
    with pytest.raises(RenderError) as error:
        render_pages(data, (1, 1))
    assert error.value.code == "DUPLICATE_PAGE"
    with pytest.raises(RenderError) as error:
        render_pages(data, ())
    assert error.value.code == "NO_PAGES"


def test_image_limit_problems_reports_each_rule():
    assert image_limit_problems(100, 100, 10) == [
        "a side is under 280 px",
        "total pixels outside the accepted range",
    ]
    assert image_limit_problems(1568, 1568, MAX_IMAGE_BYTES + 1) == ["image exceeds 16 MiB"]
    assert image_limit_problems(2000, 2000, 10) == [
        "a side is over 1568 px",
        "total pixels outside the accepted range",
    ]
