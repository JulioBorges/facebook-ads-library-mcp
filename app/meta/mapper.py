"""Mapper for transforming raw Meta API payloads into SafeAd DTOs."""

from typing import Any

from app.meta.schemas import SafeAd
from app.security.url_policy import build_public_ad_url


def _ensure_string_list(val: Any) -> list[str]:
    """Ensure value is converted to a list of strings."""
    if not val:
        return []
    if isinstance(val, list):
        return [str(item) for item in val if item is not None]
    if isinstance(val, str):
        return [val]
    return [str(val)]


def map_raw_ad_to_safe_ad(raw: dict[str, Any]) -> SafeAd:
    """Map raw Meta ad dict to SafeAd using strict allowlist mapping (SEC-003, SEC-004, Q37, Q40)."""
    ad_id = str(raw.get("id", "")).strip()
    if not ad_id:
        ad_id = "unknown"

    return SafeAd(
        id=ad_id,
        page_id=str(raw["page_id"]) if raw.get("page_id") is not None else None,
        page_name=str(raw["page_name"]) if raw.get("page_name") is not None else None,
        ad_creation_time=str(raw["ad_creation_time"]) if raw.get("ad_creation_time") else None,
        ad_creative_bodies=_ensure_string_list(raw.get("ad_creative_bodies")),
        ad_creative_link_captions=_ensure_string_list(raw.get("ad_creative_link_captions")),
        ad_creative_link_descriptions=_ensure_string_list(raw.get("ad_creative_link_descriptions")),
        ad_creative_link_titles=_ensure_string_list(raw.get("ad_creative_link_titles")),
        publisher_platforms=_ensure_string_list(raw.get("publisher_platforms")),
        currency=str(raw["currency"]) if raw.get("currency") else None,
        impressions=raw.get("impressions") if isinstance(raw.get("impressions"), dict) else None,
        spend=raw.get("spend") if isinstance(raw.get("spend"), dict) else None,
        public_ad_url=build_public_ad_url(ad_id),
        demographic_distribution=raw.get("demographic_distribution")
        if isinstance(raw.get("demographic_distribution"), list)
        else None,
        delivery_by_region=raw.get("delivery_by_region")
        if isinstance(raw.get("delivery_by_region"), list)
        else None,
        reach="not_available",
    )
