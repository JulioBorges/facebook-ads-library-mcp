"""Strict URL policy and URL construction utilities."""

from urllib.parse import urlparse

from app.exceptions import InvalidInputError

ALLOWED_FACEBOOK_HOSTS = {"facebook.com", "www.facebook.com"}


def build_public_ad_url(ad_id: str) -> str:
    """Build public Facebook Ads Library URL exclusively from sanitized ad_id."""
    return f"https://www.facebook.com/ads/library/?id={ad_id}"


def is_safe_facebook_url(url: str) -> bool:
    """Validate that a URL is an HTTPS URL pointing strictly to Facebook."""
    if not isinstance(url, str) or not url.strip():
        return False
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme.lower() != "https":
            return False
        host = (parsed.hostname or "").lower()
        if host not in ALLOWED_FACEBOOK_HOSTS:
            return False
        # Block embedded credentials
        return not (parsed.username or parsed.password)
    except (ValueError, TypeError):
        return False


def is_safe_destination_url(url: str) -> bool:
    """Validate that a campaign link destination is HTTPS and well-formed (without making any network call)."""
    if not isinstance(url, str) or not url.strip():
        return False
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme.lower() != "https":
            return False
        if not parsed.netloc or not parsed.hostname:
            return False
        return not (parsed.username or parsed.password)
    except (ValueError, TypeError):
        return False


def validate_destination_url(url: str) -> str:
    """Validate and return safe destination URL or raise InvalidInputError."""
    if not is_safe_destination_url(url):
        raise InvalidInputError(
            f"Invalid destination URL '{url}'. Must be a valid HTTPS URL without embedded credentials."
        )
    return url.strip()
