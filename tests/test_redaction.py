"""Unit tests for global redaction and sanitization."""

from app.security.redaction import (
    is_sensitive_key,
    safe_log_value,
    sanitize_for_output,
    sanitize_string,
    sanitize_url,
)


def test_is_sensitive_key():
    assert is_sensitive_key("access_token") is True
    assert is_sensitive_key("Authorization") is True
    assert is_sensitive_key("FACEBOOK_ACCESS_TOKEN") is True
    assert is_sensitive_key("cloudinary_api_secret") is True
    assert is_sensitive_key("mcp_auth_token") is True
    assert is_sensitive_key("brand_name") is False
    assert is_sensitive_key("public_url") is False


def test_sanitize_url():
    raw_url = "https://graph.facebook.com/v26.0/ads_archive?access_token=EAAB123456&search_terms=Nike&token=secret"
    sanitized = sanitize_url(raw_url)
    assert "EAAB123456" not in sanitized
    assert "secret" not in sanitized
    assert "access_token=%5BREDACTED%5D" in sanitized or "access_token=[REDACTED]" in sanitized
    assert "search_terms=Nike" in sanitized


def test_sanitize_string():
    text = "Authorization: Bearer my_secret_token_value and EAAB998877665544"
    sanitized = sanitize_string(text)
    assert "my_secret_token_value" not in sanitized
    assert "EAAB998877665544" not in sanitized
    assert "[REDACTED]" in sanitized


def test_preserve_cloudinary_public_url():
    cloudinary_url = "https://res.cloudinary.com/demo/image/upload/v1234567890/sample.jpg"
    assert sanitize_string(cloudinary_url) == cloudinary_url


def test_sanitize_for_output_dict():
    payload = {
        "access_token": "SUPER_SECRET_TOKEN",
        "api_key": "123456",
        "safe_data": "Hello World",
        "nested": {
            "token": "nested_secret",
            "count": 42,
            "url": "https://example.com/?token=secret123&q=test",
        },
        "list_data": [
            {"secret": "item_secret"},
            "Bearer secret_bearer_token",
        ],
    }
    cleaned = sanitize_for_output(payload)
    assert cleaned["access_token"] == "[REDACTED]"
    assert cleaned["api_key"] == "[REDACTED]"
    assert cleaned["safe_data"] == "Hello World"
    assert cleaned["nested"]["token"] == "[REDACTED]"
    assert "secret123" not in str(cleaned["nested"]["url"])
    assert cleaned["list_data"][0]["secret"] == "[REDACTED]"
    assert "secret_bearer_token" not in cleaned["list_data"][1]


def test_safe_log_value():
    logged = safe_log_value({"client_secret": "xyz", "name": "test"})
    assert "xyz" not in logged
    assert "[REDACTED]" in logged
