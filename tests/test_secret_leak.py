"""Security test suite verifying zero secret leaks in outputs, errors, logs and parameters."""

import responses

from app.exceptions import MetaAPIError
from app.security.redaction import safe_log_value, sanitize_for_output
from app.tools.search import search_facebook_ads


@responses.activate
def test_no_token_leak_in_tool_output(monkeypatch):
    secret_token = "TEST_FAKE_TOKEN_DO_NOT_USE_123456"
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", secret_token)
    monkeypatch.setenv("META_GRAPH_API_VERSION", "v26.0")

    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={
            "data": [
                {
                    "id": "1001",
                    "page_name": "TestPage",
                    "ad_creative_bodies": ["Check our store"],
                }
            ]
        },
        status=200,
    )

    result = search_facebook_ads(brand_name="TestPage", country="BR")

    assert result["success"] is True
    output_str = str(result)
    assert secret_token not in output_str
    assert "access_token" not in result["search_params"]


@responses.activate
def test_no_token_leak_in_api_error_response(monkeypatch):
    secret_token = "TEST_FAKE_TOKEN_DO_NOT_USE_123456"
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", secret_token)

    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        status=400,
        json={"error": {"message": f"Invalid parameter with token {secret_token}"}},
    )

    result = search_facebook_ads(brand_name="ErrorBrand")

    assert result["success"] is False
    assert result["error"]["code"] == "META_API_ERROR"
    output_str = str(result)
    assert secret_token not in output_str


def test_no_token_leak_in_exceptions():
    secret = "TEST_FAKE_TOKEN_DO_NOT_USE_123456"
    err = MetaAPIError(f"Failed with {secret}")
    sanitized = sanitize_for_output(err.to_dict())

    assert secret not in str(sanitized)
    assert secret not in safe_log_value(err.to_dict())
