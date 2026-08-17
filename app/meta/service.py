"""AdsService: Business logic layer orchestrating Meta Ads queries and transformations."""

from collections import defaultdict
from typing import Any

from app.meta.client import MetaAdsClient
from app.meta.mapper import map_raw_ad_to_safe_ad
from app.security.validation import (
    validate_ad_type,
    validate_brand_name,
    validate_country_code,
    validate_limit,
)


class AdsService:
    """Service layer for searching, discovering, and analyzing ads."""

    def __init__(self, client: MetaAdsClient):
        self.client = client

    def search_ads(
        self,
        brand_name: str,
        country: str = "BR",
        ad_type: str = "ALL",
        limit: int = 50,
        since: str | None = None,
        until: str | None = None,
    ) -> dict[str, Any]:
        """Search ads by brand name or keyword and return sanitized SafeAd models."""
        valid_brand = validate_brand_name(brand_name)
        valid_country = validate_country_code(country)
        valid_ad_type = validate_ad_type(ad_type)
        valid_limit = validate_limit(limit, min_val=1, max_val=100)

        response = self.client.search_ads(
            search_terms=valid_brand,
            country=valid_country,
            ad_type=valid_ad_type,
            limit=valid_limit,
            since=since,
            until=until,
        )

        raw_data = response.get("data", [])
        safe_ads = [map_raw_ad_to_safe_ad(item) for item in raw_data if isinstance(item, dict)]

        # Construct sanitized search params (SEC-001, §6)
        safe_search_params = {
            "search_terms": valid_brand,
            "country": valid_country,
            "ad_type": valid_ad_type,
            "limit": valid_limit,
        }
        if since:
            safe_search_params["since"] = since
        if until:
            safe_search_params["until"] = until

        return {
            "total_results": len(safe_ads),
            "search_params": safe_search_params,
            "ads": [ad.model_dump() for ad in safe_ads],
            "success": True,
        }

    def discover_competitors(
        self,
        industry_keywords: str,
        region: str = "BR",
        min_ads: int = 5,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Discover competitor brands by keywords using cursor pagination without limit*3 hack (Q9)."""
        valid_keywords = validate_brand_name(industry_keywords)
        valid_region = validate_country_code(region)
        valid_limit = validate_limit(limit, min_val=1, max_val=100)

        # Collect ads safely via cursor pagination
        raw_ads = self.client.fetch_all_ads_paginated(
            search_terms=valid_keywords,
            country=valid_region,
            ad_type="ALL",
            max_results=max(valid_limit * 5, 200),
            page_size=50,
            max_pages=5,
        )

        brands_map: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "page_name": "",
                "page_id": "",
                "ad_count": 0,
                "sample_ads": [],
                "platforms": set(),
            }
        )

        for raw_ad in raw_ads:
            page_name = str(raw_ad.get("page_name") or "Unknown Brand").strip()
            page_id = str(raw_ad.get("page_id") or "")
            entry = brands_map[page_name]
            entry["page_name"] = page_name
            if page_id and not entry["page_id"]:
                entry["page_id"] = page_id
            entry["ad_count"] += 1

            platforms = raw_ad.get("publisher_platforms") or []
            if isinstance(platforms, list):
                for p in platforms:
                    entry["platforms"].add(str(p))

            if len(entry["sample_ads"]) < 3:
                safe_ad = map_raw_ad_to_safe_ad(raw_ad)
                entry["sample_ads"].append(safe_ad.model_dump())

        # Filter by min_ads and sort descending by ad_count
        competitors = []
        for brand_info in brands_map.values():
            if brand_info["ad_count"] >= min_ads:
                competitors.append(
                    {
                        "brand_name": brand_info["page_name"],
                        "page_id": brand_info["page_id"],
                        "total_ads_found": brand_info["ad_count"],
                        "active_platforms": sorted(brand_info["platforms"]),
                        "sample_ads": brand_info["sample_ads"],
                    }
                )

        competitors.sort(key=lambda x: x["total_ads_found"], reverse=True)
        final_competitors = competitors[:valid_limit]

        return {
            "industry_keywords": valid_keywords,
            "region": valid_region,
            "min_ads_filter": min_ads,
            "total_competitors_found": len(final_competitors),
            "competitors": final_competitors,
            "success": True,
        }
