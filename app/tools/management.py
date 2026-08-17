"""Campaign management and asset upload tools (Scope C, Q13, Q15, Q18, Q22)."""

import base64
import mimetypes
import os
from typing import Any

from app.cloudinary.client import CloudinaryClient
from app.config import load_settings
from app.exceptions import (
    CloudinaryNotConfiguredError,
    InvalidInputError,
    MCPBaseException,
    format_error_response,
    generate_correlation_id,
)
from app.meta.ad_account_service import AdAccountService
from app.meta.campaign_service import CampaignService
from app.meta.client import MetaAdsClient
from app.security.redaction import sanitize_for_output
from app.security.response_limits import enforce_response_limits
from app.security.validation import ALLOWED_MIME_TYPES

MAX_IMAGE_BYTES = 10485760  # 10MB decoded limit (Q18)


def get_management_services() -> tuple[AdAccountService, CampaignService, CloudinaryClient]:
    """Instantiate campaign and cloud management services with runtime settings."""
    settings = load_settings()
    client = MetaAdsClient(
        access_token=settings.facebook_access_token or "",
        graph_api_version=settings.meta_graph_api_version,
        connect_timeout=settings.http_connect_timeout,
        read_timeout=settings.http_read_timeout,
    )
    account_service = AdAccountService(client=client)
    campaign_service = CampaignService(
        client=client,
        account_service=account_service,
        max_campaign_budget=settings.max_campaign_budget,
    )
    cloudinary_client = CloudinaryClient(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        folder=settings.cloudinary_folder,
        connect_timeout=settings.http_connect_timeout,
        read_timeout=settings.http_read_timeout,
    )
    return account_service, campaign_service, cloudinary_client


def list_ad_accounts() -> dict[str, Any]:
    """List all Meta ad accounts accessible to the authenticated token (read-only, cached 5 min)."""
    correlation_id = generate_correlation_id()
    try:
        account_service, _, _ = get_management_services()
        accounts = account_service.list_accounts()

        res = {
            "total_accounts": len(accounts),
            "accounts": [acc.model_dump() for acc in accounts],
            "success": True,
        }
        return enforce_response_limits(sanitize_for_output(res))

    except MCPBaseException as exc:
        return format_error_response(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
        )
    except Exception as exc:  # noqa: BLE001
        return format_error_response(
            code="META_API_ERROR",
            message=f"Failed to list ad accounts: {exc!s}",
            correlation_id=correlation_id,
        )


def upload_creative_asset(
    file_path: str | None = None,
    image_base64: str | None = None,
    mime_type: str | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    """Upload an image asset to Cloudinary CDN and return a public CDN URL.

    LLM USAGE GUIDANCE:
    - PREFERRED METHOD: Pass `file_path` with the path to the local image file (e.g. '/path/to/image.png' or './creatives/ad.jpg').
      The server streams the file directly from disk to Cloudinary, avoiding heavy Base64 token overhead in the conversation context.
    - FALLBACK METHOD: Pass `image_base64` only if the image is in-memory or cannot be referenced by a file path.
    - `filename` and `mime_type` are optional when `file_path` is provided (auto-detected from file).

    Parameters:
        file_path: Local filesystem path to the image file to stream (max 10MB). Preferred.
        image_base64: Base64-encoded image string (max 10MB decoded). Use only when file_path is unavailable.
        mime_type: MIME type of the image ('image/png', 'image/jpeg', 'image/webp', 'image/gif'). Optional when file_path is provided.
        filename: Friendly filename for the asset (e.g. 'hero_banner.png'). Optional when file_path is provided.
    """
    correlation_id = generate_correlation_id()
    try:
        _, _, cloud_client = get_management_services()
        if not cloud_client.is_configured:
            raise CloudinaryNotConfiguredError(correlation_id=correlation_id)

        if not file_path and not image_base64:
            raise InvalidInputError(
                "Either 'file_path' or 'image_base64' must be provided",
                correlation_id=correlation_id,
            )

        # 1. File stream upload path (Preferred)
        if file_path:
            if not isinstance(file_path, str) or not file_path.strip():
                raise InvalidInputError(
                    "file_path must be a non-empty string",
                    correlation_id=correlation_id,
                )

            resolved_path = os.path.abspath(os.path.expanduser(file_path.strip()))
            if not os.path.isfile(resolved_path):
                raise InvalidInputError(
                    f"File not found or is not a regular file: {file_path}",
                    correlation_id=correlation_id,
                )

            file_size = os.path.getsize(resolved_path)
            if file_size == 0:
                raise InvalidInputError(
                    "Image file is empty (0 bytes)",
                    correlation_id=correlation_id,
                )

            if file_size > MAX_IMAGE_BYTES:
                raise InvalidInputError(
                    f"Image size ({file_size} bytes) exceeds maximum 10MB limit ({MAX_IMAGE_BYTES} bytes)",
                    correlation_id=correlation_id,
                )

            if mime_type and mime_type.strip():
                clean_mime = mime_type.strip().lower()
            else:
                guessed_mime, _ = mimetypes.guess_type(resolved_path)
                clean_mime = (guessed_mime or "").strip().lower()

            if clean_mime not in ALLOWED_MIME_TYPES:
                raise InvalidInputError(
                    f"Invalid mime_type '{clean_mime or mime_type}'. Allowed: {sorted(ALLOWED_MIME_TYPES)}",
                    correlation_id=correlation_id,
                )

            clean_filename = (
                filename.strip() if filename and filename.strip() else os.path.basename(resolved_path)
            ) or "creative.png"

            with open(resolved_path, "rb") as file_stream:
                asset = cloud_client.upload_image_stream(
                    file_stream=file_stream,
                    filename=clean_filename,
                    mime_type=clean_mime,
                    file_size=file_size,
                )

            res = {
                "asset": asset.model_dump(),
                "success": True,
            }
            return enforce_response_limits(sanitize_for_output(res))

        # 2. Base64 payload upload path (Fallback)
        clean_mime = (mime_type or "").strip().lower()
        if clean_mime not in ALLOWED_MIME_TYPES:
            raise InvalidInputError(
                f"Invalid mime_type '{mime_type}'. Allowed: {sorted(ALLOWED_MIME_TYPES)}",
                correlation_id=correlation_id,
            )

        if not isinstance(image_base64, str) or not image_base64.strip():
            raise InvalidInputError(
                "image_base64 must be a non-empty base64 string",
                correlation_id=correlation_id,
            )

        # Strip possible data URI header if present
        raw_b64 = image_base64.strip()
        if ";base64," in raw_b64:
            raw_b64 = raw_b64.split(";base64,")[-1]

        try:
            image_bytes = base64.b64decode(raw_b64, validate=True)
        except Exception as b64_err:
            raise InvalidInputError(
                "Invalid base64 payload", correlation_id=correlation_id
            ) from b64_err

        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise InvalidInputError(
                f"Image size ({len(image_bytes)} bytes) exceeds maximum 10MB limit ({MAX_IMAGE_BYTES} bytes)",
                correlation_id=correlation_id,
            )

        asset = cloud_client.upload_image(
            image_bytes=image_bytes,
            filename=(filename or "creative.png").strip() or "creative.png",
            mime_type=clean_mime,
        )

        res = {
            "asset": asset.model_dump(),
            "success": True,
        }
        return enforce_response_limits(sanitize_for_output(res))

    except MCPBaseException as exc:
        return format_error_response(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
        )
    except Exception as exc:  # noqa: BLE001
        return format_error_response(
            code="META_API_ERROR",
            message=f"Creative upload failed: {exc!s}",
            correlation_id=correlation_id,
        )


def create_campaign(
    ad_account_id: str,
    name: str,
    objective: str,
    daily_budget: float,
    special_ad_categories: list[str] | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Create a new Facebook Ads Campaign with budget limits and dry-run safety default.

    Parameters:
        ad_account_id: Ad Account ID (digits, optionally prefixed by 'act_')
        name: Name of the campaign (1..200 characters)
        objective: Campaign objective ('OUTCOME_TRAFFIC', 'OUTCOME_ENGAGEMENT', 'OUTCOME_LEADS', 'OUTCOME_SALES', 'OUTCOME_APP_PROMOTION')
        daily_budget: Daily budget in account currency (decimal, e.g. 10.00). Must not exceed MAX_CAMPAIGN_BUDGET.
        special_ad_categories: Special categories (e.g. ['HOUSING', 'EMPLOYMENT', 'CREDIT'] or ['NONE']). Default ['NONE'].
        dry_run: If True (default), simulates the operation and returns planned payload without spending money.
    """
    correlation_id = generate_correlation_id()
    try:
        _, campaign_service, _ = get_management_services()
        result = campaign_service.create_campaign(
            ad_account_id=ad_account_id,
            name=name,
            objective=objective,
            daily_budget=daily_budget,
            special_ad_categories=special_ad_categories,
            dry_run=dry_run,
        )
        res = {
            "campaign": result.model_dump(),
            "success": True,
        }
        return enforce_response_limits(sanitize_for_output(res))

    except MCPBaseException as exc:
        return format_error_response(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
        )
    except Exception as exc:  # noqa: BLE001
        return format_error_response(
            code="META_API_ERROR",
            message=f"Campaign creation failed: {exc!s}",
            correlation_id=correlation_id,
        )


def create_ad_set(
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
) -> dict[str, Any]:
    """Create a new Ad Set with server-side targeting validation and dry-run safety default.

    Parameters:
        ad_account_id: Ad Account ID (digits, optionally prefixed by 'act_')
        campaign_id: Parent Campaign ID
        name: Name of the Ad Set (1..200 characters)
        countries: Target countries (list of 2-letter ISO codes, e.g. ['BR', 'US'])
        age_min: Minimum target age (18..65, default 18)
        age_max: Maximum target age (18..65, default 65)
        genders: Target genders: 0 = All, 1 = Male, 2 = Female (default 0)
        publisher_platforms: Platforms (e.g. ['facebook', 'instagram']). Defaults to all platforms.
        daily_budget: Optional daily budget override in account currency (decimal). Must not exceed MAX_CAMPAIGN_BUDGET.
        dry_run: If True (default), simulates creation without committing changes to Meta.
    """
    correlation_id = generate_correlation_id()
    try:
        _, campaign_service, _ = get_management_services()
        result = campaign_service.create_ad_set(
            ad_account_id=ad_account_id,
            campaign_id=campaign_id,
            name=name,
            countries=countries,
            age_min=age_min,
            age_max=age_max,
            genders=genders,
            publisher_platforms=publisher_platforms,
            daily_budget=daily_budget,
            dry_run=dry_run,
        )
        res = {
            "ad_set": result.model_dump(),
            "success": True,
        }
        return enforce_response_limits(sanitize_for_output(res))

    except MCPBaseException as exc:
        return format_error_response(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
        )
    except Exception as exc:  # noqa: BLE001
        return format_error_response(
            code="META_API_ERROR",
            message=f"Ad Set creation failed: {exc!s}",
            correlation_id=correlation_id,
        )


def create_ad(
    ad_account_id: str,
    ad_set_id: str,
    image_url: str,
    title: str,
    body: str,
    link_url: str,
    call_to_action: str,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Create an Ad with image, copy, link destination, and CTA allowlist (dry-run default).

    Parameters:
        ad_account_id: Ad Account ID (digits, optionally prefixed by 'act_')
        ad_set_id: Parent Ad Set ID
        image_url: Public HTTPS URL of the image asset (e.g. from upload_creative_asset)
        title: Headline text (1..200 characters)
        body: Ad body copy (1..2000 characters)
        link_url: Destination link (HTTPS only; never fetched by the server)
        call_to_action: Call-to-action button enum ('SHOP_NOW', 'LEARN_MORE', 'SIGN_UP', 'DOWNLOAD', 'CONTACT_US', 'GET_OFFER', 'GET_QUOTE', 'SUBSCRIBE', 'INSTALL_APP', 'BOOK_TRAVEL', 'LISTEN_NOW')
        dry_run: If True (default), simulates creation without committing changes to Meta.
    """
    correlation_id = generate_correlation_id()
    try:
        _, campaign_service, _ = get_management_services()
        result = campaign_service.create_ad(
            ad_account_id=ad_account_id,
            ad_set_id=ad_set_id,
            image_url=image_url,
            title=title,
            body=body,
            link_url=link_url,
            call_to_action=call_to_action,
            dry_run=dry_run,
        )
        res = {
            "ad": result.model_dump(),
            "success": True,
        }
        return enforce_response_limits(sanitize_for_output(res))

    except MCPBaseException as exc:
        return format_error_response(
            code=exc.code,
            message=exc.message,
            correlation_id=correlation_id,
        )
    except Exception as exc:  # noqa: BLE001
        return format_error_response(
            code="META_API_ERROR",
            message=f"Ad creation failed: {exc!s}",
            correlation_id=correlation_id,
        )
