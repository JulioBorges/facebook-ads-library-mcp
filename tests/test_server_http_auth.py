"""Tests for HTTP transport Bearer authentication and health endpoint (Q4, Q33)."""

from starlette.testclient import TestClient

from app.server import app


def test_public_health_endpoint_without_auth():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_http_auth_missing_header_returns_401():
    with TestClient(app) as client:
        response = client.get("/mcp")
        assert response.status_code == 401
        assert "error" in response.json()


def test_http_auth_invalid_token_returns_403():
    with TestClient(app) as client:
        response = client.get("/mcp", headers={"Authorization": "Bearer wrong-token-12345"})
        assert response.status_code == 403
        assert "error" in response.json()


def test_http_auth_valid_token_passes_auth(monkeypatch):
    monkeypatch.setenv("MCP_AUTH_TOKEN", "valid-secret-token")
    from app.server import create_asgi_app

    authenticated_app = create_asgi_app()
    with TestClient(authenticated_app) as client:
        response = client.get("/mcp", headers={"Authorization": "Bearer valid-secret-token"})
        # It passes the auth middleware and reaches FastMCP HTTP session handler
        assert response.status_code != 401
        assert response.status_code != 403
