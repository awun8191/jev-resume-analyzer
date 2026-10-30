from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from app.main import app


def pdf_bytes(text="Synthetic example project", encrypted=False, blank=False):
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    if not blank:
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
        )
        stream = DecodedStreamObject()
        stream.set_data(f"BT /F1 12 Tf 30 700 Td ({text}) Tj ET".encode())
        page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("synthetic-password")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def docx_bytes():
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(
            "word/document.xml",
            """<w:document
          xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body><w:p><w:r><w:t>First synthetic paragraph</w:t></w:r></w:p>
          <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Table text</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
          <w:sdt><w:sdtContent><w:p><w:r><w:t>Content control</w:t></w:r></w:p>
          </w:sdtContent></w:sdt><w:p><w:r><w:t>Last paragraph</w:t></w:r></w:p>
          </w:body></w:document>""",
        )
    return output.getvalue()


def pytest_make_parametrize_id(config, val, argname):
    return f"{argname}={repr(val)[:60]}" if argname == "data" else None


@pytest.mark.parametrize(
    "name,data,format_",
    [("example.PDF", pdf_bytes(), "pdf"), ("example.docx", docx_bytes(), "docx")],
)
def test_extraction(name, data, format_):
    with TestClient(app, raise_server_exceptions=False) as client:
        result = client.post("/api/v1/documents/extract", files={"file": (name, data)})
    assert result.status_code == 200
    body = result.json()
    assert body["source_format"] == format_
    if format_ == "docx":
        assert body["text"].splitlines() == [
            "First synthetic paragraph",
            "Table text",
            "Content control",
            "Last paragraph",
        ]
        assert body["page_count"] is None
    else:
        assert "Synthetic example project" in body["text"]
        assert body["page_count"] == 1


@pytest.mark.parametrize(
    "name,data,status",
    [
        ("empty.pdf", b"", 422),
        ("wrong.txt", b"hello", 415),
        ("wrong.pdf", b"hello", 415),
        ("broken.pdf", b"%PDF-1.7\nbroken", 422),
        ("locked.pdf", pdf_bytes(encrypted=True), 422),
        ("scan.pdf", pdf_bytes(blank=True), 422),
        ("bad.docx", b"PK\x03\x04broken", 422),
        ("large.pdf", b"%PDF-" + b"x" * 4000000, 413),
    ],
)
def test_bad_documents(name, data, status):
    with TestClient(app, raise_server_exceptions=False) as client:
        result = client.post("/api/v1/documents/extract", files={"file": (name, data)})
    assert result.status_code == status
    assert set(result.json()) == {"error", "request_id"}


@pytest.mark.parametrize(
    "files",
    [
        [],
        [("wrong", ("a.pdf", pdf_bytes()))],
        [("file", ("a.pdf", pdf_bytes())), ("file", ("b.pdf", pdf_bytes()))],
    ],
)
def test_exactly_one_file(files):
    with TestClient(app, raise_server_exceptions=False) as client:
        result = client.post("/api/v1/documents/extract", files=files)
    assert result.status_code == 422
    assert "error" in result.json()
