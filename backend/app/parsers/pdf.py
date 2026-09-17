from io import BytesIO

from pypdf import PdfReader

from app.parsers.errors import ParseError


def extract_pdf(data: bytes, max_pages: int) -> dict:
    reader = PdfReader(BytesIO(data), strict=False)
    if reader.is_encrypted:
        raise ParseError(422, "Remove the PDF password and upload an unencrypted copy.")
    if len(reader.pages) > max_pages:
        raise ParseError(413, "The PDF exceeds the page limit. Upload a shorter document.")
    texts = [page.extract_text() or "" for page in reader.pages]
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
