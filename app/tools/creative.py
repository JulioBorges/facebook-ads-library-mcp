"""Creative analysis tool using hardened Crawl4AI and regex analysis (SEC-005, Q6, Q8, Q30)."""

import asyncio
from typing import Any

from crawl4ai import AsyncWebCrawler

from app.crawler.browser_config import get_browser_config, get_crawler_run_config
from app.crawler.creative_analyzer import analyze_creative_text
from app.exceptions import (
    CreativeFetchError,
    MCPBaseException,
    format_error_response,
    generate_correlation_id,
)
from app.security.redaction import sanitize_for_output
from app.security.response_limits import enforce_response_limits
from app.security.url_policy import build_public_ad_url, is_safe_facebook_url
from app.security.validation import validate_ad_id

# Concurrency limiter enforcing max 1 concurrent crawler execution (§45)
CRAWLER_SEMAPHORE = asyncio.Semaphore(1)


async def analyze_ad_creative_elements(
    ad_id: str,
    extract_text: bool = True,
    detect_cta: bool = True,
) -> dict[str, Any]:
    """Analyze ad creative elements from Facebook Ads Library by ad ID.

    Parameters:
        ad_id: Numeric Facebook Ad ID (1..32 digits). URLs and arbitrary paths are strictly rejected.
        extract_text: Whether to include extracted copy/text (default True).
        detect_cta: Whether to perform regex analysis for CTAs and urgency triggers (default True).
    """
    correlation_id = generate_correlation_id()
    try:
        valid_ad_id = validate_ad_id(ad_id)
        target_url = build_public_ad_url(valid_ad_id)

        if not is_safe_facebook_url(target_url):
            raise CreativeFetchError(
                "Constructed URL failed security policy", correlation_id=correlation_id
            )

        try:
            async with (
                CRAWLER_SEMAPHORE,
                AsyncWebCrawler(config=get_browser_config()) as crawler,
            ):
                run_config = get_crawler_run_config(timeout_seconds=40)
                result = await asyncio.wait_for(
                    crawler.arun(url=target_url, config=run_config),
                    timeout=45.0,
                )
        except Exception as crawl_err:
            raise CreativeFetchError(
                f"Creative crawling failed: {crawl_err!s}",
                correlation_id=correlation_id,
            ) from crawl_err

        if not result or not result.success:
            raise CreativeFetchError(
                "Unable to render or extract creative content",
                correlation_id=correlation_id,
            )

        extracted_text = result.markdown or result.extracted_content or ""
        analysis = analyze_creative_text(extracted_text) if detect_cta else None

        response_data: dict[str, Any] = {
            "ad_id": valid_ad_id,
            "public_ad_url": target_url,
            "success": True,
        }
        if extract_text:
            response_data["extracted_text"] = extracted_text
        if detect_cta:
            response_data["analysis"] = analysis

        return enforce_response_limits(sanitize_for_output(response_data))

    except MCPBaseException as exc:
        return format_error_response(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
        )
    except Exception as exc:  # noqa: BLE001
        return format_error_response(
            code="CREATIVE_FETCH_ERROR",
            message=f"Creative analysis encountered an error: {exc!s}",
            correlation_id=correlation_id,
        )
