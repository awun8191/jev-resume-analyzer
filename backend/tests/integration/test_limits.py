from io import BytesIO
from zipfile import ZipFile

from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_settings
from app.main import app


def test_request_body_limit():
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/v1/documents/extract", content=b"x" * 11000000)
        assert response.status_code == 413
    finally:
        app.dependency_overrides.clear()


def test_docx_total_uncompressed_limit():
    data = BytesIO()
    with ZipFile(data, "w") as z:
        z.writestr("word/document.xml", "<document/>")
        z.writestr("large.bin", b"x" * 1000)
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, max_docx_uncompressed_bytes=500
    )
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/documents/extract", files={"file": ("x.docx", data.getvalue())}
            )
        assert response.status_code == 413
    finally:
        app.dependency_overrides.clear()
