"""Spike CLI: send one PDF page image to TypeSafe and print the Box answers.

Dry run by default. Sending needs TYPESAFE_API_KEY in backend/.env and --send.

    uv run python scripts/image_spike.py tests/fixtures/two_page_resume.pdf
    uv run python scripts/image_spike.py tests/fixtures/two_page_resume.pdf --pages 1 2
    uv run python scripts/image_spike.py tests/fixtures/two_page_resume.pdf --send

This script is not wired into the API. It prints geometry and counts, never the
document text and never the API key.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import Settings  # noqa: E402
from app.rubrics.structure_questions_v1 import structure_questions  # noqa: E402
from app.rubrics.structure_v1 import (  # noqa: E402
    assessment_from_answers,
    score_structure,
)
from app.services.box_geometry import box_to_page_pixels, box_to_pdf_points  # noqa: E402
from app.services.image_request import (  # noqa: E402
    DANGER_ZONE_IMAGES_HEADER,
    RequestBuildError,
    build_image_request,
    page_path,
    parse_image_response,
)
from app.services.page_render import RenderError, render_pages  # noqa: E402

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
BOX_MODEL = "jev-1.14.0"  # Box needs Jev 1.14; pin it, the alias moves.
NOTE = (
    "Each entry under pages is one rendered page of a single resume, in reading order. "
    "The images are the only record of the document layout."
)

SECTIONS = (
    ("header", "the applicant name and contact block at the top of the resume"),
    ("summary", "the section heading SUMMARY and the paragraph under it"),
    ("experience", "the section heading EXPERIENCE and the employment entries under it"),
    ("education", "the section heading EDUCATION and the entries under it"),
    ("skills", "the section heading SKILLS and the list under it"),
    ("projects", "the section heading PROJECTS and the entries under it"),
)

ENTRIES = (
    ("job_1", "the first employment entry, the block that starts with 'Senior Backend Engineer'"),
    ("job_2", "the second employment entry, the block that starts with 'Kestrel Payments'"),
    ("job_3", "the third employment entry, the block that starts with 'Junior Developer'"),
)

LAYOUT_CRITERIA = {
    "one_column": "All body text sits in one vertical column.",
    "two_columns": "Body text is arranged in two vertical columns.",
    "three_or_more_columns": "Body text is arranged in three or more vertical columns.",
    "table": "Body text sits in ruled or aligned table cells.",
    "mixed": "The page mixes columns, tables or full-width blocks.",
}


def section_questions(page_number: int, sections=SECTIONS) -> dict:
    path = page_path(page_number)
    questions = {}
    for key, description in sections:
        questions[f"p{page_number}_{key}_box"] = {
            "type": "box",
            "instructions": f"{description} in {path}",
        }
        questions[f"p{page_number}_{key}_present"] = {
            "type": "noul",
            "instructions": f"Does {path} show {description}?",
        }
    return questions


def entry_questions(page_number: int, entries=ENTRIES) -> dict:
    path = page_path(page_number)
    questions = {}
    for key, description in entries:
        questions[f"p{page_number}_{key}_box"] = {
            "type": "box",
            "instructions": f"{description} in {path}",
        }
        questions[f"p{page_number}_{key}_present"] = {
            "type": "noul",
            "instructions": f"Does {path} show {description}?",
        }
    return questions


def layout_question(page_number: int) -> dict:
    return {
        "type": "choice",
        "instructions": (
            f"How is the body text of the resume in {page_path(page_number)} arranged?"
        ),
        "criteria": LAYOUT_CRITERIA,
    }


def build_questions(preset: str, page_numbers: list[int]) -> dict:
    if preset == "structure":
        return structure_questions(page_numbers)
    questions = {}
    if preset in ("sections", "both"):
        questions["layout_structure"] = layout_question(page_numbers[0])
        for number in page_numbers:
            questions.update(section_questions(number))
    if preset in ("entries", "both"):
        questions.update(entry_questions(page_numbers[0]))
    return questions


def page_of(key: str, page_numbers: list[int]) -> int:
    """Read the page number out of a question id such as p2_margins_box."""
    for number in page_numbers:
        if key.startswith(f"p{number}_"):
            return number
    return page_numbers[0]


def print_structure(parsed, page_numbers: list[int]) -> dict:
    assessment = assessment_from_answers(parsed.answers, len(page_numbers))
    report = score_structure(assessment)
    print(f"structure score: {report.score} ({report.reason})")
    print(f"assessable weight: {report.assessable_weight} lost: {report.lost_points}")
    for finding in report.findings:
        print(
            f"  [{finding.severity}] {finding.key} page {finding.page} "
            f"lost {finding.points_lost} box {finding.box} "
            f"conf {finding.box_confidence} :: {finding.evidence}"
        )
    for note in report.limitations:
        print(f"  limitation: {note}")
    return report.model_dump()


def print_plan(request, pages, questions: dict) -> None:
    print("pages")
    for page in pages:
        print(f"  {json.dumps(page.summary())}")
    plan = request.describe()
    print(f"transport: {plan['transport']}")
    print(f"header: {DANGER_ZONE_IMAGES_HEADER}: {request.headers[DANGER_ZONE_IMAGES_HEADER]}")
    print(f"questions: {len(questions)} {sorted(questions)}")
    print(f"json bytes: {plan['json_bytes']}  image bytes: {plan['total_image_bytes']}")
    print(f"reference uses: {plan['reference_uses']}")


def send(request, settings: Settings, timeout: float) -> dict:
    key = settings.typesafe_api_key.get_secret_value().strip()
    if not key:
        raise SystemExit("TYPESAFE_API_KEY is not set in backend/.env")
    boundary = "jev-image-spike-boundary"
    kwargs = request.http_kwargs(boundary)
    headers = {"Authorization": f"Bearer {key}", **kwargs["headers"]}
    started = time.perf_counter()
    with httpx.Client(timeout=timeout, trust_env=False) as client:
        response = client.post(ENDPOINT, content=kwargs["content"], headers=headers)
    elapsed_ms = (time.perf_counter() - started) * 1000
    if response.status_code != 200:
        # Provider error bodies are short and contain no document text.
        raise SystemExit(f"HTTP {response.status_code}: {response.text[:400]}")
    payload = response.json()
    return {"payload": payload, "elapsed_ms": round(elapsed_ms, 1), "http_status": 200}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--pages", type=int, nargs="+", default=[1])
    parser.add_argument(
        "--preset", choices=("sections", "entries", "structure", "both"), default="sections"
    )
    parser.add_argument("--transport", choices=("multipart", "base64"), default="multipart")
    parser.add_argument("--model", default=BOX_MODEL)
    parser.add_argument("--send", action="store_true", help="Send one billable request")
    parser.add_argument("--print-body", action="store_true")
    parser.add_argument("--evidence", type=Path, help="Write request and response JSON here")
    args = parser.parse_args()

    settings = Settings()
    data = args.pdf.read_bytes()
    try:
        pages = render_pages(data, tuple(args.pages))
    except RenderError as error:
        raise SystemExit(f"{error.code}: {error.message}") from None
    questions = build_questions(args.preset, args.pages)
    try:
        request = build_image_request(
            pages,
            questions,
            document_note=NOTE,
            model=args.model,
            transport=args.transport,
        )
    except RequestBuildError as error:
        raise SystemExit(f"{error.code}: {error.message}") from None

    structure = None
    print_plan(request, pages, questions)
    if args.print_body:
        print(json.dumps(request.describe()["body"], indent=2))

    if not args.send:
        print("dry run: pass --send to make one billable request")
        return

    result = send(request, settings, settings.typesafe_timeout_seconds)
    if args.evidence:
        # Write the raw response first, so a failed parse still leaves evidence.
        raw = {
            "generated_by": "backend/scripts/image_spike.py",
            "model_requested": args.model,
            "endpoint": ENDPOINT,
            "pages": [page.summary() for page in pages],
            "request": request.describe(),
            "response": result["payload"],
            "elapsed_ms": result["elapsed_ms"],
            "http_status": result["http_status"],
        }
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(raw, indent=2) + "\n")
        print(f"raw evidence written: {args.evidence}")
    try:
        parsed = parse_image_response(result["payload"], set(questions))
    except Exception:
        print(json.dumps(result["payload"], indent=2)[:4000])
        raise
    images = {page.page_number: page for page in pages}
    print(f"model: {parsed.model}")
    print(f"elapsed_ms: {result['elapsed_ms']}")
    print(f"usage: {parsed.usage.model_dump() if parsed.usage else None}")
    for key, answer in sorted(parsed.answers.items()):
        if answer.type == "box":
            page_number = page_of(key, args.pages)
            image = images[page_number]
            pixels = box_to_page_pixels(answer.box.model_dump(), image)
            points = box_to_pdf_points(answer.box.model_dump(), image)
            print(
                f"  {key}: box {answer.box.model_dump()} confidence {answer.confidence} "
                f"px {pixels} pt {[round(value, 1) for value in points]}"
            )
        elif answer.type == "noul":
            print(f"  {key}: noul {answer.noul}")
        else:
            print(f"  {key}: choice {answer.choice}")
    if args.preset == "structure":
        structure = print_structure(parsed, args.pages)

    if args.evidence:
        evidence = {
            "generated_by": "backend/scripts/image_spike.py",
            "model_requested": args.model,
            "model_returned": parsed.model,
            "endpoint": ENDPOINT,
            "pages": [page.summary() for page in pages],
            "request": request.describe(),
            "response": result["payload"],
            "structure": structure,
            "elapsed_ms": result["elapsed_ms"],
            "usage": parsed.usage.model_dump() if parsed.usage else None,
        }
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(evidence, indent=2) + "\n")
        print(f"evidence written: {args.evidence}")


if __name__ == "__main__":
    main()
