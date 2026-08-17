"""Ad account listing, caching (5 min TTL), and validation service (Q16/Q17)."""

import time

from app.exceptions import AdAccountNotFoundError
from app.meta.client import MetaAdsClient
from app.meta.schemas import SafeAdAccount
from app.security.validation import validate_ad_account_id

CACHE_TTL_SECONDS = 300  # 5 minutes cache


class AdAccountService:
    """Service managing authorized Meta Ad Accounts with in-memory TTL caching."""

    def __init__(self, client: MetaAdsClient):
        self.client = client
        self._cached_accounts: list[SafeAdAccount] = []
        self._last_fetch_time: float = 0.0

    def _normalize_account_id(self, account_id: str) -> str:
        """Strip 'act_' prefix for consistent comparison."""
        cleaned = str(account_id).strip()
        if cleaned.startswith("act_"):
            return cleaned[4:]
        return cleaned

    def list_accounts(self, force_refresh: bool = False) -> list[SafeAdAccount]:
        """Fetch authorized ad accounts from Meta Graph API or return cached accounts (Q17)."""
        now = time.time()
        if (
            not force_refresh
            and self._cached_accounts
            and (now - self._last_fetch_time < CACHE_TTL_SECONDS)
        ):
            return self._cached_accounts

        raw_accounts = self.client.get_ad_accounts()
        safe_accounts: list[SafeAdAccount] = []

        for item in raw_accounts:
            raw_id = item.get("account_id") or item.get("id") or ""
            norm_id = self._normalize_account_id(str(raw_id))
            safe_accounts.append(
                SafeAdAccount(
                    ad_account_id=norm_id,
                    name=str(item.get("name") or f"Account {norm_id}"),
                    currency=str(item.get("currency") or "BRL"),
                    account_status=int(item.get("account_status", 1)),
                )
            )

        self._cached_accounts = safe_accounts
        self._last_fetch_time = now
        return self._cached_accounts

    def validate_ad_account(self, ad_account_id: str) -> SafeAdAccount:
        """Validate that the given ad_account_id belongs to authorized accounts."""
        valid_id = validate_ad_account_id(ad_account_id)
        norm_input_id = self._normalize_account_id(valid_id)

        accounts = self.list_accounts()
        for acc in accounts:
            if self._normalize_account_id(acc.ad_account_id) == norm_input_id:
                return acc

        # If not found in cache, attempt fresh fetch once
        accounts = self.list_accounts(force_refresh=True)
        for acc in accounts:
            if self._normalize_account_id(acc.ad_account_id) == norm_input_id:
                return acc

        raise AdAccountNotFoundError(
            f"Ad account ID '{ad_account_id}' was not found in authorized accounts for this token."
        )
