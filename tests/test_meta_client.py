"""Unit tests for MetaAdsClient with responses mocking."""

import pytest
import responses

from app.exceptions import MetaAPIError
from app.meta.client import MetaAdsClient


@responses.activate
def test_client_sends_bearer_header_not_in_params():
    token = "TEST_SECRET_FACEBOOK_TOKEN_12345"
    client = MetaAdsClient(access_token=token, graph_api_version="v26.0")

    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={"data": [{"id": "111", "page_name": "Test Brand"}]},
        status=200,
    )

    result = client.search_ads(search_terms="Test Brand")
    assert len(result["data"]) == 1

    req = responses.calls[0].request
    assert req.headers["Authorization"] == f"Bearer {token}"
    # Token MUST NOT be in query string
    assert "access_token" not in req.url
    assert token not in req.url


@responses.activate
def test_client_get_retries_on_500():
    token = "TEST_TOKEN"
    client = MetaAdsClient(access_token=token, max_retries=2)

    # First attempt fails with 500, second succeeds with 200
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        status=500,
    )
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={"data": [{"id": "222"}]},
        status=200,
    )

    result = client.search_ads(search_terms="Retry Test")
    assert len(result["data"]) == 1
    assert len(responses.calls) == 2


@responses.activate
def test_client_post_does_not_retry():
    token = "TEST_TOKEN"
    client = MetaAdsClient(access_token=token, max_retries=3)

    responses.add(
        responses.POST,
        "https://graph.facebook.com/v26.0/act_12345/campaigns",
        status=500,
        json={"error": {"message": "Internal error"}},
    )

    with pytest.raises(MetaAPIError, match="Meta API POST error"):
        client.create_campaign("12345", {"name": "Test Campaign"})

    # Must be called strictly once (no retry for POST)
    assert len(responses.calls) == 1


@responses.activate
def test_client_redirect_rejected():
    token = "TEST_TOKEN"
    client = MetaAdsClient(access_token=token)

    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        status=302,
        headers={"Location": "https://attacker.com"},
    )

    with pytest.raises(MetaAPIError, match="Unexpected redirect"):
        client.search_ads(search_terms="Redirect test")


@responses.activate
def test_client_paginated_cursor():
    token = "TEST_TOKEN"
    client = MetaAdsClient(access_token=token)

    # Page 1
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={
            "data": [{"id": "1"}, {"id": "2"}],
            "paging": {"cursors": {"after": "cursor_page_2"}},
        },
        status=200,
    )
    # Page 2
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/ads_archive",
        json={
            "data": [{"id": "3"}],
            "paging": {"cursors": {"after": "cursor_page_3"}},
        },
        status=200,
    )

    ads = client.fetch_all_ads_paginated(search_terms="Shoes", max_results=3, page_size=2)
    assert len(ads) == 3
    assert [a["id"] for a in ads] == ["1", "2", "3"]
    assert len(responses.calls) == 2
