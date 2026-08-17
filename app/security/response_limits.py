"""Response size limiting and payload truncation policies (Policy C, Q36)."""

import json
from typing import Any

from app.exceptions import ResponseTooLargeError

MAX_BRAND_NAME_CHARS = 200
MAX_SEARCH_RESULTS = 100
MAX_EXPORT_RECORDS = 250
MAX_BRANDS_COMPARISON = 10
MAX_CREATIVE_TEXT_CHARS = 20000
MAX_TOOL_RESPONSE_BYTES = 1000000  # 1MB byte limit


def _truncate_long_strings(data: Any) -> tuple[Any, bool]:
    """Recursively truncate strings exceeding MAX_CREATIVE_TEXT_CHARS."""
    was_truncated = False

    if isinstance(data, str):
        if len(data) > MAX_CREATIVE_TEXT_CHARS:
            return data[:MAX_CREATIVE_TEXT_CHARS] + " ...[TRUNCATED]", True
        return data, False

    if isinstance(data, dict):
        new_dict: dict[str, Any] = {}
        for k, v in data.items():
            new_v, trunc = _truncate_long_strings(v)
            if trunc:
                was_truncated = True
            new_dict[k] = new_v
        return new_dict, was_truncated

    if isinstance(data, list):
        new_list: list[Any] = []
        for item in data:
            new_item, trunc = _truncate_long_strings(item)
            if trunc:
                was_truncated = True
            new_list.append(new_item)
        return new_list, was_truncated

    return data, False


def enforce_response_limits(data: dict[str, Any]) -> dict[str, Any]:
    """Apply Policy C limits: truncate long text fields, verify <= 1MB, or raise ResponseTooLargeError (Q36)."""
    sanitized_data, was_truncated = _truncate_long_strings(data)

    if was_truncated and isinstance(sanitized_data, dict):
        sanitized_data["truncated"] = True

    try:
        serialized = json.dumps(sanitized_data, ensure_ascii=False)
        byte_size = len(serialized.encode("utf-8"))
        if byte_size > MAX_TOOL_RESPONSE_BYTES:
            raise ResponseTooLargeError(
                f"Response payload ({byte_size} bytes) exceeds 1MB limit. Please specify a smaller limit."
            )
    except TypeError:
        pass

    return sanitized_data
