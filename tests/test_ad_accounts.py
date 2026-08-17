"""Tests for AdAccountService listing, caching, and validation (Q16/Q17)."""

import pytest
import responses

from app.exceptions import AdAccountNotFoundError
from app.meta.ad_account_service import AdAccountService
from app.meta.client import MetaAdsClient


@responses.activate
def test_ad_account_service_caches_for_5_minutes():
    client = MetaAdsClient(access_token="TOKEN", graph_api_version="v26.0")
    service = AdAccountService(client=client)

    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/me/adaccounts",
        json={
            "data": [
                {
                    "account_id": "111222333",
                    "name": "Primary Account",
                    "currency": "BRL",
                    "account_status": 1,
                }
            ]
        },
        status=200,
    )

    # First call hits API
    accounts = service.list_accounts()
    assert len(accounts) == 1
    assert accounts[0].ad_account_id == "111222333"
    assert len(responses.calls) == 1

    # Second call uses in-memory cache without hitting API
    cached_accounts = service.list_accounts()
    assert len(cached_accounts) == 1
    assert len(responses.calls) == 1


@responses.activate
def test_validate_ad_account_success_and_failure():
    client = MetaAdsClient(access_token="TOKEN", graph_api_version="v26.0")
    service = AdAccountService(client=client)

    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/me/adaccounts",
        json={"data": [{"account_id": "999888777", "name": "Valid Account", "currency": "BRL"}]},
        status=200,
    )

    # With prefix
    acc = service.validate_ad_account("act_999888777")
    assert acc.ad_account_id == "999888777"

    # Without prefix
    acc2 = service.validate_ad_account("999888777")
    assert acc2.ad_account_id == "999888777"

    # Unauthorized ID raises AdAccountNotFoundError
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/me/adaccounts",
        json={"data": [{"account_id": "999888777", "name": "Valid Account", "currency": "BRL"}]},
        status=200,
    )
    with pytest.raises(AdAccountNotFoundError):
        service.validate_ad_account("123456789")
