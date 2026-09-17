"""PDF coordinates are points, origin top-left, after page rotation."""
from io import BytesIO

import pdfplumber

from app.parsers.errors import ParseError
from app.parsers.pdf import _fix_bullets


def extract_pdf_evidence(data):
    spans, links, pages = [], [], []
    with pdfplumber.open(BytesIO(data)) as pdf:
        for number, page in enumerate(pdf.pages, 1):
            words = page.extract_words(extra_attrs=["fontname", "size"])
            for word in words:
                text = _fix_bullets(word["text"])
                if text != word["text"]:
                    if not text.strip():
                        continue
                spans.append({
                    "id": f"s{len(spans)}", "text": text, "page": number,
                    "bbox": [word["x0"], word["top"], word["x1"], word["bottom"]],
                    "font_name": word["fontname"], "font_size_pt": round(word["size"], 2),
                })
            margins = None
            if words:
                margins = [min(w["x0"] for w in words), min(w["top"] for w in words),
                           page.width - max(w["x1"] for w in words),
                           page.height - max(w["bottom"] for w in words)]
            pages.append({"number": number, "width_pt": page.width,
                          "height_pt": page.height, "rotation": page.rotation,
                          "margins_pt": margins,
                          "margin_kind": "estimated_content_whitespace" if words
                          else "not_assessed"})
            for annotation in page.annots or []:
                if str(annotation.get("data", {}).get("Subtype")) != "/'Link'":
                    continue
                box = [annotation["x0"], annotation["top"],
                       annotation["x1"], annotation["bottom"]]
                label = " ".join(w["text"] for w in words
                                 if w["x0"] < box[2] and w["x1"] > box[0]
                                 and w["top"] < box[3] and w["bottom"] > box[1])
                target = annotation.get("uri")
                links.append({"label": label, "target": target, "bbox": box,
                              "page": number, "kind": "external" if target else "internal"})
            if len(spans) > 5000 or len(links) > 500:
                raise ParseError(413, "Document metadata exceeds the processing limit.")
    return {"source_format": "pdf", "pages": pages, "spans": spans, "links": links,
            "limitations": ["PDF margins are estimated from text, not configured margins.",
                             "Reading order and visual appearance are not verified.",
                             "Link destinations were extracted, not visited."]}
