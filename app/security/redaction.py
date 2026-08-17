"""Global redaction and data sanitization routines."""

import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

SENSITIVE_KEYS = {
    "access_token",
    "authorization",
    "token",
    "api_key",
    "apikey",
    "client_secret",
    "secret",
    "password",
    "cookie",
    "set-cookie",
    "cloudinary_api_key",
    "cloudinary_api_secret",
    "cloud_name",
    "mcp_auth_token",
    "bearer",
}

# Regex to detect bearer tokens or raw Facebook access tokens (e.g. EAAB... or TEST_FAKE...)
BEARER_TOKEN_PATTERN = re.compile(r"(?i)(bearer\s+)([a-zA-Z0-9_\-\.~]+)")
META_TOKEN_PATTERN = re.compile(r"EAA[A-Za-z0-9]+")
FAKE_TOKEN_PATTERN = re.compile(r"TEST_FAKE_TOKEN[A-Za-z0-9_]*")


def is_sensitive_key(key: str) -> bool:
    """Check if a dictionary key name represents a secret or credential."""
    cleaned = key.lower().replace("-", "_")
    if cleaned in SENSITIVE_KEYS:
        return True
    return any(sens in cleaned for sens in ["token", "secret", "password", "api_key", "auth"])


def sanitize_url(url_str: str) -> str:
    """Strip sensitive query parameters from URL strings."""
    if not isinstance(url_str, str) or not url_str.strip():
        return url_str
    try:
        parsed = urlparse(url_str.strip())
        if not parsed.query:
            return url_str

        query_params = parse_qsl(parsed.query, keep_blank_values=True)
        sanitized_params = []
        for k, v in query_params:
            if is_sensitive_key(k):
                sanitized_params.append((k, "[REDACTED]"))
            else:
                sanitized_params.append((k, v))

        new_query = urlencode(sanitized_params)
        return urlunparse(parsed._replace(query=new_query))
    except (ValueError, TypeError):
        return "[INVALID_URL]"


def sanitize_string(text: str) -> str:
    """Redact known secret patterns from arbitrary strings."""
    if not text:
        return text

    # Do not redact public Cloudinary media URLs
    if "res.cloudinary.com" in text:
        return text

    # Redact Bearer headers/strings
    text = BEARER_TOKEN_PATTERN.sub(r"\1[REDACTED]", text)
    text = META_TOKEN_PATTERN.sub("[REDACTED_META_TOKEN]", text)
    text = FAKE_TOKEN_PATTERN.sub("[REDACTED_TOKEN]", text)

    # Redact URLs containing sensitive query params
    if (
        "://" in text
        and any(k in text for k in ("token=", "key=", "secret=", "auth="))
        and text.startswith(("http://", "https://"))
    ):
        return sanitize_url(text)

    return text


def sanitize_for_output(data: Any) -> Any:
    """Recursively sanitize data structures for safe output to tools, callers, and logs."""
    if isinstance(data, dict):
        sanitized_dict: dict[str, Any] = {}
        for k, v in data.items():
            if is_sensitive_key(str(k)):
                sanitized_dict[k] = "[REDACTED]"
            else:
                sanitized_dict[k] = sanitize_for_output(v)
        return sanitized_dict

    if isinstance(data, list):
        return [sanitize_for_output(item) for item in data]

    if isinstance(data, tuple):
        return tuple(sanitize_for_output(item) for item in data)

    if isinstance(data, set):
        return {sanitize_for_output(item) for item in data}

    if isinstance(data, str):
        return sanitize_string(data)

    return data


def safe_log_value(val: Any) -> str:
    """Format and redact arbitrary values for safe structured logging."""
    sanitized = sanitize_for_output(val)
    return str(sanitized)
