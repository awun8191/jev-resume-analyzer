"""Deterministic metadata checks. Never fetch URLs from uploaded documents."""
from collections import Counter
from hashlib import sha256
from urllib.parse import urlsplit

from app.models.analyses import Finding, RubricExplanation


def layout_findings(evidence, text):
    valid = evidence is not None and evidence.source_text_sha256 == sha256(
        text.strip().encode()).hexdigest()
    findings = []

    def add(key, dimension, answer, explanation):
        findings.append(Finding(
            question_id=key, dimension=dimension, question=dimension,
            scope="general_review", answer=answer, probabilities=None, confidence=None,
            criteria=[explanation], rubric_explanation=RubricExplanation(
                template_ref=f"v2.{key}", text=explanation)))

    if not valid:
        for key, label in [("links", "Hyperlink targets"), ("font_sizes", "Text font sizes"),
                           ("margins", "Page margins"), ("visual", "Visual placement")]:
            add(key, label, "unable_to_assess",
                "Not assessed: metadata unavailable or no longer matches edited text.")
        return findings
    assert evidence is not None
    targets = [link.target for link in evidence.links if link.kind == "external"]
    if targets:
        safe = all(target and urlsplit(target).scheme.lower() in
                   ("http", "https", "mailto", "tel") for target in targets)
        add("links", "Hyperlink targets", "present" if safe else "absent",
            "Extracted external links use recognized web, email or telephone schemes. "
            "Destinations were not visited; availability and ownership are not verified.")
    else:
        add("links", "Hyperlink targets", "unable_to_assess",
            "Not assessed: no external hyperlink targets were recovered. Visible URL text "
            "alone does not prove clickability.")
    sizes = Counter()
    for span in evidence.spans:
        if span.font_size_pt is not None and span.font_size_pt > 0:
            sizes[round(span.font_size_pt, 1)] += len(span.text)
    if sizes:
        dominant = sizes.most_common(1)[0][0]
        add("font_sizes", "Dominant text size", "present" if dominant >= 10 else "absent",
            f"Most character-weighted text uses {dominant:g} pt. The review guideline is "
            "at least 10 pt; this is not a rendered legibility assessment.")
    else:
        add("font_sizes", "Text font sizes", "unable_to_assess",
            "Not assessed: usable font sizes were not recovered.")
    configured = [p.margins_pt for p in evidence.pages if p.margin_kind == "configured"]
    if configured and all(configured):
        add("margins", "Configured margins", "present" if all(
            min(m) >= 36 for m in configured) else "absent",
            "All configured section margins are checked against a 36 pt minimum (0.5 inch).")
    else:
        add("margins", "Configured margins", "unable_to_assess",
            "Not assessed: PDF content whitespace is an estimate, not configured margins.")
    add("visual", "Visual placement", "unable_to_assess",
        "Not assessed: Jev is text-only. Extracted coordinates are available, but no visual "
        "inspection of header placement, overlap or alignment was performed.")
    return findings
