"""Search tools for Facebook Ads Library."""

from typing import Any

from app.config import load_settings
from app.exceptions import MCPBaseException, format_error_response, generate_correlation_id
from app.meta.client import MetaAdsClient
from app.meta.service import AdsService
from app.security.redaction import sanitize_for_output


def get_ads_service() -> AdsService:
    """Instantiate AdsService with runtime settings."""
    settings = load_settings()
    client = MetaAdsClient(
        access_token=settings.facebook_access_token or "",
        graph_api_version=settings.meta_graph_api_version,
        connect_timeout=settings.http_connect_timeout,
        read_timeout=settings.http_read_timeout,
    )
    return AdsService(client=client)


def search_facebook_ads(
    brand_name: str,
    country: str = "BR",
    ad_type: str = "ALL",
    limit: int = 50,
) -> dict[str, Any]:
    """Search Facebook Ads Library for a specific brand or keyword.

    Parameters:
        brand_name: Name of the brand or search keywords (1..200 characters)
        country: Two-letter ISO country code (e.g. 'BR', 'US'). Default 'BR' (Q32).
        ad_type: Ad category filter ('ALL', 'POLITICAL_AND_ISSUE_ADS', 'HOUSING', 'EMPLOYMENT', 'CREDIT'). Default 'ALL'.
        limit: Number of ads to return (1..100). Default 50.
    """
    correlation_id = generate_correlation_id()
    try:
        service = get_ads_service()
        result = service.search_ads(
            brand_name=brand_name,
            country=country,
            ad_type=ad_type,
            limit=limit,
        )
        return sanitize_for_output(result)
    except MCPBaseException as exc:
        return format_error_response(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
        )
    except Exception as exc:  # noqa: BLE001
        return format_error_response(
            code="META_API_ERROR",
            message=f"Search operation failed: {exc!s}",
            correlation_id=correlation_id,
        )
