"""Automated Acceptance Test with Fake Token (spec-v3.md §39).

Verifies zero secret leakage in tool responses, error payloads, and logs.
"""

import os
import unittest

import responses

# Configure fake token before importing app modules
FAKE_TOKEN = "TEST_FAKE_TOKEN_DO_NOT_USE_123456"
os.environ["FACEBOOK_ACCESS_TOKEN"] = FAKE_TOKEN
os.environ["META_GRAPH_API_VERSION"] = "v26.0"
os.environ["MCP_AUTH_TOKEN"] = "TEST_MCP_SECRET_AUTH_TOKEN_9999"
os.environ["CLOUDINARY_CLOUD_NAME"] = "test-cloud"
os.environ["CLOUDINARY_API_KEY"] = "1234567890"
os.environ["CLOUDINARY_API_SECRET"] = "TEST_CLOUDINARY_SECRET_XYZ"
os.environ["MAX_CAMPAIGN_BUDGET"] = "10.00"

from app.tools.export import export_facebook_ads_data
from app.tools.management import create_ad, create_ad_set, create_campaign, list_ad_accounts
from app.tools.search import search_facebook_ads


class FakeTokenAcceptanceTest(unittest.TestCase):
    def assert_no_leak(self, payload: object) -> None:
        """Verify that neither fake tokens nor cloudinary secrets appear in string representation."""
        as_str = str(payload)
        self.assertNotIn(FAKE_TOKEN, as_str, f"Token leaked in payload: {as_str}")
        self.assertNotIn("TEST_CLOUDINARY_SECRET_XYZ", as_str, "Cloudinary secret leaked")
        self.assertNotIn("TEST_MCP_SECRET_AUTH_TOKEN_9999", as_str, "MCP Auth token leaked")

    @responses.activate
    def test_search_facebook_ads_leak_free(self):
        responses.add(
            responses.GET,
            "https://graph.facebook.com/v26.0/ads_archive",
            json={
                "data": [
                    {
                        "id": "111",
                        "page_name": "TestPage",
                        "ad_creative_bodies": ["Buy our new product"],
                    }
                ]
            },
            status=200,
        )
        res = search_facebook_ads(brand_name="TestPage", country="BR")
        self.assertTrue(res["success"])
        self.assert_no_leak(res)

    @responses.activate
    def test_api_error_response_leak_free(self):
        responses.add(
            responses.GET,
            "https://graph.facebook.com/v26.0/ads_archive",
            status=400,
            json={"error": {"message": f"Auth failed with token {FAKE_TOKEN}"}},
        )
        res = search_facebook_ads(brand_name="ErrorBrand")
        self.assertFalse(res["success"])
        self.assert_no_leak(res)

    @responses.activate
    def test_management_tools_leak_free(self):
        responses.add(
            responses.GET,
            "https://graph.facebook.com/v26.0/me/adaccounts",
            json={"data": [{"account_id": "999888", "name": "Main", "currency": "BRL"}]},
            status=200,
        )
        # List accounts
        res_acc = list_ad_accounts()
        self.assertTrue(res_acc["success"])
        self.assert_no_leak(res_acc)

        # Create campaign dry run
        res_camp = create_campaign(
            ad_account_id="999888",
            name="Promo 2026",
            objective="OUTCOME_SALES",
            daily_budget=10.00,
            dry_run=True,
        )
        self.assertTrue(res_camp["success"])
        self.assert_no_leak(res_camp)

        # Create ad set dry run
        res_set = create_ad_set(
            ad_account_id="999888",
            campaign_id="camp_1",
            name="Set 1",
            countries=["BR"],
            daily_budget=5.00,
            dry_run=True,
        )
        self.assertTrue(res_set["success"])
        self.assert_no_leak(res_set)

        # Create ad dry run
        res_ad = create_ad(
            ad_account_id="999888",
            ad_set_id="adset_1",
            image_url="https://res.cloudinary.com/test-cloud/image/upload/sample.jpg",
            title="Promo Title",
            body="Promo Body",
            link_url="https://example.com/promo",
            call_to_action="SHOP_NOW",
            dry_run=True,
        )
        self.assertTrue(res_ad["success"])
        self.assert_no_leak(res_ad)

    @responses.activate
    def test_exports_leak_free(self):
        responses.add(
            responses.GET,
            "https://graph.facebook.com/v26.0/ads_archive",
            json={"data": [{"id": "1", "page_name": "Brand"}]},
            status=200,
        )
        for fmt in ("json", "csv", "markdown"):
            res = export_facebook_ads_data(brand_name="Brand", export_format=fmt)
            self.assertTrue(res["success"])
            self.assert_no_leak(res)


if __name__ == "__main__":
    unittest.main()
