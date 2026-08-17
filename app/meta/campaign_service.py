"""CampaignService: Management layer for creating campaigns, ad sets, and ads with dry-run and budget safeguards (Q13, Q15, Q21, Q22, Q39)."""

from typing import Any

from app.exceptions import BudgetExceededError, InvalidInputError
from app.meta.ad_account_service import AdAccountService
from app.meta.client import MetaAdsClient
from app.meta.schemas import SafeAdResult, SafeAdSetResult, SafeCampaignResult
from app.security.url_policy import validate_destination_url
from app.security.validation import (
    ALLOWED_PUBLISHER_PLATFORMS,
    CTA_ALLOWED,
    OBJECTIVE_ALLOWED,
    SPECIAL_AD_CATEGORIES_ALLOWED,
    validate_ad_account_id,
    validate_brand_name,
    validate_country_code,
)


class CampaignService:
    """Service handling campaign creation, ad sets, and ads with strict financial and input controls."""

    def __init__(
        self,
        client: MetaAdsClient,
        account_service: AdAccountService,
        max_campaign_budget: float = 10.00,
    ):
        self.client = client
        self.account_service = account_service
        self.max_campaign_budget = max_campaign_budget

    def _validate_and_convert_budget(self, budget: float) -> tuple[float, int]:
        """Validate daily budget against decimal ceiling and convert to integer subunits (x100) (Q21, Q39)."""
        if not isinstance(budget, (int, float)) or isinstance(budget, bool):
            raise InvalidInputError("daily_budget must be a numeric value")

        budget_float = round(float(budget), 2)
        if budget_float <= 0:
            raise InvalidInputError("daily_budget must be greater than zero (> 0)")

        if budget_float > self.max_campaign_budget:
            raise BudgetExceededError(
                f"daily_budget ({budget_float:.2f}) exceeds configured maximum ceiling ({self.max_campaign_budget:.2f})"
            )

        subunit = round(budget_float * 100)
        return budget_float, subunit

    def _resolve_ad_account_id(self, ad_account_id: str, dry_run: bool) -> str:
        """Resolve the normalized ad_account_id, scoping live API validation to real operations.

        In dry-run mode only local format validation is performed (no network call),
        so simulations keep working for planning/preview purposes even if the Meta
        API is unreachable or the configured token/permissions aren't set up yet --
        matching the documented promise that dry_run "simulates ... without
        committing changes to Meta". Live ownership validation (which does hit
        Meta's `/me/adaccounts`) only runs when we're about to actually spend money.
        """
        if dry_run:
            valid_id = validate_ad_account_id(ad_account_id)
            return valid_id.removeprefix("act_")

        account = self.account_service.validate_ad_account(ad_account_id)
        return account.ad_account_id

    def create_campaign(
        self,
        ad_account_id: str,
        name: str,
        objective: str,
        daily_budget: float,
        special_ad_categories: list[str] | None = None,
        dry_run: bool = True,
    ) -> SafeCampaignResult:
        """Create campaign with budget validation and dry-run default."""
        resolved_account_id = self._resolve_ad_account_id(ad_account_id, dry_run)
        valid_name = validate_brand_name(name)

        valid_obj = objective.strip().upper()
        if valid_obj not in OBJECTIVE_ALLOWED:
            raise InvalidInputError(
                f"Invalid objective '{objective}'. Allowed values: {sorted(OBJECTIVE_ALLOWED)}"
            )

        # Validate special ad categories
        categories = ["NONE"]
        if special_ad_categories:
            if not isinstance(special_ad_categories, list):
                raise InvalidInputError("special_ad_categories must be a list of strings")
            categories = []
            for cat in special_ad_categories:
                c_clean = str(cat).strip().upper()
                if c_clean not in SPECIAL_AD_CATEGORIES_ALLOWED:
                    raise InvalidInputError(
                        f"Invalid special ad category '{cat}'. Allowed: {sorted(SPECIAL_AD_CATEGORIES_ALLOWED)}"
                    )
                categories.append(c_clean)

        budget_decimal, budget_subunit = self._validate_and_convert_budget(daily_budget)

        if dry_run:
            return SafeCampaignResult(
                id="dry_run_campaign_id_simulated",
                ad_account_id=resolved_account_id,
                name=valid_name,
                objective=valid_obj,
                daily_budget_decimal=budget_decimal,
                daily_budget_subunit=budget_subunit,
                special_ad_categories=categories,
                dry_run=True,
                status="SIMULATED",
            )

        payload = {
            "name": valid_name,
            "objective": valid_obj,
            "status": "PAUSED",
            "special_ad_categories": categories,
            "daily_budget": budget_subunit,
        }

        res = self.client.create_campaign(resolved_account_id, payload)
        campaign_id = str(res.get("id", "created_campaign"))

        return SafeCampaignResult(
            id=campaign_id,
            ad_account_id=resolved_account_id,
            name=valid_name,
            objective=valid_obj,
            daily_budget_decimal=budget_decimal,
            daily_budget_subunit=budget_subunit,
            special_ad_categories=categories,
            dry_run=False,
            status="PAUSED",
        )

    def create_ad_set(
        self,
        ad_account_id: str,
        campaign_id: str,
        name: str,
        countries: list[str],
        age_min: int = 18,
        age_max: int = 65,
        genders: int = 0,
        publisher_platforms: list[str] | None = None,
        daily_budget: float | None = None,
        dry_run: bool = True,
    ) -> SafeAdSetResult:
        """Create ad set with server-side validated targeting and dry-run default."""
        resolved_account_id = self._resolve_ad_account_id(ad_account_id, dry_run)
        valid_name = validate_brand_name(name)

        if not isinstance(countries, list) or not countries:
            raise InvalidInputError(
                "countries must be a non-empty list of 2-letter ISO country codes"
            )
        valid_countries = [validate_country_code(c) for c in countries]

        if (
            not isinstance(age_min, int)
            or not isinstance(age_max, int)
            or isinstance(age_min, bool)
        ):
            raise InvalidInputError("age_min and age_max must be integers between 18 and 65")
        if age_min < 18 or age_max > 65 or age_min > age_max:
            raise InvalidInputError(
                f"Invalid age range {age_min}-{age_max}. Must satisfy 18 <= age_min <= age_max <= 65."
            )

        if genders not in (0, 1, 2):
            raise InvalidInputError("genders must be 0 (all), 1 (male), or 2 (female)")

        platforms = list(ALLOWED_PUBLISHER_PLATFORMS)
        if publisher_platforms:
            if not isinstance(publisher_platforms, list):
                raise InvalidInputError("publisher_platforms must be a list of strings")
            platforms = []
            for p in publisher_platforms:
                p_clean = str(p).strip().lower()
                if p_clean not in ALLOWED_PUBLISHER_PLATFORMS:
                    raise InvalidInputError(
                        f"Invalid publisher platform '{p}'. Allowed: {sorted(ALLOWED_PUBLISHER_PLATFORMS)}"
                    )
                platforms.append(p_clean)

        budget_decimal: float | None = None
        budget_subunit: int | None = None
        if daily_budget is not None:
            budget_decimal, budget_subunit = self._validate_and_convert_budget(daily_budget)

        targeting = {
            "geo_locations": {"countries": valid_countries},
            "age_min": age_min,
            "age_max": age_max,
            "genders": [genders] if genders in (1, 2) else [1, 2],
            "publisher_platforms": platforms,
        }

        if dry_run:
            return SafeAdSetResult(
                id="dry_run_ad_set_id_simulated",
                ad_account_id=resolved_account_id,
                campaign_id=campaign_id,
                name=valid_name,
                daily_budget_decimal=budget_decimal,
                daily_budget_subunit=budget_subunit,
                targeting=targeting,
                dry_run=True,
                status="SIMULATED",
            )

        payload: dict[str, Any] = {
            "campaign_id": campaign_id,
            "name": valid_name,
            "status": "PAUSED",
            "targeting": targeting,
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "REACH",
        }
        if budget_subunit is not None:
            payload["daily_budget"] = budget_subunit

        res = self.client.create_ad_set(resolved_account_id, payload)
        ad_set_id = str(res.get("id", "created_ad_set"))

        return SafeAdSetResult(
            id=ad_set_id,
            ad_account_id=resolved_account_id,
            campaign_id=campaign_id,
            name=valid_name,
            daily_budget_decimal=budget_decimal,
            daily_budget_subunit=budget_subunit,
            targeting=targeting,
            dry_run=False,
            status="PAUSED",
        )

    def create_ad(
        self,
        ad_account_id: str,
        ad_set_id: str,
        image_url: str,
        title: str,
        body: str,
        link_url: str,
        call_to_action: str,
        dry_run: bool = True,
    ) -> SafeAdResult:
        """Create ad with validated copy, HTTPS link_url, CTA allowlist, and dry-run default."""
        resolved_account_id = self._resolve_ad_account_id(ad_account_id, dry_run)
        valid_title = validate_brand_name(title)

        if not isinstance(body, str) or not body.strip() or len(body) > 2000:
            raise InvalidInputError("body must be a string between 1 and 2000 characters")

        valid_link = validate_destination_url(link_url)

        valid_cta = call_to_action.strip().upper()
        if valid_cta not in CTA_ALLOWED:
            raise InvalidInputError(
                f"Invalid call_to_action '{call_to_action}'. Allowed values: {sorted(CTA_ALLOWED)}"
            )

        if not isinstance(image_url, str) or not image_url.startswith("https://"):
            raise InvalidInputError(
                "image_url must be a valid HTTPS URL (e.g. from Cloudinary asset upload)"
            )

        if dry_run:
            return SafeAdResult(
                id="dry_run_ad_id_simulated",
                ad_account_id=resolved_account_id,
                ad_set_id=ad_set_id,
                title=valid_title,
                body=body.strip(),
                image_url=image_url.strip(),
                link_url=valid_link,
                call_to_action=valid_cta,
                dry_run=True,
                status="SIMULATED",
            )

        payload = {
            "adset_id": ad_set_id,
            "name": valid_title,
            "status": "PAUSED",
            "creative": {
                "title": valid_title,
                "body": body.strip(),
                "image_url": image_url.strip(),
                "link_url": valid_link,
                "call_to_action": {"type": valid_cta},
            },
        }

        res = self.client.create_ad(resolved_account_id, payload)
        ad_id = str(res.get("id", "created_ad"))

        return SafeAdResult(
            id=ad_id,
            ad_account_id=resolved_account_id,
            ad_set_id=ad_set_id,
            title=valid_title,
            body=body.strip(),
            image_url=image_url.strip(),
            link_url=valid_link,
            call_to_action=valid_cta,
            dry_run=False,
            status="PAUSED",
        )
