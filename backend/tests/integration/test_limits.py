from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.dependencies import get_settings
from app.main import app
from app.middleware import MAX_UPLOAD_BYTES, MULTIPART_OVERHEAD_BYTES

BOUNDARY = MAX_UPLOAD_BYTES + MULTIPART_OVERHEAD_BYTES


def test_request_body_limit():
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/v1/documents/extract", content=b"x" * (BOUNDARY + 1))
        assert response.status_code == 413
        assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
    finally:
        app.dependency_overrides.clear()


def test_body_at_the_boundary_is_not_rejected_for_size():
    # The boundary admits exactly its limit; the route then rejects the shape, not the size.
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post("/api/v1/documents/extract", content=b"x" * BOUNDARY)
        assert response.status_code != 413
    finally:
        app.dependency_overrides.clear()


def test_upload_cap_stays_under_the_platform_body_limit():
    settings = Settings(_env_file=None)
    assert settings.max_upload_bytes == MAX_UPLOAD_BYTES == 4000000
    assert BOUNDARY < 4_500_000
    with pytest.raises(ValidationError):
        Settings(_env_file=None, max_upload_bytes=4000001)


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
