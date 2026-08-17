"""Tests for response limiting and Policy C payload enforcement (SEC-015/016, Q36)."""

import pytest

from app.exceptions import ResponseTooLargeError
from app.security.response_limits import (
    MAX_CREATIVE_TEXT_CHARS,
    enforce_response_limits,
)


def test_enforce_response_limits_truncates_long_text():
    oversized_text = "A" * (MAX_CREATIVE_TEXT_CHARS + 500)
    data = {
        "title": "Normal title",
        "ad_body": oversized_text,
        "nested": {"copy": oversized_text},
    }

    result = enforce_response_limits(data)
    assert result.get("truncated") is True
    assert len(result["ad_body"]) < len(oversized_text)
    assert result["ad_body"].endswith("...[TRUNCATED]")
    assert result["nested"]["copy"].endswith("...[TRUNCATED]")


def test_enforce_response_limits_raises_on_payload_over_1mb():
    # Construct a payload with many records that exceeds 1MB even after truncation
    huge_data = {
        "ads": [
            {"id": str(i), "text": "x" * 1000}
            for i in range(1200)  # ~1.2MB payload
        ]
    }

    with pytest.raises(ResponseTooLargeError, match="exceeds 1MB limit"):
        enforce_response_limits(huge_data)
