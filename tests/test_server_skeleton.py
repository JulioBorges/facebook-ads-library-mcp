"""Tests for project skeleton, settings, exceptions, and server health check."""

import pytest
from starlette.testclient import TestClient

from app.config import load_settings, read_secret
from app.exceptions import (
    MetaAPIError,
    format_error_response,
    generate_correlation_id,
)
from app.server import app


def test_read_secret_from_env(monkeypatch):
    monkeypatch.setenv("MY_TEST_SECRET", "secret_value_123")
    assert read_secret(env_name="MY_TEST_SECRET") == "secret_value_123"


def test_read_secret_from_file(tmp_path):
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("file_secret_456\n")
    assert read_secret(file_path=str(secret_file)) == "file_secret_456"


def test_read_secret_precedence(tmp_path, monkeypatch):
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("file_secret_priority\n")
    monkeypatch.setenv("MY_TEST_SECRET", "env_secret")
    assert (
        read_secret(file_path=str(secret_file), env_name="MY_TEST_SECRET") == "file_secret_priority"
    )


def test_load_settings(monkeypatch):
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "fb-token-123")
    monkeypatch.setenv("META_GRAPH_API_VERSION", "v26.0")
    monkeypatch.setenv("MAX_CAMPAIGN_BUDGET", "25.50")
    settings = load_settings()
    assert settings.facebook_access_token == "fb-token-123"
    assert settings.meta_graph_api_version == "v26.0"
    assert settings.max_campaign_budget == 25.50


def test_settings_validation_http(monkeypatch):
    monkeypatch.setenv("MCP_TRANSPORT", "http")
    monkeypatch.delenv("MCP_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "fb-token")
    monkeypatch.setenv("META_GRAPH_API_VERSION", "v26.0")
    settings = load_settings()
    with pytest.raises(ValueError, match="MCP_AUTH_TOKEN is required"):
        settings.validate_for_startup()


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_exceptions_format():
    corr_id = generate_correlation_id()
    assert len(corr_id) == 16

    err = MetaAPIError("Graph API failed", correlation_id=corr_id)
    resp = err.to_dict()
    assert resp["success"] is False
    assert resp["error"]["code"] == "META_API_ERROR"
    assert resp["error"]["message"] == "Graph API failed"
    assert resp["error"]["correlation_id"] == corr_id

    formatted = format_error_response("CUSTOM_ERR", "custom msg", corr_id)
    assert formatted["error"]["code"] == "CUSTOM_ERR"
