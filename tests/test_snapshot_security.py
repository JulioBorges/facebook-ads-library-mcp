"""Security tests verifying complete absence of ad_snapshot_url from all flows (SEC-004, Q40)."""

import responses

from app.meta.client import SEARCH_FIELDS
from app.meta.mapper import map_raw_ad_to_safe_ad
from app.meta.schemas import SafeAd
from app.tools.search import search_facebook_ads


def test_search_fields_excludes_ad_snapshot_url_and_reach():
    assert "ad_snapshot_url" not in SEARCH_FIELDS
    assert "reach" not in SEARCH_FIELDS


def test_safe_ad_model_has_no_snapshot_url():
    fields = SafeAd.model_fields.keys()
    assert "ad_snapshot_url" not in fields
    assert "snapshot_url" not in fields


def test_mapper_drops_ad_snapshot_url_if_present_in_meta_raw_data():
    raw_payload = {
        "id": "99999",
        "page_name": "Test Brand",
        "ad_snapshot_url": "https://www.facebook.com/ads/archive/render_ad/?id=99999&access_token=LEAKED",
        "ad_creative_bodies": ["Buy now"],
    }
    safe_ad = map_raw_ad_to_safe_ad(raw_payload)
    ad_dict = safe_ad.model_dump()

    assert "ad_snapshot_url" not in ad_dict
    assert "LEAKED" not in str(ad_dict)
    assert safe_ad.public_ad_url == "https://www.facebook.com/ads/library/?id=99999"


@responses.activate
def test_search_facebook_ads_tool_never_returns_snapshot_url(monkeypatch):
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "SAFE_TEST_TOKEN")
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={
            "data": [
                {
                    "id": "12345",
                    "page_name": "Brand",
                    "ad_snapshot_url": "https://facebook.com/snapshot?token=SHOULD_NEVER_EXIST",
                }
            ]
        },
        status=200,
    )

    result = search_facebook_ads(brand_name="Brand")
    assert result["success"] is True
    result_str = str(result)
    assert "ad_snapshot_url" not in result_str
    assert "SHOULD_NEVER_EXIST" not in result_str
