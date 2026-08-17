"""Performance analysis and intelligence reporting tools."""

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from app.exceptions import (
    InvalidInputError,
    MCPBaseException,
    format_error_response,
    generate_correlation_id,
)
from app.security.redaction import sanitize_for_output
from app.security.response_limits import enforce_response_limits
from app.security.validation import validate_brand_name
from app.tools.search import get_ads_service


def analyze_ad_performance_metrics(
    brand_name: str,
    time_period: int = 30,
) -> dict[str, Any]:
    """Analyze performance metrics and ad distribution for a brand across a specific time period.

    Parameters:
        brand_name: Name of the brand (1..200 characters)
        time_period: Analysis time window in days (>= 1, default 30). Filters via since/until dates (Q10).
    """
    correlation_id = generate_correlation_id()
    try:
        valid_brand = validate_brand_name(brand_name)
        if not isinstance(time_period, int) or time_period < 1:
            raise InvalidInputError("time_period must be an integer >= 1")

        # Calculate since and until dates (YYYY-MM-DD)
        now = datetime.now(UTC)
        since_date = (now - timedelta(days=time_period)).strftime("%Y-%m-%d")
        until_date = now.strftime("%Y-%m-%d")

        service = get_ads_service()
        search_res = service.search_ads(
            brand_name=valid_brand,
            limit=100,
            since=since_date,
            until=until_date,
        )

        ads = search_res.get("ads", [])
        total_ads = len(ads)

        # Platform distribution
        platform_counts: Counter[str] = Counter()
        spend_ranges: list[dict[str, Any]] = []
        impressions_ranges: list[dict[str, Any]] = []
        currencies: set[str] = set()

        for ad in ads:
            for p in ad.get("publisher_platforms", []):
                platform_counts[p] += 1
            if ad.get("spend"):
                spend_ranges.append(ad["spend"])
            if ad.get("impressions"):
                impressions_ranges.append(ad["impressions"])
            if ad.get("currency"):
                currencies.add(ad["currency"])

        summary = {
            "brand_name": valid_brand,
            "time_period_days": time_period,
            "date_range": {"since": since_date, "until": until_date},
            "total_ads_analyzed": total_ads,
            "platform_distribution": dict(platform_counts),
            "currencies_found": sorted(currencies),
            "spend_data_points": len(spend_ranges),
            "impressions_data_points": len(impressions_ranges),
            "success": True,
        }

        return enforce_response_limits(sanitize_for_output(summary))

    except MCPBaseException as exc:
        return format_error_response(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
        )
    except Exception as exc:  # noqa: BLE001
        return format_error_response(
            code="META_API_ERROR",
            message=f"Performance metrics analysis failed: {exc!s}",
            correlation_id=correlation_id,
        )


def generate_facebook_intelligence_report(
    brand_name: str,
    include_competitors: bool = True,
) -> dict[str, Any]:
    """Generate comprehensive intelligence report for a brand with optional competitor landscape.

    Parameters:
        brand_name: Name of the brand (1..200 characters)
        include_competitors: Whether to search and include competitor brands in the report (default True).
    """
    correlation_id = generate_correlation_id()
    try:
        valid_brand = validate_brand_name(brand_name)
        service = get_ads_service()

        # Fetch brand ads
        brand_ads_res = service.search_ads(brand_name=valid_brand, limit=50)
        ads = brand_ads_res.get("ads", [])

        # Aggregate platforms and sample creative messaging
        platforms: Counter[str] = Counter()
        top_headlines: list[str] = []
        top_bodies: list[str] = []

        for ad in ads:
            for p in ad.get("publisher_platforms", []):
                platforms[p] += 1
            for title in ad.get("ad_creative_link_titles", []):
                if title and title not in top_headlines and len(top_headlines) < 5:
                    top_headlines.append(title)
            for body in ad.get("ad_creative_bodies", []):
                if body and body not in top_bodies and len(top_bodies) < 5:
                    top_bodies.append(body)

        report: dict[str, Any] = {
            "brand_name": valid_brand,
            "generated_at": datetime.now(UTC).isoformat(),
            "brand_profile": {
                "active_ads_count": len(ads),
                "platform_distribution": dict(platforms),
                "sample_headlines": top_headlines,
                "sample_copies": top_bodies,
            },
            "success": True,
        }

        if include_competitors:
            comp_res = service.discover_competitors(
                industry_keywords=valid_brand,
                region="BR",
                min_ads=2,
                limit=10,
            )
            report["competitor_landscape"] = comp_res.get("competitors", [])

        return enforce_response_limits(sanitize_for_output(report))

    except MCPBaseException as exc:
        return format_error_response(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
        )
    except Exception as exc:  # noqa: BLE001
        return format_error_response(
            code="META_API_ERROR",
            message=f"Report generation failed: {exc!s}",
            correlation_id=correlation_id,
        )
