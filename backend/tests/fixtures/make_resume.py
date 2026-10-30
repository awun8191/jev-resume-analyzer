"""Build the synthetic two-page resume fixture used by the image spike tests.

Run from backend/:  uv run python tests/fixtures/make_resume.py

The fixture is fictional. It contains no real applicant data, no photograph and no
hyperlinks. Content is fixed, so the rendered page geometry is stable across runs.
"""

from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUTPUT = Path(__file__).with_name("two_page_resume.pdf")
PAGE_WIDTH, PAGE_HEIGHT = letter
LEFT = 54

NAME = "ALEX MORGAN"
CONTACT = "alex.morgan@example.com | Lagos, Nigeria | github.com/alexmorgan"

SUMMARY = (
    "Backend engineer with five years building Python services for payment and "
    "logistics teams. Comfortable owning a service from design to on-call."
)

EXPERIENCE = [
    (
        "Senior Backend Engineer | Northwind Logistics | 03/2022 - Present",
        [
            "Built a FastAPI rating service that handles 40,000 shipments an hour.",
            "Led the billing migration to Postgres and cut reconciliation errors by 30 percent.",
            "Mentored three engineers and introduced a weekly design review.",
            "Cut p95 rating latency from 900 ms to 120 ms by caching tariff lookups.",
            "Wrote the incident runbook that the on-call rotation now uses.",
        ],
    ),
    (
        "Backend Engineer | Kestrel Payments | 07/2019 - 02/2022",
        [
            "Implemented idempotent payment webhooks handling 1.2 million events a month.",
            "Added tracing and structured logging that cut incident diagnosis to 15 minutes.",
            "Paired with the fraud team to add velocity checks before settlement.",
        ],
    ),
    (
        "Junior Developer | Adept Systems | 08/2017 - 06/2019",
        [
            "Maintained a Django inventory tool for twelve retail branches.",
            "Wrote the first automated test suite for the reporting module.",
        ],
    ),
]

EDUCATION = [
    (
        "BSc Computer Science | University of Lagos | 09/2015 - 06/2019",
        ["Final year project: a timetable scheduler used by two departments."],
    )
]

SKILLS = [
    "Languages: Python, TypeScript, SQL",
    "Frameworks: FastAPI, Django, React",
    "Infrastructure: Postgres, Redis, Docker, AWS",
]

PROJECTS = [
    (
        "Route Planner | 2024",
        ["Built a route planner with OSRM and FastAPI, serving 200 queries a day."],
    )
]


def _heading(pdf: canvas.Canvas, text: str, y: float) -> float:
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(LEFT, y, text)
    pdf.setLineWidth(0.5)
    pdf.line(LEFT, y - 4, PAGE_WIDTH - LEFT, y - 4)
    return y - 20


def _entry(pdf: canvas.Canvas, title: str, bullets: list[str], y: float) -> float:
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(LEFT, y, title)
    y -= 14
    pdf.setFont("Helvetica", 9.5)
    for bullet in bullets:
        pdf.drawString(LEFT + 12, y, f"- {bullet}")
        y -= 12
    return y - 6


def build() -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle("Synthetic two page resume")

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(LEFT, PAGE_HEIGHT - 72, NAME)
    pdf.setFont("Helvetica", 9.5)
    pdf.drawString(LEFT, PAGE_HEIGHT - 90, CONTACT)

    y = PAGE_HEIGHT - 122
    y = _heading(pdf, "SUMMARY", y)
    pdf.setFont("Helvetica", 9.5)
    for line in (SUMMARY[:73], SUMMARY[73:]):
        pdf.drawString(LEFT, y, line)
        y -= 12
    y -= 10

    y = _heading(pdf, "EXPERIENCE", y)
    for title, bullets in EXPERIENCE:
        y = _entry(pdf, title, bullets, y)

    pdf.showPage()

    y = PAGE_HEIGHT - 72
    y = _heading(pdf, "EDUCATION", y)
    for title, bullets in EDUCATION:
        y = _entry(pdf, title, bullets, y)
    y -= 8

    y = _heading(pdf, "SKILLS", y)
    pdf.setFont("Helvetica", 9.5)
    for line in SKILLS:
        pdf.drawString(LEFT, y, line)
        y -= 13
    y -= 20

    y = _heading(pdf, "PROJECTS", y)
    for title, bullets in PROJECTS:
        y = _entry(pdf, title, bullets, y)

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def main() -> None:
    data = build()
    OUTPUT.write_bytes(data)
    print(f"wrote {OUTPUT} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
