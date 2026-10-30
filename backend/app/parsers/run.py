"""Bounded document parsing, shared by the subprocess worker and the inline path."""

import hashlib

from app.parsers.errors import ParseError


def parse(kind: str, data: bytes, params: dict) -> dict:
    """Return {"result": ...} or {"status": int, "message": str}. Never raises ParseError."""
    from app.models.evidence import DocumentEvidence
    from app.parsers.docx import extract_docx
    from app.parsers.docx_evidence import extract_docx_evidence
    from app.parsers.pdf import extract_pdf
    from app.parsers.pdf_evidence import extract_pdf_evidence

    params = dict(params)
    try:
        parser = extract_pdf if kind == "pdf" else extract_docx
        char_limit = params.pop("max_chars")
        result = parser(data, **params)
        if len(result["text"]) > char_limit:
            raise ParseError(413, "Extracted text exceeds the processing limit.")
        evidence_parser = extract_pdf_evidence if kind == "pdf" else extract_docx_evidence
        try:
            evidence = evidence_parser(data)
        except ParseError:
            raise
        except Exception:
            evidence = {
                "source_format": kind,
                "limitations": [
                    "Metadata extraction failed; layout and hyperlinks: not assessed."
                ],
            }
        evidence["source_text_sha256"] = hashlib.sha256(
            result["text"].strip().encode()
        ).hexdigest()
        result["document_evidence"] = DocumentEvidence.model_validate(evidence).model_dump()
        return {"result": result}
    except ParseError as exc:
        return {"status": exc.status, "message": exc.message}
    except Exception:
        return {
            "status": 422,
            "message": "Document unreadable or too complex. Export a fresh text-based PDF or DOCX.",
        }
