"""Tests for campaign budget validation, ceiling enforcement, and subunit conversion (Q21, Q39)."""

import pytest

from app.exceptions import BudgetExceededError, InvalidInputError
from app.meta.ad_account_service import AdAccountService
from app.meta.campaign_service import CampaignService
from app.meta.client import MetaAdsClient


def test_budget_conversion_and_subunits():
    client = MetaAdsClient(access_token="TOKEN")
    account_service = AdAccountService(client=client)
    service = CampaignService(
        client=client, account_service=account_service, max_campaign_budget=10.00
    )

    # Valid conversion tests (x100)
    b_dec, b_sub = service._validate_and_convert_budget(10.00)
    assert b_dec == 10.00
    assert b_sub == 1000

    b_dec, b_sub = service._validate_and_convert_budget(5.50)
    assert b_dec == 5.50
    assert b_sub == 550

    b_dec, b_sub = service._validate_and_convert_budget(9.99)
    assert b_dec == 9.99
    assert b_sub == 999


def test_budget_ceiling_rejection():
    client = MetaAdsClient(access_token="TOKEN")
    account_service = AdAccountService(client=client)
    service = CampaignService(
        client=client, account_service=account_service, max_campaign_budget=10.00
    )

    with pytest.raises(BudgetExceededError):
        service._validate_and_convert_budget(10.01)

    with pytest.raises(BudgetExceededError):
        service._validate_and_convert_budget(50.00)


def test_zero_or_negative_budget_rejection():
    client = MetaAdsClient(access_token="TOKEN")
    account_service = AdAccountService(client=client)
    service = CampaignService(
        client=client, account_service=account_service, max_campaign_budget=10.00
    )

    with pytest.raises(InvalidInputError):
        service._validate_and_convert_budget(0.00)

    with pytest.raises(InvalidInputError):
        service._validate_and_convert_budget(-5.00)

    with pytest.raises(InvalidInputError):
        service._validate_and_convert_budget("not_a_number")  # type: ignore
