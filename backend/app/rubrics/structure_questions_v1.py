"""Structure and formatting questions for the image route. Version 1.

The scoring lives in app/rubrics/structure_v1.py. This module only writes question
text, so the wording can change without moving a weight.
"""

from typing import Literal

from app.rubrics.structure_v1 import LAYOUT_OPTIONS, SECTION_KEYS

VERSION = "structure-1"

SECTION_DESCRIPTIONS = {
    "header": "the applicant name and contact details at the top",
    "summary": "a short summary or profile paragraph",
    "experience": "the employment history section",
    "education": "the education section",
    "skills": "the skills list",
    "projects": "the projects section",
}

FORMAT_CRITERIA = {
    "margins": {
        "pass": "Content keeps a clear margin on all four sides and nothing touches an edge.",
        "minor": "One margin is tight or uneven, but no content touches an edge.",
        "major": "Content touches or crosses a page edge, or the margins are very uneven.",
    },
    "alignment": {
        "pass": "Text blocks share few left edges and line up on a clear vertical grid.",
        "minor": "One block is misaligned or indented differently from the rest.",
        "major": "Several blocks use different left edges, so the page looks ragged.",
    },
    "hierarchy": {
        "pass": "Section headings are clearly larger or bolder than body text, consistently.",
        "minor": "One heading breaks the size or weight pattern used by the other headings.",
        "major": "Headings are hard to tell apart from body text, or the pattern changes often.",
    },
    "spacing": {
        "pass": "Space between sections and entries follows a repeatable rhythm.",
        "minor": "One gap is clearly larger or smaller than the rest.",
        "major": "Spacing is erratic, or entries run together with no gap.",
    },
    "density": {
        "pass": "Line length and white space keep the page easy to read.",
        "minor": "Some lines run long or the text is slightly crowded.",
        "major": "Lines span the full page width or the text is packed with no breathing room.",
    },
    "entry_format": {
        "pass": "Every entry in a section uses the same title, date and bullet pattern.",
        "minor": "One entry breaks the pattern used by its neighbours.",
        "major": "Entries in the same section follow two or more different patterns.",
    },
    "page_balance": {
        "pass": "Content fills the page evenly without a large empty area.",
        "minor": "The page ends with a noticeable empty area, or is slightly crowded.",
        "major": "A large part of the page is empty, or the page is badly overcrowded.",
    },
}


def _criteria(check: str) -> dict[str, str]:
    return {
        **FORMAT_CRITERIA[check],
        "unable_to_assess": "The page is unreadable or does not show this property.",
    }


def structure_questions(page_numbers: list[int]) -> dict:
    """One request worth of questions over the given pages, in reading order."""
    from app.services.image_request import page_path

    questions: dict = {
        "layout": {
            "type": "choice",
            "instructions": (
                f"How is the body text of the resume in {page_path(page_numbers[0])} "
                "arranged?"
            ),
            "criteria": LAYOUT_OPTIONS,
        },
        "readable": {
            "type": "noul",
            "instructions": (
                "Is every part of this resume page readable at this resolution, with no "
                "blur, clipping or unreadable text?"
            ),
        },
        "content_present": {
            "type": "noul",
            "instructions": "Does this resume page show any visible text at all?",
        },
    }
    for number in page_numbers:
        path = page_path(number)
        prefix = f"p{number}_"
        for check in FORMAT_CRITERIA:
            questions[f"{prefix}{check}"] = {
                "type": "choice",
                "instructions": (
                    f"Judge only the {check.replace('_', ' ')} of the resume page in "
                    f"{path}."
                ),
                "criteria": _criteria(check),
            }
            questions[f"{prefix}{check}_box"] = {
                "type": "box",
                "instructions": (
                    f"the part of the resume in {path} that shows the {check.replace('_', ' ')}"
                ),
            }
        for section in SECTION_KEYS:
            description = SECTION_DESCRIPTIONS[section]
            questions[f"{prefix}{section}_present"] = {
                "type": "noul",
                "instructions": f"Does {path} contain {description}?",
            }
            questions[f"{prefix}{section}_box"] = {
                "type": "box",
                "instructions": f"{description} in {path}",
            }
    return questions


Preset = Literal["sections", "entries", "structure", "both"]
