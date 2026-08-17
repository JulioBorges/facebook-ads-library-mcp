"""Tests for export tools and CSV formula injection sanitization (SEC-017, Q12)."""

import responses

from app.tools.export import export_facebook_ads_data, sanitize_csv_cell


def test_sanitize_csv_cell():
    # Formula injection attempts
    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+cmd|' /C calc'!A0") == "'+cmd|' /C calc'!A0"
    assert sanitize_csv_cell("-2+3") == "'-2+3"
    assert sanitize_csv_cell("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_csv_cell("\tTab") == "'\tTab"
    assert sanitize_csv_cell("\rReturn") == "'\rReturn"

    # Normal text
    assert sanitize_csv_cell("Nike Official") == "Nike Official"
    assert sanitize_csv_cell("12345") == "12345"
    assert sanitize_csv_cell(None) == ""


@responses.activate
def test_export_facebook_ads_json(monkeypatch):
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "SAFE_TOKEN")
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={"data": [{"id": "1", "page_name": "Test Brand"}]},
        status=200,
    )

    res = export_facebook_ads_data(brand_name="Test Brand", export_format="json")
    assert res["success"] is True
    assert res["export_format"] == "json"
    assert res["total_records"] == 1
    assert isinstance(res["data"], list)


@responses.activate
def test_export_facebook_ads_csv_injection_prevention(monkeypatch):
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "SAFE_TOKEN")
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={
            "data": [
                {
                    "id": "1",
                    "page_name": "=cmd|' /C calc'!A0",
                    "ad_creative_bodies": ["+SUM(A1:A10)"],
                }
            ]
        },
        status=200,
    )

    res = export_facebook_ads_data(brand_name="InjectedBrand", export_format="csv")
    assert res["success"] is True
    csv_content = res["data"]
    assert "'=cmd|" in csv_content
    assert "'+SUM" in csv_content


@responses.activate
def test_export_facebook_ads_markdown(monkeypatch):
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "SAFE_TOKEN")
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={"data": [{"id": "101", "page_name": "MD Brand"}]},
        status=200,
    )

    res = export_facebook_ads_data(brand_name="MD Brand", export_format="markdown")
    assert res["success"] is True
    md = res["data"]
    assert "# Facebook Ads Export — MD Brand" in md
    assert "| 101 | MD Brand |" in md


def test_export_invalid_format():
    res = export_facebook_ads_data(brand_name="Brand", export_format="xml")
    assert res["success"] is False
    assert res["error"]["code"] == "INVALID_INPUT"
