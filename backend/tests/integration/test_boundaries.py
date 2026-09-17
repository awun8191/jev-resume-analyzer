import asyncio
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_gateway, get_settings
from app.main import app
from app.middleware import RequestBoundary
from tests.integration.test_documents import pdf_bytes


@pytest.mark.parametrize('url,method', [('/missing', 'get'), ('/api/v1/health', 'delete')])
def test_http_errors_enveloped(url, method):
    with TestClient(app, raise_server_exceptions=False) as client:
        result = getattr(client, method)(url)
    assert set(result.json()) == {'error', 'request_id'}


def test_no_provider_for_health_or_extraction():
    def forbidden():
        raise AssertionError('Provider dependency must not be resolved')
    app.dependency_overrides[get_gateway] = forbidden
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            assert client.get('/api/v1/health').status_code == 200
            response = client.post('/api/v1/documents/extract',
                                   files={'file': ('a.pdf', pdf_bytes())})
            assert response.status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_internal_error_does_not_escape_or_log(caplog):
    class BrokenGateway:
        async def evaluate(self, *args):
            raise RuntimeError('PRIVATE_EXCEPTION_MARKER')
    app.dependency_overrides[get_gateway] = BrokenGateway
    try:
        # True means this fails if the server re-raises after building a safe response.
        with TestClient(app, raise_server_exceptions=True) as client:
            result = client.post('/api/v1/analyses',
                                 json={'mode': 'review', 'cv_text': 'synthetic'})
        assert result.status_code == 500
        assert 'PRIVATE_EXCEPTION_MARKER' not in result.text + caplog.text
    finally:
        app.dependency_overrides.clear()


def test_surrogate_text_rejected():
    with TestClient(app, raise_server_exceptions=False) as client:
        result = client.post('/api/v1/analyses', content=
            b'{"mode":"review","cv_text":"\\ud800"}',
            headers={'content-type': 'application/json'})
    assert result.status_code == 422


def test_parser_timeout():
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, parser_timeout_seconds=0.00001)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            result = client.post('/api/v1/documents/extract',
                                 files={'file': ('a.pdf', pdf_bytes())})
        assert result.status_code == 422
        assert result.json()['error']['code'] == 'PARSER_TIMEOUT'
    finally:
        app.dependency_overrides.clear()


def test_page_limit():
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, max_extracted_chars=2)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            result = client.post('/api/v1/documents/extract',
                                 files={'file': ('a.pdf', pdf_bytes())})
        assert result.status_code == 413
    finally:
        app.dependency_overrides.clear()


def test_xml_entities_rejected():
    data = BytesIO()
    with ZipFile(data, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
        archive.writestr('word/document.xml',
            '<!DOCTYPE x [<!ENTITY example "synthetic">]><document>&example;</document>')
    with TestClient(app, raise_server_exceptions=False) as client:
        result = client.post('/api/v1/documents/extract',
                             files={'file': ('a.docx', data.getvalue())})
    assert result.status_code == 422


def test_capacity_limit():
    async def forbidden(*args):
        raise AssertionError('Must reject before downstream')
    boundary = RequestBoundary(forbidden)
    boundary.active = 2
    messages = []
    async def receive():
        return {'type': 'http.request', 'body': b'', 'more_body': False}
    async def send(message):
        messages.append(message)
    asyncio.run(boundary({'type': 'http', 'method': 'POST', 'path': '/api/v1/analyses',
                          'headers': []}, receive, send))
    assert messages[0]['status'] == 429
