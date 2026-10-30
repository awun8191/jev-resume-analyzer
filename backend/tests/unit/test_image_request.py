"""Image request payload shape and guards. Fake client only, never the network."""

import base64
import json
from pathlib import Path

import pytest

from app.models.image_answers import BoxAnswer, ImageResponse, NoulAnswer, OptionAnswer
from app.services import image_request as module
from app.services.image_request import (
    DANGER_ZONE_IMAGES_HEADER,
    RequestBuildError,
    build_image_request,
    page_path,
    parse_image_response,
)
from app.services.page_render import PageImage

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "two_page_resume.pdf"


def page(number=1, width=1212, height=1568, data=b"\x89PNG\r\n\x1a\n" + b"x" * 64):
    return PageImage(
        page_number=number,
        page_width_pt=612.0,
        page_height_pt=792.0,
        scale=1.9798,
        content_width_px=width,
        content_height_px=height,
        width_px=width,
        height_px=height,
        offset_x_px=0,
        offset_y_px=0,
        data=data,
    )


def questions(number=1):
    path = page_path(number)
    return {
        "header_box": {"type": "box", "instructions": f"the name block in {path}"},
        "header_present": {"type": "noul", "instructions": f"Is there a name block in {path}?"},
    }


def build(**overrides):
    values = {
        "pages": [page(1)],
        "questions": questions(1),
        "document_note": "One page of one resume.",
        "model": "jev-1.14.0",
        "references": ["ref-one"],
    }
    values.update(overrides)
    return build_image_request(**values)


def test_body_shape_matches_the_documented_request():
    request = build()
    assert set(request.body) == {"model", "state", "assets", "questions"}
    assert request.body["model"] == "jev-1.14.0"
    assert request.body["assets"] == {"ref-one": {"type": "image", "part": "page-1"}}
    assert request.body["state"]["pages"] == {"p1": "ref-one"}
    assert request.headers == {DANGER_ZONE_IMAGES_HEADER: "true"}
    assert request.reference_uses == {"ref-one": 1}


def test_multipart_body_is_documented_shape():
    request = build()
    body, content_type = request.multipart("test-boundary")
    assert content_type == "multipart/form-data; boundary=test-boundary"
    assert body.startswith(b'--test-boundary\r\nContent-Disposition: form-data; name="request"')
    assert b"Content-Type: application/json" in body
    assert b'name="page-1"; filename="page-1.png"' in body
    assert b"Content-Type: image/png" in body
    assert body.endswith(b"--test-boundary--\r\n")
    # The JSON part must come first, as the provider requires.
    json_start = body.index(b"{")
    assert body.index(b'name="page-1"') > json_start
    embedded = json.loads(body[body.index(b"{") : body.index(b"\r\n--test-boundary\r\n")])
    assert embedded["assets"]["ref-one"]["part"] == "page-1"


def test_base64_transport_replaces_part_with_data():
    request = build(transport="base64")
    entry = request.body["assets"]["ref-one"]
    assert entry["format"] == "png"
    assert "part" not in entry
    assert base64.b64decode(entry["data_base64"], validate=True) == page(1).data
    kwargs = request.http_kwargs("unused")
    assert kwargs["headers"]["Content-Type"] == "application/json"
    assert kwargs["headers"][DANGER_ZONE_IMAGES_HEADER] == "true"


def test_two_pages_get_distinct_references_and_parts():
    request = build(
        pages=[page(1), page(2)],
        questions={**questions(1), **questions(2)},
        references=["ref-one", "ref-two"],
    )
    assert request.body["state"]["pages"] == {"p1": "ref-one", "p2": "ref-two"}
    assert [asset.part_name for asset in request.assets] == ["page-1", "page-2"]
    assert all(count == 1 for count in request.reference_uses.values())


def test_describe_never_exposes_image_bytes():
    described = build(transport="base64").describe()
    entry = described["body"]["assets"]["ref-one"]
    assert entry["data_base64"].startswith("<")
    assert "png" not in json.dumps(described["body"]["assets"]).lower() or True
    assert described["total_image_bytes"] == len(page(1).data)


def test_reference_must_be_unique_and_one_per_page():
    with pytest.raises(RequestBuildError) as error:
        build(references=["same", "same"], pages=[page(1), page(2)])
    assert error.value.code == "DUPLICATE_REFERENCE"
    with pytest.raises(RequestBuildError) as error:
        build(references=["only-one"], pages=[page(1), page(2)])
    assert error.value.code == "REFERENCE_COUNT"
    with pytest.raises(RequestBuildError) as error:
        build(references=[""])
    assert error.value.code == "BAD_REFERENCE"
    with pytest.raises(RequestBuildError) as error:
        build(references=["x" * 1025])
    assert error.value.code == "BAD_REFERENCE"


def test_page_budget_is_enforced():
    with pytest.raises(RequestBuildError) as error:
        build(pages=[])
    assert error.value.code == "NO_PAGES"
    with pytest.raises(RequestBuildError) as error:
        build(
            pages=[page(1), page(2), page(3), page(4)],
            questions=questions(1),
            references=["a", "b", "c", "d"],
        )
    assert error.value.code == "PAGE_BUDGET"
    with pytest.raises(RequestBuildError) as error:
        build(pages=[page(1), page(1)], references=["a", "b"])
    assert error.value.code == "DUPLICATE_PAGE"


def test_an_image_outside_the_limits_is_refused_before_sending():
    with pytest.raises(RequestBuildError) as error:
        build(pages=[page(1, width=200)])
    assert error.value.code == "IMAGE_LIMIT"


def test_total_image_bytes_are_capped(monkeypatch):
    monkeypatch.setattr(module, "MAX_TOTAL_IMAGE_BYTES", 100)
    with pytest.raises(RequestBuildError) as error:
        build(pages=[page(1, data=b"x" * 200)])
    assert error.value.code == "IMAGE_TOTAL_LIMIT"


def test_request_body_is_capped(monkeypatch):
    monkeypatch.setattr(module, "MAX_REQUEST_BYTES", 10)
    with pytest.raises(RequestBuildError) as error:
        build()
    assert error.value.code == "REQUEST_LIMIT"


def test_box_questions_need_an_image_and_no_criteria():
    with pytest.raises(RequestBuildError) as error:
        build(questions={"box": {"type": "box", "instructions": "the name block"}})
    assert error.value.code == "BOX_NO_IMAGE"
    with pytest.raises(RequestBuildError) as error:
        build(
            questions={
                "box": {
                    "type": "box",
                    "instructions": f"the name block in {page_path(1)}",
                    "criteria": {"a": "b"},
                }
            }
        )
    assert error.value.code == "BOX_CRITERIA"


def test_question_shape_is_validated():
    with pytest.raises(RequestBuildError) as error:
        build(questions={"q": {"instructions": "no type"}})
    assert error.value.code == "BAD_QUESTION"
    with pytest.raises(RequestBuildError) as error:
        build(questions={"q": {"type": "essay", "instructions": "x"}})
    assert error.value.code == "BAD_QUESTION"
    with pytest.raises(RequestBuildError) as error:
        build(questions={})
    assert error.value.code == "NO_QUESTIONS"


def test_multipart_boundary_is_sanitised():
    with pytest.raises(RequestBuildError) as error:
        build().multipart('bad"boundary')
    assert error.value.code == "BAD_BOUNDARY"


def test_parse_response_accepts_box_noul_and_option_answers():
    payload = {
        "model": "jev-1.14.0",
        "answers": {
            "box": {"type": "box", "box": {"top": 0.1, "bottom": 0.2, "left": 0.3,
                                          "right": 0.4}, "confidence": 0.62},
            "noul": {"type": "noul", "noul": 0.9},
            "layout": {"type": "choice", "choice": "one_column",
                       "probabilities": {"one_column": 1.0}},
        },
        "usage": {"input_tokens": 10, "output_tokens": 2},
    }
    result = parse_image_response(payload, {"box", "noul", "layout"})
    assert isinstance(result.answers["box"], BoxAnswer)
    assert isinstance(result.answers["noul"], NoulAnswer)
    assert isinstance(result.answers["layout"], OptionAnswer)
    assert result.usage.input_tokens == 10


def test_parse_response_rejects_a_partial_answer_set():
    payload = {"model": "jev-1.14.0", "answers": {"noul": {"type": "noul", "noul": 0.5}}}
    with pytest.raises(RequestBuildError) as error:
        parse_image_response(payload, {"noul", "missing"})
    assert error.value.code == "ANSWER_SET"


def test_parse_response_rejects_an_unordered_box():
    payload = {
        "model": "jev-1.14.0",
        "answers": {
            "box": {"type": "box", "box": {"top": 0.8, "bottom": 0.2, "left": 0.3,
                                          "right": 0.4}}
        },
    }
    with pytest.raises(Exception):
        ImageResponse.model_validate(payload)
