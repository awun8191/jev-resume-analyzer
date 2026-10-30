"""Synthetic provider and rasteriser doubles shared by the integration tests.

Nothing here talks to the network or to pdfium unless a test asks for the real
fixture. The answers are fixed so a score is reproducible.
"""

from io import BytesIO

from pypdf import PdfWriter

from app.models.image_answers import BoxAnswer, BoxEdges, ImageResponse, NoulAnswer, OptionAnswer
from app.models.questions import ChoiceAnswer, Distribution, ProviderResponse, Usage
from app.services.page_render import PageImage

OPTIONS = ("present", "absent", "not_applicable", "unable_to_assess")

SECTION_TOPS = {
    "header": 0.05,
    "summary": 0.15,
    "experience": 0.25,
    "education": 0.55,
    "skills": 0.75,
    "projects": 0.85,
}


def blank_pdf(pages: int) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=612, height=792)
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def page_image(number: int) -> PageImage:
    """A stand-in for a rendered page that passes every provider image limit."""
    return PageImage(
        page_number=number,
        page_width_pt=612.0,
        page_height_pt=792.0,
        scale=2.0,
        content_width_px=1080,
        content_height_px=1400,
        width_px=1080,
        height_px=1400,
        offset_x_px=0,
        offset_y_px=0,
        data=b"\x89PNG\r\n\x1a\n" + b"0" * 256,
    )


def choice(selected: str) -> ChoiceAnswer:
    return ChoiceAnswer(
        type="choice",
        choice=selected,
        probabilities=Distribution(**{key: 0.7 if key == selected else 0.1 for key in OPTIONS}),
        confidence=0.6,
    )


def option(selected: str) -> OptionAnswer:
    return OptionAnswer(type="choice", choice=selected, probabilities=None, confidence=0.9)


def noul(value: float) -> NoulAnswer:
    return NoulAnswer(type="noul", noul=value)


def box(top: float) -> BoxAnswer:
    return BoxAnswer(
        type="box",
        box=BoxEdges(top=top, bottom=min(0.99, top + 0.08), left=0.1, right=0.9),
        confidence=0.9,
    )


def perfect_structure_answers(questions: dict) -> dict:
    """A clean single column page: every check passes and every section is present."""
    answers = {}
    for key in questions:
        if key == "layout":
            answers[key] = option("one_column")
        elif key in ("readable", "content_present"):
            answers[key] = noul(1.0)
        elif key.endswith("_present"):
            answers[key] = noul(1.0)
        elif key.endswith("_box"):
            section = key.split("_", 1)[1].removesuffix("_box")
            answers[key] = box(SECTION_TOPS.get(section, 0.5))
        else:
            answers[key] = option("pass")
    return answers


class FakeGateway:
    """Records both call kinds and answers every question that was asked."""

    def __init__(self, text_choice="present", image_layout="one_column"):
        self.text_calls = []
        self.image_calls = []
        self.text_choice = text_choice
        self.image_layout = image_layout
        self.text_error = None
        self.image_error = None

    async def evaluate(self, state, questions):
        self.text_calls.append({"state": state, "questions": questions})
        if self.text_error is not None:
            raise self.text_error
        return ProviderResponse(
            model="jev-1.14.0",
            answers={key: choice(self.text_choice) for key in questions},
            usage=Usage(input_tokens=123, output_tokens=45),
        )

    async def evaluate_image(self, request):
        self.image_calls.append(request)
        if self.image_error is not None:
            raise self.image_error
        answers = perfect_structure_answers(request.body["questions"])
        if self.image_layout != "one_column":
            answers["layout"] = option(self.image_layout)
        return ImageResponse(
            model="jev-1.14.0",
            answers=answers,
            usage=Usage(input_tokens=900, output_tokens=30),
        )
