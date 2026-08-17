"""Competitive analysis tools for Facebook Ads."""

from typing import Any

from app.exceptions import (
    InvalidInputError,
    MCPBaseException,
    format_error_response,
    generate_correlation_id,
)
from app.security.redaction import sanitize_for_output
from app.security.response_limits import MAX_BRANDS_COMPARISON, enforce_response_limits
from app.security.validation import validate_brand_name, validate_limit
from app.tools.search import get_ads_service


def discover_competitor_brands(
    industry_keywords: str,
    region: str = "BR",
    min_ads: int = 5,
    limit: int = 100,
) -> dict[str, Any]:
    """Discover competitor brands running ads in a given industry or keyword.

    Parameters:
        industry_keywords: Industry keywords or category search term (1..200 characters)
        region: Two-letter ISO country code (e.g. 'BR', 'US'). Default 'BR' (Q32).
        min_ads: Minimum number of ads to qualify as an active competitor (default 5).
        limit: Maximum number of competitors to return (1..100). Default 100.
    """
    correlation_id = generate_correlation_id()
    try:
        if min_ads < 1:
            raise InvalidInputError("min_ads must be at least 1")
        valid_limit = validate_limit(limit, min_val=1, max_val=100)

        service = get_ads_service()
        result = service.discover_competitors(
            industry_keywords=industry_keywords,
            region=region,
            min_ads=min_ads,
            limit=valid_limit,
        )
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
            message=f"Competitor discovery failed: {exc!s}",
            correlation_id=correlation_id,
        )


def competitive_ad_analysis(
    brands_list: list[str],
) -> dict[str, Any]:
    """Analyze and compare ads across multiple competitor brands (up to 10 brands).

    Parameters:
        brands_list: List of brand names to compare (max 10, duplicates removed).
    """
    correlation_id = generate_correlation_id()
    try:
        if not isinstance(brands_list, list) or not brands_list:
            raise InvalidInputError("brands_list must be a non-empty list of strings")

        # Deduplicate and validate brand names
        cleaned_brands: list[str] = []
        for b in brands_list:
            if not isinstance(b, str):
                continue
            name = b.strip()
            if name and name not in cleaned_brands:
                cleaned_brands.append(validate_brand_name(name))

        if not cleaned_brands:
            raise InvalidInputError("brands_list does not contain any valid brand names")

        if len(cleaned_brands) > MAX_BRANDS_COMPARISON:
            cleaned_brands = cleaned_brands[:MAX_BRANDS_COMPARISON]

        service = get_ads_service()
        comparison_results: list[dict[str, Any]] = []
        platform_overlap: dict[str, set[str]] = {}

        for brand in cleaned_brands:
            search_res = service.search_ads(brand_name=brand, limit=50)
            ads = search_res.get("ads", [])

            platforms = set()
            for ad in ads:
                for p in ad.get("publisher_platforms", []):
                    platforms.add(p)

            platform_overlap[brand] = platforms

            comparison_results.append(
                {
                    "brand_name": brand,
                    "total_active_ads": len(ads),
                    "platforms_used": sorted(platforms),
                    "sample_creatives": [
                        {
                            "id": ad.get("id"),
                            "public_ad_url": ad.get("public_ad_url"),
                            "creative_bodies": ad.get("ad_creative_bodies", [])[:2],
                        }
                        for ad in ads[:3]
                    ],
                }
            )

        # Calculate shared platforms
        all_platforms = set().union(*platform_overlap.values()) if platform_overlap else set()

        response_data = {
            "brands_analyzed": cleaned_brands,
            "total_brands": len(cleaned_brands),
            "all_active_platforms": sorted(all_platforms),
            "comparison": comparison_results,
            "success": True,
        }

        return enforce_response_limits(sanitize_for_output(response_data))

    except MCPBaseException as exc:
        return format_error_response(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
        )
    except Exception as exc:  # noqa: BLE001
        return format_error_response(
            code="META_API_ERROR",
            message=f"Competitive ad analysis failed: {exc!s}",
            correlation_id=correlation_id,
        )
