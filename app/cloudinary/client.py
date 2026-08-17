"""CloudinaryClient: Thin isolated client for uploading creative assets (Q18, Q19, Q31)."""

import cloudinary
import cloudinary.uploader

from app.exceptions import CloudinaryNotConfiguredError
from app.meta.schemas import SafeAssetResult


class CloudinaryClient:
    """Isolated Cloudinary client preventing credential leakage and managing media assets."""

    def __init__(
        self,
        cloud_name: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
    ):
        self.cloud_name = cloud_name
        self.api_key = api_key
        self.api_secret = api_secret

    @property
    def is_configured(self) -> bool:
        """Check whether Cloudinary credentials are fully set."""
        return bool(self.cloud_name and self.api_key and self.api_secret)

    def upload_image(
        self,
        image_bytes: bytes,
        filename: str,
        mime_type: str,
        folder: str = "facebook_ads_creatives",
    ) -> SafeAssetResult:
        """Upload raw image bytes to Cloudinary with strict timeouts and safe response formatting."""
        if not self.is_configured:
            raise CloudinaryNotConfiguredError()

        cloudinary.config(
            cloud_name=self.cloud_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            secure=True,
        )

        response = cloudinary.uploader.upload(
            image_bytes,
            folder=folder,
            resource_type="image",
            use_filename=True,
            filename_override=filename,
            timeout=30,
        )

        return SafeAssetResult(
            asset_id=str(response.get("public_id", "")),
            public_url=str(response.get("secure_url", "")),
            mime_type=mime_type,
            width=response.get("width"),
            height=response.get("height"),
            bytes=int(response.get("bytes", len(image_bytes))),
        )
