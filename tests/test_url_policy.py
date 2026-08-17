"""Unit tests for strict URL policy and public ad URL generation."""

import pytest

from app.exceptions import InvalidInputError
from app.security.url_policy import (
    build_public_ad_url,
    is_safe_destination_url,
    is_safe_facebook_url,
    validate_destination_url,
)


def test_build_public_ad_url():
    url = build_public_ad_url("1234567890")
    assert url == "https://www.facebook.com/ads/library/?id=1234567890"


def test_is_safe_facebook_url():
    assert is_safe_facebook_url("https://www.facebook.com/ads/library/?id=123") is True
    assert is_safe_facebook_url("https://facebook.com/ads/library/?id=123") is True

    # Reject non-https
    assert is_safe_facebook_url("http://www.facebook.com/ads/library/?id=123") is False
    # Reject other domains
    assert is_safe_facebook_url("https://evil-facebook.com/ads/library/?id=123") is False
    assert is_safe_facebook_url("https://facebook.com.attacker.com/") is False
    # Reject embedded credentials
    assert is_safe_facebook_url("https://user:pass@www.facebook.com/ads") is False
    # Reject local/file schemes
    assert is_safe_facebook_url("file:///etc/passwd") is False
    assert is_safe_facebook_url("javascript:alert(1)") is False


def test_is_safe_destination_url():
    assert is_safe_destination_url("https://example.com/landing-page") is True
    assert is_safe_destination_url("https://subdomain.shop.com/product/123?ref=ad") is True

    # Reject http
    assert is_safe_destination_url("http://example.com") is False
    # Reject credentials
    assert is_safe_destination_url("https://admin:secret@example.com") is False
    # Reject empty or invalid
    assert is_safe_destination_url("") is False
    assert is_safe_destination_url("ftp://server/path") is False


def test_validate_destination_url():
    assert validate_destination_url("https://mybrand.com/promo") == "https://mybrand.com/promo"
    with pytest.raises(InvalidInputError):
        validate_destination_url("http://insecure.com")
