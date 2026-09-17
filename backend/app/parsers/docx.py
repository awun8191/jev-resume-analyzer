from io import BytesIO
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from defusedxml.ElementTree import fromstring

from app.parsers.errors import ParseError

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def extract_docx(data: bytes, max_uncompressed_bytes: int) -> dict:
    with ZipFile(BytesIO(data)) as archive:
        entries = archive.infolist()
        if (
            len(entries) > 1000
            or sum(entry.file_size for entry in entries) > max_uncompressed_bytes
        ):
            raise ParseError(413, "DOCX decompressed content exceeds the processing limit.")
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)):
            raise ParseError(422, "DOCX has ambiguous duplicate parts. Export a fresh copy.")
        for entry in entries:
            if entry.flag_bits & 1 or entry.compress_type not in (ZIP_STORED, ZIP_DEFLATED):
                raise ParseError(422, "DOCX encryption or compression is not supported.")
        if "[Content_Types].xml" not in names or "word/document.xml" not in names:
            raise ParseError(422, "Not a readable Word document. Export a fresh DOCX.")
        with archive.open("word/document.xml") as part:
            raw = part.read(max_uncompressed_bytes + 1)
        if len(raw) > max_uncompressed_bytes:
            raise ParseError(413, "DOCX content exceeds the processing limit.")
    root = fromstring(raw)
    if root.tag != W + "document":
        raise ParseError(422, "Unsupported Word document XML. Export a fresh DOCX.")
    # Walk once in XML order, including nested tables, text boxes and content controls.
    # Paragraph-end events avoid flattening nested paragraphs twice.
    pieces = []
    stack = [(root, False)]
    nodes = 0
    while stack:
        element, closing = stack.pop()
        if closing:
            if element.tag == W + "p":
                pieces.append("\n")
            continue
        nodes += 1
        if nodes > 200000:
            raise ParseError(413, "DOCX structure exceeds the processing limit.")
        if element.tag == W + "t":
            pieces.append(element.text or "")
        elif element.tag in (W + "br", W + "cr"):
            pieces.append("\f" if element.get(W + "type") == "page" else "\n")
        elif element.tag == W + "tab":
            pieces.append("\t")
        stack.append((element, True))
        stack.extend((child, False) for child in reversed(list(element)))
    text = "".join(pieces).strip()
    if not text:
        raise ParseError(422, "No readable DOCX text. Export a text-based document, not images.")
    return {
        "text": text,
        "page_count": None,
        "warnings": [
            {
                "code": "docx_layout",
                "message": "Check layout and duplicated alternate content. "
                "Headers, footers, footnotes and embedded objects are not extracted.",
            }
        ],
    }
