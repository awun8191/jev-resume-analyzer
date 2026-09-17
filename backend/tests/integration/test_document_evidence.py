from io import BytesIO

from reportlab.pdfgen import canvas


def test_upload_preserves_layout_and_links():
    from fastapi.testclient import TestClient

    from app.main import app
    client = TestClient(app)
    output = BytesIO()
    page = canvas.Canvas(output, pagesize=(612, 792))
    page.setFont("Helvetica", 18)
    page.drawString(54, 738, "Synthetic Candidate")
    page.setFont("Helvetica", 11)
    page.drawString(54, 710, "Portfolio")
    page.linkURL("https://example.com/portfolio", (54, 708, 100, 723))
    page.save()
    response = client.post("/api/v1/documents/extract", files={
        "file": ("synthetic.pdf", output.getvalue(), "application/pdf")
    })
    assert response.status_code == 200, response.text
    evidence = response.json()["document_evidence"]
    assert evidence["pages"][0]["width_pt"] == 612
    assert evidence["links"][0]["target"] == "https://example.com/portfolio"
    assert evidence["links"][0]["label"] == "Portfolio"
    assert any(span["font_size_pt"] == 18 for span in evidence["spans"])
    assert evidence["pages"][0]["margin_kind"] == "estimated_content_whitespace"
    assert evidence["source_text_sha256"]
