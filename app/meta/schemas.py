"""Pydantic schemas and DTOs with strict allowlists for Meta Ads and campaign management."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SafeAd(BaseModel):
    """Sanitized and allowlisted Facebook Ad DTO (SEC-003, SEC-004, Q2, Q37, Q40)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    page_id: str | None = None
    page_name: str | None = None
    ad_creation_time: str | None = None
    ad_creative_bodies: list[str] = Field(default_factory=list)
    ad_creative_link_captions: list[str] = Field(default_factory=list)
    ad_creative_link_descriptions: list[str] = Field(default_factory=list)
    ad_creative_link_titles: list[str] = Field(default_factory=list)
    publisher_platforms: list[str] = Field(default_factory=list)
    currency: str | None = None
    impressions: dict[str, Any] | None = None
    spend: dict[str, Any] | None = None
    public_ad_url: str
    demographic_distribution: list[dict[str, Any]] | None = None
    delivery_by_region: list[dict[str, Any]] | None = None
    reach: str | None = "not_available"


class SafeAdAccount(BaseModel):
    """Sanitized Ad Account DTO (Q18)."""

    model_config = ConfigDict(extra="forbid")

    ad_account_id: str
    name: str
    currency: str
    account_status: int


class SafeAssetResult(BaseModel):
    """Sanitized creative asset upload DTO (Q18, Q19)."""

    model_config = ConfigDict(extra="forbid")

    asset_id: str
    public_url: str
    mime_type: str
    width: int | None = None
    height: int | None = None
    bytes: int


class SafeCampaignResult(BaseModel):
    """Sanitized campaign creation result DTO (Q15, Q22)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    ad_account_id: str
    name: str
    objective: str
    daily_budget_decimal: float
    daily_budget_subunit: int
    special_ad_categories: list[str] = Field(default_factory=list)
    dry_run: bool
    status: str


class SafeAdSetResult(BaseModel):
    """Sanitized ad set creation result DTO (Q15, Q22)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    ad_account_id: str
    campaign_id: str
    name: str
    daily_budget_decimal: float | None = None
    daily_budget_subunit: int | None = None
    targeting: dict[str, Any]
    dry_run: bool
    status: str


class SafeAdResult(BaseModel):
    """Sanitized ad creation result DTO (Q15, Q22, Q41)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    ad_account_id: str
    ad_set_id: str
    title: str
    body: str
    image_url: str
    link_url: str
    call_to_action: str
    dry_run: bool
    status: str
