"""Tests for campaign, ad set, and ad management tools with dry-run and validation."""

import responses

from app.tools.management import create_ad, create_ad_set, create_campaign, list_ad_accounts


@responses.activate
def test_list_ad_accounts_tool(monkeypatch):
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "SAFE_TOKEN")
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/me/adaccounts",
        json={
            "data": [
                {
                    "account_id": "123456",
                    "name": "Ad Account",
                    "currency": "BRL",
                    "account_status": 1,
                }
            ]
        },
        status=200,
    )

    res = list_ad_accounts()
    assert res["success"] is True
    assert res["total_accounts"] == 1
    assert res["accounts"][0]["ad_account_id"] == "123456"


@responses.activate
def test_create_campaign_dry_run_and_real(monkeypatch):
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "SAFE_TOKEN")
    monkeypatch.setenv("MAX_CAMPAIGN_BUDGET", "10.00")

    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/me/adaccounts",
        json={"data": [{"account_id": "123456", "name": "Ad Account", "currency": "BRL"}]},
        status=200,
    )

    # 1. Dry Run (Default)
    dry_res = create_campaign(
        ad_account_id="123456",
        name="Summer Promo",
        objective="OUTCOME_SALES",
        daily_budget=8.50,
        dry_run=True,
    )
    assert dry_res["success"] is True
    assert dry_res["campaign"]["dry_run"] is True
    assert dry_res["campaign"]["status"] == "SIMULATED"
    assert dry_res["campaign"]["daily_budget_subunit"] == 850

    # 2. Real Execution (dry_run=False)
    responses.add(
        responses.POST,
        "https://graph.facebook.com/v26.0/act_123456/campaigns",
        json={"id": "camp_998877"},
        status=200,
    )

    real_res = create_campaign(
        ad_account_id="123456",
        name="Summer Promo Real",
        objective="OUTCOME_SALES",
        daily_budget=8.50,
        dry_run=False,
    )
    assert real_res["success"] is True
    assert real_res["campaign"]["dry_run"] is False
    assert real_res["campaign"]["id"] == "camp_998877"
    assert real_res["campaign"]["status"] == "PAUSED"


@responses.activate
def test_create_ad_set_dry_run_and_targeting(monkeypatch):
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "SAFE_TOKEN")
    # No `/me/adaccounts` mock: dry_run now validates the ad_account_id format
    # locally instead of hitting the live Meta API (see campaign_service.py
    # `_resolve_ad_account_id`), so a pure simulation call makes no HTTP request.

    res = create_ad_set(
        ad_account_id="123456",
        campaign_id="camp_1",
        name="Brazil Broad 18-45",
        countries=["BR"],
        age_min=18,
        age_max=45,
        genders=0,
        publisher_platforms=["facebook", "instagram"],
        daily_budget=5.00,
        dry_run=True,
    )
    assert res["success"] is True
    assert res["ad_set"]["targeting"]["geo_locations"]["countries"] == ["BR"]
    assert res["ad_set"]["targeting"]["age_max"] == 45
    assert res["ad_set"]["daily_budget_subunit"] == 500


@responses.activate
def test_create_ad_dry_run_and_cta_validation(monkeypatch):
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "SAFE_TOKEN")
    # No `/me/adaccounts` mock: both calls below are dry_run, which validates the
    # ad_account_id format locally instead of hitting the live Meta API.

    # Valid CTA
    res = create_ad(
        ad_account_id="123456",
        ad_set_id="adset_1",
        image_url="https://res.cloudinary.com/demo/image/upload/v1/creative.jpg",
        title="Exclusive Offer",
        body="Get 20% discount on all items today only.",
        link_url="https://mystore.com/summer-sale",
        call_to_action="SHOP_NOW",
        dry_run=True,
    )
    assert res["success"] is True
    assert res["ad"]["call_to_action"] == "SHOP_NOW"
    assert res["ad"]["link_url"] == "https://mystore.com/summer-sale"

    # Invalid CTA
    res_bad_cta = create_ad(
        ad_account_id="123456",
        ad_set_id="adset_1",
        image_url="https://res.cloudinary.com/demo/image/upload/v1/creative.jpg",
        title="Exclusive Offer",
        body="Text",
        link_url="https://mystore.com/summer-sale",
        call_to_action="INVALID_ACTION",
        dry_run=True,
    )
    assert res_bad_cta["success"] is False
    assert res_bad_cta["error"]["code"] == "INVALID_INPUT"
