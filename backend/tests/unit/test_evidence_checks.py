import re
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile

from reportlab.pdfgen import canvas

from app.models.evidence import DocumentEvidence
from app.parsers.docx_evidence import extract_docx_evidence
from app.parsers.pdf_evidence import extract_pdf_evidence
from app.rubrics.cv_review_v2 import prepare
from app.services.layout_checks import layout_findings


def evidence(text="synthetic", **kwargs):
    return DocumentEvidence(source_format="pdf", source_text_sha256=sha256(
        text.encode()).hexdigest(), **kwargs)


def test_missing_or_stale_metadata_is_not_assessed():
    for item in (None, evidence()):
        findings = layout_findings(item, "changed text")
        assert len(findings) == 4
        assert all(f.answer == "unable_to_assess" for f in findings)
        assert all(f.confidence is None for f in findings)


def test_missing_fonts_and_estimated_margins_are_not_failures():
    findings = layout_findings(evidence(), "synthetic")
    assert all(f.answer == "unable_to_assess" for f in findings)


def test_two_bullets_get_independent_checks():
    text = "Experience\n• Built a service.\n• Helped with things."
    questions, bullets = prepare(text)
    assert len(bullets) == 2
    assert len(questions) == 14
    assert len({q.id for q in questions}) == 14
    assert bullets[0]["text"] == "Built a service."
    assert all("at least one" not in q.instructions.lower() for q in questions)


def test_bullet_boundaries_exclude_headings_and_role_lines():
    # Boundary classes observed in a real single-column PDF, rebuilt as synthetic text:
    # skills list followed by a section heading, a task bullet that runs into the next
    # role heading, a project header line, and an education heading.
    text = (
        "PROFESSIONAL EXPERIENCE\n"
        "Software Developer | SynthCorp 01/2025 - Present | Remote\n"
        "- Architected a backend using Python and FastAPI.\n"
        "- Added caching. Software Developer | NextCorp 06/2025 - 12/2025 | Remote\n"
        "- Built custom data extraction scripts for network designs.\n"
        "FEATURED PROJECTS\n"
        "- Built semantic search endpoints. Synthetic Project 08/2024 - 02/2025 "
        "Technologies: Python, Docker\n"
        "- Containerized ingestion microservices using Docker.\n"
        "EDUCATION & CERTIFICATIONS\n"
        "B.Eng. in Electrical Engineering Graduated: 2026 Synthetic University\n"
    )
    _, bullets = prepare(text)
    joined = "\n".join(b["text"] for b in bullets)
    assert "PROFESSIONAL EXPERIENCE" not in joined
    assert "EDUCATION & CERTIFICATIONS" not in joined
    for bullet in bullets:
        assert not re.search(r"\d{2}/\d{4}", bullet["text"]), bullet
        assert "Technologies:" not in bullet["text"], bullet["text"]
    passages = [b["text"] for b in bullets]
    assert "Architected a backend using Python and FastAPI." in passages
    assert "Containerized ingestion microservices using Docker." in passages
    assert not any("Synthetic Project" in p for p in passages)


def test_geometry_path_builds_bullets_from_real_pdf():
    output = BytesIO()
    page = canvas.Canvas(output, pagesize=(612, 792))
    y = 720
    page.setFont("Helvetica-Bold", 12)
    page.drawString(54, y, "PROFESSIONAL EXPERIENCE")
    y -= 18
    page.setFont("Helvetica", 11)
    page.drawString(54, y, "Software Developer | SynthCorp 01/2025 - Present | Remote")
    lines = ("\u2022 Architected a backend using Python and FastAPI deployed on",
             "Google Cloud Platform handling concurrent orders.",
             "\u2022 Added caching for queries.")
    for body in lines:
        y -= 13
        page.drawString(54, y, body)
    page.save()
    evidence = extract_pdf_evidence(output.getvalue())
    questions, bullets = prepare("PROFESSIONAL EXPERIENCE", evidence["spans"])
    assert [b["text"] for b in bullets] == [
        "Architected a backend using Python and FastAPI deployed on "
        "Google Cloud Platform handling concurrent orders.", "Added caching for queries."]
    assert len(questions) == 8 + 3 * len(bullets)


def test_docx_relationships_styles_margins_and_header():
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    r = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    output = BytesIO()
    with ZipFile(output, "w") as z:
        z.writestr("word/document.xml", f'''<w:document xmlns:w="{w}" xmlns:r="{r}">
        <w:body><w:p><w:hyperlink r:id="link"><w:r><w:t>Portfolio</w:t></w:r>
        </w:hyperlink></w:p><w:sectPr><w:pgSz w:w="12240" w:h="15840"/>
        <w:pgMar w:left="720" w:top="720" w:right="720" w:bottom="720"/>
        </w:sectPr></w:body></w:document>''')
        z.writestr("word/_rels/document.xml.rels", '''<Relationships>
        <Relationship Id="link" TargetMode="External" Target="https://example.com"/>
        </Relationships>''')
        z.writestr("word/styles.xml", f'''<w:styles xmlns:w="{w}">
        <w:style w:styleId="Normal"><w:rPr><w:sz w:val="22"/>
        <w:rFonts w:ascii="Calibri"/></w:rPr></w:style></w:styles>''')
        z.writestr("word/header1.xml", f'''<w:hdr xmlns:w="{w}"><w:p><w:r>
        <w:t>Synthetic Header</w:t></w:r></w:p></w:hdr>''')
    result = extract_docx_evidence(output.getvalue())
    assert result["links"][0]["target"] == "https://example.com"
    assert result["spans"][0]["font_size_pt"] == 11
    assert any(s["location"] == "header1" for s in result["spans"])
    assert result["pages"][0]["margins_pt"] == [36, 36, 36, 36]
    assert all("bbox" not in s for s in result["spans"])
