"""MetaAdsClient: Unified secure client for Meta Graph API (read & write)."""

import json
import time
from typing import Any

import requests

from app.exceptions import MetaAPIError

SEARCH_FIELDS = (
    "id,page_id,page_name,ad_creation_time,"
    "ad_creative_bodies,ad_creative_link_captions,"
    "ad_creative_link_descriptions,ad_creative_link_titles,"
    "publisher_platforms,currency,impressions,spend,"
    "demographic_distribution,delivery_by_region"
)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class MetaAdsClient:
    """Secure Meta Graph API client isolating credentials and preventing leaks."""

    def __init__(
        self,
        access_token: str,
        graph_api_version: str = "v26.0",
        connect_timeout: int = 5,
        read_timeout: int = 30,
        max_retries: int = 3,
        max_total_seconds: float = 45.0,
    ):
        self.graph_api_version = graph_api_version
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.max_retries = max_retries
        # Hard wall-clock ceiling across all attempts+backoffs for a single call.
        # (connect_timeout + read_timeout) * (max_retries + 1) can otherwise
        # exceed a calling MCP client's own ~60s tool-call timeout when the
        # network is down/blocked rather than merely slow -- e.g. the default
        # 5s/30s timeouts with 3 retries can take up to ~127s to finally raise,
        # so the caller sees an opaque timeout instead of our clear error
        # message. This mirrors the fix already applied to CloudinaryClient.
        self.max_total_seconds = max_total_seconds
        self.base_url = f"https://graph.facebook.com/{graph_api_version}"

        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
                "User-Agent": "FacebookAdsMCP/3.0.0",
            }
        )

    def _get_with_retry(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute GET request with exponential backoff retry on transient errors (Q25).

        Bounded by `max_total_seconds` wall-clock time across all attempts and
        backoff sleeps, so a persistently unreachable network fails with a
        clear MetaAPIError well before a calling MCP client's own timeout,
        instead of being silently multiplied past it by the retry loop.
        """
        retries = 0
        backoffs = [1, 2, 4]
        start_time = time.monotonic()

        while True:
            try:
                response = self.session.get(
                    url,
                    params=params,
                    allow_redirects=False,
                    timeout=(self.connect_timeout, self.read_timeout),
                )
                # Check for unexpected redirects (SEC-007)
                if response.is_redirect or response.status_code in (301, 302, 307, 308):
                    raise MetaAPIError("Unexpected redirect from Meta Graph API")

                if response.status_code == 200:
                    try:
                        return response.json()
                    except ValueError as err:
                        raise MetaAPIError("Invalid JSON returned by Meta Graph API") from err

                if response.status_code in RETRYABLE_STATUS_CODES and retries < self.max_retries:
                    sleep_time = backoffs[min(retries, len(backoffs) - 1)]
                    if time.monotonic() - start_time + sleep_time >= self.max_total_seconds:
                        raise MetaAPIError(
                            f"Meta API error (HTTP {response.status_code}) after "
                            f"{retries + 1} attempt(s); giving up at the "
                            f"{self.max_total_seconds:.0f}s retry budget"
                        )
                    retries += 1
                    time.sleep(sleep_time)
                    continue

                # Non-retryable error or retries exhausted
                err_msg = f"Meta API error (HTTP {response.status_code})"
                try:
                    err_json = response.json()
                    if isinstance(err_json, dict) and "error" in err_json:
                        meta_err = err_json["error"]
                        if isinstance(meta_err, dict) and "message" in meta_err:
                            err_msg = f"Meta API error: {meta_err['message']}"
                except (ValueError, KeyError, TypeError):
                    pass
                raise MetaAPIError(err_msg)

            except requests.RequestException as exc:
                sleep_time = backoffs[min(retries, len(backoffs) - 1)]
                elapsed = time.monotonic() - start_time
                if retries < self.max_retries and elapsed + sleep_time < self.max_total_seconds:
                    retries += 1
                    time.sleep(sleep_time)
                    continue
                raise MetaAPIError(
                    "Could not reach the Meta Graph API within the configured retry "
                    f"budget ({elapsed:.1f}s elapsed, {retries + 1} attempt(s)). This "
                    "usually means a network, VPN, or proxy/firewall is blocking "
                    f"graph.facebook.com. Underlying error: {exc!s}"
                ) from exc

    def _post_no_retry(
        self,
        url: str,
        json_payload: dict[str, Any] | None = None,
        data_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute POST request without retry to ensure idempotency and prevent duplicates (Q25)."""
        try:
            response = self.session.post(
                url,
                json=json_payload,
                data=data_payload,
                allow_redirects=False,
                timeout=(self.connect_timeout, self.read_timeout),
            )
            if response.is_redirect or response.status_code in (301, 302, 307, 308):
                raise MetaAPIError("Unexpected redirect from Meta Graph API during POST")

            if response.status_code in (200, 201):
                try:
                    return response.json()
                except ValueError as err:
                    raise MetaAPIError("Invalid JSON returned by Meta Graph API on POST") from err

            err_msg = f"Meta API POST error (HTTP {response.status_code})"
            try:
                err_json = response.json()
                if isinstance(err_json, dict) and "error" in err_json:
                    meta_err = err_json["error"]
                    if isinstance(meta_err, dict) and "message" in meta_err:
                        err_msg = f"Meta API POST error: {meta_err['message']}"
            except (ValueError, KeyError, TypeError):
                pass
            raise MetaAPIError(err_msg)

        except requests.RequestException as exc:
            raise MetaAPIError(f"Meta API POST network failure: {exc!s}") from exc

    def search_ads(
        self,
        search_terms: str,
        country: str = "BR",
        ad_type: str = "ALL",
        limit: int = 50,
        after: str | None = None,
        since: str | None = None,
        until: str | None = None,
    ) -> dict[str, Any]:
        """Query Facebook Ads Library API."""
        url = f"{self.base_url}/ads_archive"
        params: dict[str, Any] = {
            "search_terms": search_terms,
            "ad_reached_countries": json.dumps([country]),
            "ad_type": ad_type,
            "limit": limit,
            "fields": SEARCH_FIELDS,
        }
        if after:
            params["after"] = after
        if since:
            params["ad_delivery_date_min"] = since
        if until:
            params["ad_delivery_date_max"] = until

        return self._get_with_retry(url, params=params)

    def fetch_all_ads_paginated(
        self,
        search_terms: str,
        country: str = "BR",
        ad_type: str = "ALL",
        max_results: int = 100,
        page_size: int = 50,
        max_pages: int = 5,
    ) -> list[dict[str, Any]]:
        """Paginate safely through search results using cursor parameters without following external URLs (Q9)."""
        collected_ads: list[dict[str, Any]] = []
        after_cursor: str | None = None
        pages_fetched = 0

        while pages_fetched < max_pages and len(collected_ads) < max_results:
            fetch_limit = min(page_size, max_results - len(collected_ads))
            if fetch_limit <= 0:
                break

            result = self.search_ads(
                search_terms=search_terms,
                country=country,
                ad_type=ad_type,
                limit=fetch_limit,
                after=after_cursor,
            )
            pages_fetched += 1
            data = result.get("data", [])
            if not isinstance(data, list) or not data:
                break

            collected_ads.extend(data)

            # Check for cursor safely
            paging = result.get("paging", {})
            cursors = paging.get("cursors", {}) if isinstance(paging, dict) else {}
            after_cursor = cursors.get("after") if isinstance(cursors, dict) else None

            if not after_cursor:
                break

        return collected_ads[:max_results]

    def get_ad_accounts(self) -> list[dict[str, Any]]:
        """Fetch authorized ad accounts for authenticated user."""
        url = f"{self.base_url}/me/adaccounts"
        params = {"fields": "account_id,id,name,currency,account_status"}
        result = self._get_with_retry(url, params=params)
        data = result.get("data", [])
        if isinstance(data, list):
            return data
        return []

    def create_campaign(self, ad_account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Create campaign in specified ad account (POST without retry)."""
        account_path = (
            f"act_{ad_account_id}" if not ad_account_id.startswith("act_") else ad_account_id
        )
        url = f"{self.base_url}/{account_path}/campaigns"
        return self._post_no_retry(url, json_payload=payload)

    def create_ad_set(self, ad_account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Create ad set in specified ad account (POST without retry)."""
        account_path = (
            f"act_{ad_account_id}" if not ad_account_id.startswith("act_") else ad_account_id
        )
        url = f"{self.base_url}/{account_path}/adsets"
        return self._post_no_retry(url, json_payload=payload)

    def create_ad(self, ad_account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Create ad in specified ad account (POST without retry)."""
        account_path = (
            f"act_{ad_account_id}" if not ad_account_id.startswith("act_") else ad_account_id
        )
        url = f"{self.base_url}/{account_path}/ads"
        return self._post_no_retry(url, json_payload=payload)
