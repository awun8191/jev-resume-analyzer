from io import BytesIO

from pypdf import PdfReader

from app.parsers.errors import ParseError

# Standard-font PDFs often render the bullet glyph as an unresolved character id.
CID_BULLETS = {"(cid:127)": "\u2022", "(cid:149)": "\u2022", "(cid:155)": "\u2022"}


def _fix_bullets(text):
    for cid, bullet in CID_BULLETS.items():
        text = text.replace(cid, bullet)
    return text


def extract_pdf(data: bytes, max_pages: int) -> dict:
    reader = PdfReader(BytesIO(data), strict=False)
    if reader.is_encrypted:
        raise ParseError(422, "Remove the PDF password and upload an unencrypted copy.")
    if len(reader.pages) > max_pages:
        raise ParseError(413, "The PDF exceeds the page limit. Upload a shorter document.")
    import pdfplumber

    with pdfplumber.open(BytesIO(data)) as document:
        texts = [_fix_bullets(page.extract_text() or "") for page in document.pages]
    if not any(t.strip() for t in texts):
        raise ParseError(
            422,
            "No selectable text found. Export a text-based PDF or DOCX; "
            "scanned documents require OCR, which is not supported.",
        )
    warnings = [
        {
            "code": "reading_order",
            "message": "Check reading order and completeness, especially columns and graphics.",
        }
    ]
    if any(not t.strip() for t in texts):
        warnings.append(
            {
                "code": "partial_text",
                "message": "Some pages have no selectable text. Check for missing scanned content.",
            }
        )
    return {"text": "\n\f\n".join(texts), "page_count": len(texts), "warnings": warnings}
