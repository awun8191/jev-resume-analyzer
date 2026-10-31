"""Reader-facing criteria for the content checks.

The rubric strings are written for the model: they name thresholds, prevalence
and conditions. A person reading the report needs the same rule in short, plain
words. Keep one line for what counts and one line for what does not count.
"""

from __future__ import annotations

READER_CRITERIA: dict[str, tuple[str, ...]] = {
    "impact_outcome": (
        "One entry links what you did to what changed.",
        "A list of duties alone does not count.",
    ),
    "impact_prevalence": (
        "Half or more of your entries state a result.",
        "An entry with duties only does not count.",
    ),
    "impact_magnitude": (
        "One result gives a number with a unit or baseline.",
        "A date or a version number does not count.",
    ),
    "impact_magnitude_prevalence": (
        "Half or more of your results give a number with a unit.",
        "A result with no quantity does not count.",
    ),
    "scope_actors": (
        "One entry names the people or groups your work served.",
        "A team name alone does not count.",
    ),
    "scope_prevalence": (
        "Half or more of your entries name who the work served.",
        "An entry with no audience does not count.",
    ),
    "scope_size": (
        "One entry gives the size or reach of the setting.",
        "A number with no setting does not count.",
    ),
    "ownership_own_action": (
        "One entry makes your own action clear.",
        "Company activity alone does not count.",
    ),
    "ownership_prevalence": (
        "Half or more of your entries lead with your action.",
        "Team wording with no actor does not count.",
    ),
    "ownership_decision": (
        "One entry describes a decision you made or shaped.",
        "Work done to instruction does not count.",
    ),
    "relevance_responsibility": (
        "One CV task matches a duty in the job post.",
        "No job post means this check does not apply.",
    ),
    "relevance_prevalence": (
        "Half or more of your work descriptions match the post.",
        "A description with no match does not count.",
    ),
    "relevance_requirement": (
        "The CV states one qualification the post asks for.",
        "A skill the post does not ask for does not count.",
    ),
    "clarity_concrete": (
        "One description names the thing you worked on.",
        "Vague words such as things or systems do not count.",
    ),
    "clarity_prevalence": (
        "Half or more of your descriptions name a real object.",
        "Generic wording does not count.",
    ),
    "clarity_self_contained": (
        "A reader outside the company can follow each description.",
        "Insider acronyms and shorthand do not count.",
    ),
    "complete_roles": (
        "Each role gives the employer, the title and the dates.",
        "A missing title or date does not count.",
    ),
    "complete_education": (
        "Each entry gives the issuer, the credential, the field and the dates.",
        "A missing field or date does not count.",
    ),
    "complete_projects": (
        "Each project gives its purpose and your part in it.",
        "A project with no purpose does not count.",
    ),
    "skills_evidence": (
        "Half or more of the listed skills appear in your experience.",
        "A skill in the list alone does not count.",
    ),
}


def plain_criteria(question_id: str) -> list[str]:
    """The reader-facing lines for one check, or an empty list when none exist."""
    return list(READER_CRITERIA.get(question_id, ()))
