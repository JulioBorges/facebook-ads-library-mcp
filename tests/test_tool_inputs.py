"""Unit tests for tool input validation."""

import pytest

from app.exceptions import InvalidInputError
from app.security.validation import (
    validate_ad_account_id,
    validate_ad_id,
    validate_ad_type,
    validate_brand_name,
    validate_country_code,
    validate_limit,
)


def test_validate_brand_name():
    assert validate_brand_name("Nike") == "Nike"
    assert validate_brand_name("  Adidas Brasil  ") == "Adidas Brasil"

    with pytest.raises(InvalidInputError):
        validate_brand_name("")

    with pytest.raises(InvalidInputError):
        validate_brand_name("a" * 201)

    with pytest.raises(InvalidInputError):
        validate_brand_name(123)  # type: ignore


def test_validate_country_code():
    assert validate_country_code("BR") == "BR"
    assert validate_country_code("us") == "US"

    with pytest.raises(InvalidInputError):
        validate_country_code("BRA")

    with pytest.raises(InvalidInputError):
        validate_country_code("12")


def test_validate_ad_type():
    assert validate_ad_type("ALL") == "ALL"
    assert validate_ad_type("housing") == "HOUSING"
    assert validate_ad_type("POLITICAL_AND_ISSUE_ADS") == "POLITICAL_AND_ISSUE_ADS"

    with pytest.raises(InvalidInputError):
        validate_ad_type("INVALID_TYPE")


def test_validate_limit():
    assert validate_limit(50) == 50
    assert validate_limit(1) == 1
    assert validate_limit(100) == 100

    with pytest.raises(InvalidInputError):
        validate_limit(0)

    with pytest.raises(InvalidInputError):
        validate_limit(101)

    with pytest.raises(InvalidInputError):
        validate_limit(True)  # bool is subclass of int in python


def test_validate_ad_id():
    assert validate_ad_id("1234567890") == "1234567890"

    with pytest.raises(InvalidInputError):
        validate_ad_id("https://facebook.com/123")

    with pytest.raises(InvalidInputError):
        validate_ad_id("123; DROP TABLE ads;")

    with pytest.raises(InvalidInputError):
        validate_ad_id("../../../etc/passwd")


def test_validate_ad_account_id():
    assert validate_ad_account_id("123456789") == "123456789"
    assert validate_ad_account_id("act_123456789") == "act_123456789"

    with pytest.raises(InvalidInputError):
        validate_ad_account_id("act_invalid_abc")
