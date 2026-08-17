"""CloudinaryClient: Thin isolated client for uploading creative assets (Q18, Q19, Q31).

Upload is implemented as a direct signed HTTPS POST via `requests` instead of the
`cloudinary` SDK's built-in uploader. The SDK's upload path relies on a module-level
urllib3 pool that is created once at import time and applies urllib3's default retry
policy underneath, which can silently retry a stalled/blocked connection multiple
times before giving up -- multiplying the `timeout` we pass in well past what a
caller expects (observed in production: a ~600 byte test upload still hadn't
returned after 60s, well beyond the SDK's own `timeout=30` we were setting).

Talking to the Cloudinary REST API directly with `requests` gives us the same
explicit, single-attempt, short-timeout behavior already used for `MetaAdsClient`
(including disabling `trust_env` so a misconfigured system/corporate proxy can't
silently stall the connection instead of failing fast).
"""

import hashlib
import time
from typing import BinaryIO

import requests

from app.exceptions import CloudinaryNotConfiguredError, CloudinaryUploadError
from app.meta.schemas import SafeAssetResult

UPLOAD_URL_TEMPLATE = "https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"


class CloudinaryClient:
    """Isolated Cloudinary client preventing credential leakage and managing media assets."""

    def __init__(
        self,
        cloud_name: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
        folder: str = "facebook_ads_creatives",
        connect_timeout: int = 8,
        read_timeout: int = 20,
    ):
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.folder = folder
        # Deliberately short and non-retried: a single attempt that fails fast is
        # far more useful to a caller than one that hangs near the MCP tool's own
        # ~60s timeout ceiling (see module docstring).
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout

    @property
    def is_configured(self) -> bool:
        """Check whether Cloudinary credentials are fully set."""
        return bool(self.cloud_name and self.api_key and self.api_secret)

    def _signature(self, params_to_sign: dict[str, object]) -> str:
        """Compute Cloudinary's required SHA-1 signature over sorted params + api_secret."""
        to_sign = "&".join(f"{k}={v}" for k, v in sorted(params_to_sign.items()))
        return hashlib.sha1((to_sign + (self.api_secret or "")).encode("utf-8")).hexdigest()

    def _post_upload(
        self,
        file_field: tuple[str, BinaryIO | bytes, str],
        mime_type: str,
        folder: str | None,
        fallback_bytes: int | None,
    ) -> SafeAssetResult:
        """Perform the signed multipart POST to Cloudinary with a strict, non-retried timeout."""
        if not self.is_configured:
            raise CloudinaryNotConfiguredError()

        target_folder = folder or self.folder
        timestamp = int(time.time())
        signature = self._signature({"timestamp": timestamp, "folder": target_folder})

        data = {
            "timestamp": timestamp,
            "folder": target_folder,
            "api_key": self.api_key,
            "signature": signature,
        }

        session = requests.Session()
        # Bypass any misconfigured system/corporate proxy that could otherwise
        # stall the connection silently (same fix already applied to MetaAdsClient).
        session.trust_env = False

        try:
            response = session.post(
                UPLOAD_URL_TEMPLATE.format(cloud_name=self.cloud_name),
                data=data,
                files={"file": file_field},
                timeout=(self.connect_timeout, self.read_timeout),
            )
        except requests.RequestException as exc:
            raise CloudinaryUploadError(
                "Could not reach Cloudinary within the configured timeout "
                f"(connect={self.connect_timeout}s, read={self.read_timeout}s). "
                "This usually means a network, VPN, or proxy/firewall is blocking "
                f"api.cloudinary.com. Underlying error: {exc!s}"
            ) from exc
        finally:
            session.close()

        try:
            payload = response.json()
        except ValueError as exc:
            raise CloudinaryUploadError(
                f"Cloudinary returned a non-JSON response (HTTP {response.status_code})"
            ) from exc

        if response.status_code >= 400 or "error" in payload:
            error_field = payload.get("error")
            err_message = (
                error_field.get("message") if isinstance(error_field, dict) else str(error_field)
            )
            raise CloudinaryUploadError(
                f"Cloudinary upload failed (HTTP {response.status_code}): "
                f"{err_message or 'unknown error'}"
            )

        return SafeAssetResult(
            asset_id=str(payload.get("public_id", "")),
            public_url=str(payload.get("secure_url", "")),
            mime_type=mime_type,
            width=payload.get("width"),
            height=payload.get("height"),
            bytes=int(payload.get("bytes") or fallback_bytes or 0),
        )

    def upload_image(
        self,
        image_bytes: bytes,
        filename: str,
        mime_type: str,
        folder: str | None = None,
    ) -> SafeAssetResult:
        """Upload raw image bytes to Cloudinary with a strict, non-retried timeout."""
        return self._post_upload(
            file_field=(filename, image_bytes, mime_type),
            mime_type=mime_type,
            folder=folder,
            fallback_bytes=len(image_bytes),
        )

    def upload_image_stream(
        self,
        file_stream: BinaryIO,
        filename: str,
        mime_type: str,
        folder: str | None = None,
        file_size: int | None = None,
    ) -> SafeAssetResult:
        """Upload image from a binary file stream to Cloudinary with a strict, non-retried timeout."""
        return self._post_upload(
            file_field=(filename, file_stream, mime_type),
            mime_type=mime_type,
            folder=folder,
            fallback_bytes=file_size,
        )
