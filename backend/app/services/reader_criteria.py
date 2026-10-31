"""Reader-facing criteria for the content checks.

The rubric strings are written for the model: they name thresholds, prevalence
and conditions. A person reading the report needs the same rule in short, plain
words. Each check gives two lines: what counts, and what does not count.

The text follows ASD-STE100: one idea per sentence, active voice, approved
words, no contractions. Run the checker after an edit:

    python3 ~/.hermes/skills/messaging/asd-ste100/scripts/ste_lint.py \
        --mode descriptive reader_criteria.txt
"""

from __future__ import annotations

READER_CRITERIA: dict[str, tuple[str, ...]] = {
    "impact_outcome": (
        "One entry shows what you did and what changed.",
        "A list of duties does not count.",
    ),
    "impact_prevalence": (
        "Half or more of your entries show a result.",
        "An entry with duties only does not count.",
    ),
    "impact_magnitude": (
        "One result gives a number with a unit.",
        "A date or a version does not count.",
    ),
    "impact_magnitude_prevalence": (
        "Half or more of your results give a number and a unit.",
        "A result with no number does not count.",
    ),
    "scope_actors": (
        "One entry names the people or groups that your work helped.",
        "A team name alone does not count.",
    ),
    "scope_prevalence": (
        "Half or more of your entries name the people that your work helped.",
        "An entry with no people does not count.",
    ),
    "scope_size": (
        "One entry gives the size of the company or the team.",
        "A number with no company or team does not count.",
    ),
    "ownership_own_action": (
        "One entry shows your own work.",
        "Company work alone does not count.",
    ),
    "ownership_prevalence": (
        "Half or more of your entries start with your own work.",
        "A sentence with no actor does not count.",
    ),
    "ownership_decision": (
        "One entry shows a decision that you made.",
        "Work that follows an instruction does not count.",
    ),
    "relevance_responsibility": (
        "One task in the resume agrees with a duty in the job post.",
        "If there is no job post, this check does not apply.",
    ),
    "relevance_prevalence": (
        "Half or more of your tasks agree with the job post.",
        "A task that does not agree does not count.",
    ),
    "relevance_requirement": (
        "The resume shows one qualification that the job post states.",
        "A skill that the job post does not list does not count.",
    ),
    "clarity_concrete": (
        "One description names the thing that you worked on.",
        "General words do not count.",
    ),
    "clarity_prevalence": (
        "Half or more of your descriptions name a clear thing.",
        "A general description does not count.",
    ),
    "clarity_self_contained": (
        "A reader who does not work at your company can understand each description.",
        "A short form that only your team knows does not count.",
    ),
    "complete_roles": (
        "Each role gives the employer, the title and the dates.",
        "A role with no title or no date does not count.",
    ),
    "complete_education": (
        "Each entry gives the school or the issuer, the award, the field and the dates.",
        "An entry with no field or no date does not count.",
    ),
    "complete_projects": (
        "Each project gives its purpose and your part.",
        "A project with no purpose does not count.",
    ),
    "skills_evidence": (
        "Your experience also shows half or more of your listed skills.",
        "A skill in the list only does not count.",
    ),
}


def plain_criteria(question_id: str) -> list[str]:
    """The reader-facing lines for one check, or an empty list when none exist."""
    return list(READER_CRITERIA.get(question_id, ()))
