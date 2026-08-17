"""Tests for CloudinaryClient, Base64 decoding, MIME filtering, and size limit checks (Q18, Q19)."""

import base64
from unittest.mock import patch

import pytest

from app.cloudinary.client import CloudinaryClient
from app.exceptions import CloudinaryNotConfiguredError
from app.tools.management import upload_creative_asset


def test_cloudinary_not_configured_error():
    client = CloudinaryClient()
    assert client.is_configured is False
    with pytest.raises(CloudinaryNotConfiguredError):
        client.upload_image(b"test_image_bytes", "sample.png", "image/png")


def test_cloudinary_upload_mock():
    client = CloudinaryClient(cloud_name="my_cloud", api_key="123", api_secret="abc")
    assert client.is_configured is True

    fake_response = {
        "public_id": "facebook_ads_creatives/sample_img",
        "secure_url": "https://res.cloudinary.com/my_cloud/image/upload/v1/sample_img.png",
        "width": 1080,
        "height": 1080,
        "bytes": 204800,
    }

    with patch("cloudinary.uploader.upload", return_value=fake_response):
        result = client.upload_image(b"fake_png_data", "sample.png", "image/png")
        assert result.asset_id == "facebook_ads_creatives/sample_img"
        assert "res.cloudinary.com" in result.public_url
        assert result.width == 1080
        assert result.bytes == 204800


def test_upload_creative_asset_invalid_mime():
    res = upload_creative_asset(
        image_base64="aGVsbG8=",
        mime_type="application/pdf",
        filename="doc.pdf",
    )
    assert res["success"] is False
    assert res["error"]["code"] == "INVALID_INPUT"


def test_upload_creative_asset_oversized_payload():
    # 11MB byte string encoded in base64
    large_raw = b"X" * (11 * 1024 * 1024)
    b64_str = base64.b64encode(large_raw).decode("utf-8")

    res = upload_creative_asset(
        image_base64=b64_str,
        mime_type="image/png",
        filename="huge.png",
    )
    assert res["success"] is False
    assert res["error"]["code"] == "INVALID_INPUT"
    assert "exceeds maximum 10MB limit" in res["error"]["message"]
