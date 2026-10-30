from fastapi.testclient import TestClient

from app.main import DEFAULT_ALLOWED_ORIGINS, allowed_origins, app

ALLOWED = "http://127.0.0.1:5273"
UNKNOWN = "https://evil.example"


def test_parse_default_origins():
    assert allowed_origins() == ["http://127.0.0.1:5273", "http://localhost:5273"]
    assert allowed_origins(None) == allowed_origins(DEFAULT_ALLOWED_ORIGINS)


def test_parse_strips_spaces_and_trailing_slashes():
    assert allowed_origins(" https://a.example/ , https://b.example ,,") == [
        "https://a.example",
        "https://b.example",
    ]


def test_parse_empty_value_allows_nothing():
    assert allowed_origins("") == []
    assert allowed_origins("  ,  ") == []


def test_allowed_origin_gets_the_cors_header():
    with TestClient(app) as client:
        result = client.get("/api/v1/health", headers={"Origin": ALLOWED})
    assert result.status_code == 200
    assert result.headers["access-control-allow-origin"] == ALLOWED
    assert "access-control-allow-credentials" not in result.headers


def test_unknown_origin_gets_no_cors_header():
    with TestClient(app) as client:
        result = client.get("/api/v1/health", headers={"Origin": UNKNOWN})
    assert result.status_code == 200
    assert "access-control-allow-origin" not in result.headers


def test_request_without_origin_gets_no_cors_header():
    with TestClient(app) as client:
        result = client.get("/api/v1/health")
    assert result.status_code == 200
    assert "access-control-allow-origin" not in result.headers


def test_preflight_for_an_allowed_origin():
    with TestClient(app) as client:
        result = client.options(
            "/api/v1/documents/extract",
            headers={
                "Origin": ALLOWED,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
    assert result.status_code == 200
    assert result.headers["access-control-allow-origin"] == ALLOWED
    assert "POST" in result.headers["access-control-allow-methods"]
    assert "content-type" in result.headers["access-control-allow-headers"].lower()


def test_preflight_rejects_an_unknown_origin():
    with TestClient(app) as client:
        result = client.options(
            "/api/v1/documents/extract",
            headers={"Origin": UNKNOWN, "Access-Control-Request-Method": "POST"},
        )
    assert result.status_code == 400
    assert "access-control-allow-origin" not in result.headers


def test_preflight_rejects_a_method_outside_the_allow_list():
    with TestClient(app) as client:
        result = client.options(
            "/api/v1/documents/extract",
            headers={"Origin": ALLOWED, "Access-Control-Request-Method": "DELETE"},
        )
    # Starlette answers 400 and the browser refuses the call; DELETE is never granted.
    assert result.status_code == 400
    assert "DELETE" not in result.headers.get("access-control-allow-methods", "")
