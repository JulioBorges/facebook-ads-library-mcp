"""Tests for competitive brand discovery, brand comparison, and performance reporting."""

import responses

from app.tools.competitive import competitive_ad_analysis, discover_competitor_brands
from app.tools.reporting import (
    analyze_ad_performance_metrics,
    generate_facebook_intelligence_report,
)


@responses.activate
def test_discover_competitor_brands_aggregates_and_filters(monkeypatch):
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "SAFE_TOKEN")
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={
            "data": [
                {
                    "id": "1",
                    "page_name": "Brand A",
                    "publisher_platforms": ["facebook", "instagram"],
                },
                {"id": "2", "page_name": "Brand A", "publisher_platforms": ["facebook"]},
                {"id": "3", "page_name": "Brand A", "publisher_platforms": ["instagram"]},
                {"id": "4", "page_name": "Brand B", "publisher_platforms": ["facebook"]},
            ]
        },
        status=200,
    )

    res = discover_competitor_brands(industry_keywords="fashion", region="BR", min_ads=2, limit=10)
    assert res["success"] is True
    assert res["total_competitors_found"] == 1
    assert res["competitors"][0]["brand_name"] == "Brand A"
    assert res["competitors"][0]["total_ads_found"] == 3


@responses.activate
def test_competitive_ad_analysis_multiple_brands(monkeypatch):
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "SAFE_TOKEN")
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={"data": [{"id": "10", "publisher_platforms": ["facebook"]}]},
        status=200,
    )
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={"data": [{"id": "20", "publisher_platforms": ["instagram"]}]},
        status=200,
    )

    res = competitive_ad_analysis(brands_list=["BrandOne", "BrandTwo"])
    assert res["success"] is True
    assert len(res["comparison"]) == 2
    assert res["total_brands"] == 2


@responses.activate
def test_analyze_ad_performance_metrics(monkeypatch):
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "SAFE_TOKEN")
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={
            "data": [
                {
                    "id": "100",
                    "publisher_platforms": ["facebook"],
                    "currency": "BRL",
                    "spend": {"lower_bound": "100", "upper_bound": "500"},
                    "impressions": {"lower_bound": "1000", "upper_bound": "5000"},
                }
            ]
        },
        status=200,
    )

    res = analyze_ad_performance_metrics(brand_name="TestBrand", time_period=15)
    assert res["success"] is True
    assert res["total_ads_analyzed"] == 1
    assert res["time_period_days"] == 15
    assert "date_range" in res
    assert res["platform_distribution"]["facebook"] == 1


@responses.activate
def test_generate_facebook_intelligence_report(monkeypatch):
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "SAFE_TOKEN")
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={
            "data": [
                {
                    "id": "500",
                    "publisher_platforms": ["facebook"],
                    "ad_creative_link_titles": ["Great Deals Today"],
                    "ad_creative_bodies": ["Shop our summer sale now"],
                }
            ]
        },
        status=200,
    )
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={"data": [{"id": "501", "page_name": "Rival Brand"}]},
        status=200,
    )

    res = generate_facebook_intelligence_report(brand_name="MainBrand", include_competitors=True)
    assert res["success"] is True
    assert res["brand_profile"]["active_ads_count"] == 1
    assert "Great Deals Today" in res["brand_profile"]["sample_headlines"]
