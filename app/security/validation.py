"""Input validation constants and validator functions."""

import re

from app.exceptions import InvalidInputError

# Regex patterns
AD_ID_PATTERN = re.compile(r"^\d{1,32}$")
COUNTRY_CODE_PATTERN = re.compile(r"^[A-Z]{2}$")
HEX_OR_ALPHANUMERIC_ID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

# Allowlist Enums
AD_TYPE_ALLOWED = {
    "ALL",
    "POLITICAL_AND_ISSUE_ADS",
    "HOUSING",
    "EMPLOYMENT",
    "CREDIT",
}

OBJECTIVE_ALLOWED = {
    "OUTCOME_TRAFFIC",
    "OUTCOME_ENGAGEMENT",
    "OUTCOME_LEADS",
    "OUTCOME_SALES",
    "OUTCOME_APP_PROMOTION",
}

SPECIAL_AD_CATEGORIES_ALLOWED = {
    "NONE",
    "EMPLOYMENT",
    "HOUSING",
    "CREDIT",
    "FINANCIAL_PRODUCTS_AND_SERVICES_ADS",
}

CTA_ALLOWED = {
    "SHOP_NOW",
    "LEARN_MORE",
    "SIGN_UP",
    "DOWNLOAD",
    "CONTACT_US",
    "GET_OFFER",
    "GET_QUOTE",
    "SUBSCRIBE",
    "INSTALL_APP",
    "BOOK_TRAVEL",
    "LISTEN_NOW",
}

EXPORT_FORMAT_ALLOWED = {"json", "csv", "markdown"}

ALLOWED_PUBLISHER_PLATFORMS = {
    "facebook",
    "instagram",
    "audience_network",
    "messenger",
}

ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
}


def validate_brand_name(brand_name: str) -> str:
    """Validate brand name string length between 1 and 200 characters."""
    if not isinstance(brand_name, str):
        raise InvalidInputError("brand_name must be a string")
    cleaned = brand_name.strip()
    if not cleaned or len(cleaned) > 200:
        raise InvalidInputError("brand_name must be between 1 and 200 characters")
    return cleaned


def validate_country_code(country: str) -> str:
    """Validate 2-letter ISO country code."""
    if not isinstance(country, str):
        raise InvalidInputError("country must be a string")
    cleaned = country.strip().upper()
    if not COUNTRY_CODE_PATTERN.match(cleaned):
        raise InvalidInputError(
            f"Invalid country code '{country}'. Must be 2 uppercase letters (e.g. 'BR', 'US')."
        )
    return cleaned


def validate_ad_type(ad_type: str) -> str:
    """Validate ad_type against allowed allowlist."""
    if not isinstance(ad_type, str):
        raise InvalidInputError("ad_type must be a string")
    cleaned = ad_type.strip().upper()
    if cleaned not in AD_TYPE_ALLOWED:
        raise InvalidInputError(
            f"Invalid ad_type '{ad_type}'. Allowed values: {sorted(AD_TYPE_ALLOWED)}"
        )
    return cleaned


def validate_limit(limit: int, min_val: int = 1, max_val: int = 100) -> int:
    """Validate integer limit within bounded range."""
    if not isinstance(limit, int) or isinstance(limit, bool):
        raise InvalidInputError(f"limit must be an integer between {min_val} and {max_val}")
    if limit < min_val or limit > max_val:
        raise InvalidInputError(f"limit must be between {min_val} and {max_val}")
    return limit


def validate_ad_id(ad_id: str) -> str:
    """Validate ad_id as numeric string (1-32 digits) to prevent SSRF and injection."""
    if not isinstance(ad_id, str):
        raise InvalidInputError("ad_id must be a string")
    cleaned = ad_id.strip()
    if not AD_ID_PATTERN.match(cleaned):
        raise InvalidInputError(f"Invalid ad_id '{ad_id}'. Must be 1-32 digits only.")
    return cleaned


def validate_ad_account_id(ad_account_id: str) -> str:
    """Validate ad_account_id format."""
    if not isinstance(ad_account_id, str):
        raise InvalidInputError("ad_account_id must be a string")
    cleaned = ad_account_id.strip()
    if cleaned.startswith("act_"):
        raw_id = cleaned[4:]
    else:
        raw_id = cleaned
    if not AD_ID_PATTERN.match(raw_id):
        raise InvalidInputError(
            f"Invalid ad_account_id '{ad_account_id}'. Must be digits (optionally prefixed by 'act_')."
        )
    return cleaned
