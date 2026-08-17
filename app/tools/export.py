"""Export tools for formatting Facebook Ads data in JSON, CSV, and Markdown."""

import csv
import io
import json
from typing import Any

from app.exceptions import (
    InvalidInputError,
    MCPBaseException,
    format_error_response,
    generate_correlation_id,
)
from app.security.redaction import sanitize_for_output
from app.security.response_limits import enforce_response_limits
from app.security.validation import EXPORT_FORMAT_ALLOWED, validate_brand_name, validate_limit
from app.tools.search import get_ads_service

DANGEROUS_CSV_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(value: Any) -> str:
    """Sanitize CSV cell content against formula injection attacks (SEC-017)."""
    if value is None:
        return ""
    text = str(value)
    if text.startswith(DANGEROUS_CSV_PREFIXES):
        return f"'{text}"
    return text.strip()


def _generate_csv(ads: list[dict[str, Any]]) -> str:
    """Generate CSV string with formula injection escaping."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    headers = [
        "Ad ID",
        "Page Name",
        "Creation Date",
        "Publisher Platforms",
        "Headlines",
        "Bodies",
        "Public URL",
    ]
    writer.writerow(headers)

    for ad in ads:
        row = [
            sanitize_csv_cell(ad.get("id")),
            sanitize_csv_cell(ad.get("page_name")),
            sanitize_csv_cell(ad.get("ad_creation_time")),
            sanitize_csv_cell(", ".join(ad.get("publisher_platforms") or [])),
            sanitize_csv_cell(" | ".join(ad.get("ad_creative_link_titles") or [])),
            sanitize_csv_cell(" | ".join(ad.get("ad_creative_bodies") or [])),
            sanitize_csv_cell(ad.get("public_ad_url")),
        ]
        writer.writerow(row)

    return output.getvalue()


def _generate_markdown(brand_name: str, ads: list[dict[str, Any]]) -> str:
    """Generate structured Markdown summary and table."""
    lines: list[str] = [
        f"# Facebook Ads Export — {brand_name}",
        "",
        f"**Total Records Exported:** {len(ads)}",
        "",
        "| Ad ID | Page | Platforms | Creation Date | Public Link |",
        "|---|---|---|---|---|",
    ]

    for ad in ads:
        ad_id = str(ad.get("id", "N/A")).replace("|", "\\|")
        page = str(ad.get("page_name", "N/A")).replace("|", "\\|")
        platforms = ", ".join(ad.get("publisher_platforms") or []).replace("|", "\\|")
        creation = str(ad.get("ad_creation_time", "N/A")).replace("|", "\\|")
        public_url = str(ad.get("public_ad_url", ""))
        link_md = f"[View Ad]({public_url})" if public_url else "N/A"

        lines.append(f"| {ad_id} | {page} | {platforms} | {creation} | {link_md} |")

    return "\n".join(lines)


def export_facebook_ads_data(
    brand_name: str,
    export_format: str = "json",
    limit: int = 100,
) -> dict[str, Any]:
    """Export Facebook Ads data for a brand in JSON, CSV, or Markdown format.

    Parameters:
        brand_name: Name of the brand (1..200 characters)
        export_format: Output format ('json', 'csv', 'markdown'). Default 'json'.
        limit: Maximum number of ad records to export (1..100). Default 100.
    """
    correlation_id = generate_correlation_id()
    try:
        valid_brand = validate_brand_name(brand_name)
        fmt = export_format.lower().strip()
        if fmt not in EXPORT_FORMAT_ALLOWED:
            raise InvalidInputError(
                f"Invalid export_format '{export_format}'. Allowed: {sorted(EXPORT_FORMAT_ALLOWED)}"
            )
        valid_limit = validate_limit(limit, min_val=1, max_val=100)

        service = get_ads_service()
        search_res = service.search_ads(brand_name=valid_brand, limit=valid_limit)
        ads = search_res.get("ads", [])

        if fmt == "json":
            exported_content: Any = ads
        elif fmt == "csv":
            exported_content = _generate_csv(ads)
        elif fmt == "markdown":
            exported_content = _generate_markdown(valid_brand, ads)
        else:
            exported_content = json.dumps(ads)

        result = {
            "brand_name": valid_brand,
            "export_format": fmt,
            "total_records": len(ads),
            "data": exported_content,
            "success": True,
        }

        return enforce_response_limits(sanitize_for_output(result))

    except MCPBaseException as exc:
        return format_error_response(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
        )
    except Exception as exc:  # noqa: BLE001
        return format_error_response(
            code="META_API_ERROR",
            message=f"Export failed: {exc!s}",
            correlation_id=correlation_id,
        )
