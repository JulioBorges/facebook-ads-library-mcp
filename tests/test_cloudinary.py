"""Tests for CloudinaryClient, file streaming, Base64 decoding, MIME filtering, and size limits (Q18, Q19)."""

import base64
import io
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
    with pytest.raises(CloudinaryNotConfiguredError):
        client.upload_image_stream(io.BytesIO(b"test_image_bytes"), "sample.png", "image/png")


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

    with patch("cloudinary.uploader.upload", return_value=fake_response) as mock_upload:
        result = client.upload_image(b"fake_png_data", "sample.png", "image/png")
        assert result.asset_id == "facebook_ads_creatives/sample_img"
        assert "res.cloudinary.com" in result.public_url
        assert result.width == 1080
        assert result.bytes == 204800
        mock_upload.assert_called_once()
        assert mock_upload.call_args[1]["folder"] == "facebook_ads_creatives"


def test_cloudinary_upload_stream_mock():
    client = CloudinaryClient(cloud_name="my_cloud", api_key="123", api_secret="abc")
    fake_response = {
        "public_id": "facebook_ads_creatives/stream_sample",
        "secure_url": "https://res.cloudinary.com/my_cloud/image/upload/v1/stream_sample.png",
        "width": 1200,
        "height": 628,
        "bytes": 150000,
    }

    stream = io.BytesIO(b"binary_stream_data")
    with patch("cloudinary.uploader.upload", return_value=fake_response) as mock_upload:
        result = client.upload_image_stream(
            file_stream=stream,
            filename="banner.png",
            mime_type="image/png",
            file_size=150000,
        )
        assert result.asset_id == "facebook_ads_creatives/stream_sample"
        assert result.public_url == fake_response["secure_url"]
        assert result.width == 1200
        assert result.bytes == 150000
        mock_upload.assert_called_once()


def test_cloudinary_upload_custom_folder():
    client = CloudinaryClient(
        cloud_name="my_cloud",
        api_key="123",
        api_secret="abc",
        folder="exclusive_campaign_assets",
    )
    fake_response = {
        "public_id": "exclusive_campaign_assets/sample_img",
        "secure_url": "https://res.cloudinary.com/my_cloud/image/upload/v1/exclusive_campaign_assets/sample_img.png",
        "width": 800,
        "height": 600,
        "bytes": 102400,
    }

    with patch("cloudinary.uploader.upload", return_value=fake_response) as mock_upload:
        result = client.upload_image(b"fake_png_data", "sample.png", "image/png")
        assert result.asset_id == "exclusive_campaign_assets/sample_img"
        assert mock_upload.call_args[1]["folder"] == "exclusive_campaign_assets"


def test_upload_creative_asset_missing_both_args():
    res = upload_creative_asset()
    assert res["success"] is False
    assert res["error"]["code"] == "INVALID_INPUT"
    assert "Either 'file_path' or 'image_base64' must be provided" in res["error"]["message"]


def test_upload_creative_asset_file_stream_success(tmp_path, monkeypatch):
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "my_cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "123")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "abc")

    test_file = tmp_path / "creative_banner.png"
    test_file.write_bytes(b"fake_png_image_content")

    fake_response = {
        "public_id": "facebook_ads_creatives/creative_banner",
        "secure_url": "https://res.cloudinary.com/my_cloud/image/upload/v1/creative_banner.png",
        "width": 1080,
        "height": 1080,
        "bytes": len(b"fake_png_image_content"),
    }

    with patch("cloudinary.uploader.upload", return_value=fake_response):
        res = upload_creative_asset(file_path=str(test_file))
        assert res["success"] is True
        assert res["asset"]["asset_id"] == "facebook_ads_creatives/creative_banner"
        assert res["asset"]["public_url"] == fake_response["secure_url"]
        assert res["asset"]["mime_type"] == "image/png"


def test_upload_creative_asset_file_not_found(monkeypatch):
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "my_cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "123")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "abc")

    res = upload_creative_asset(file_path="/non/existent/path/ad_image.png")
    assert res["success"] is False
    assert res["error"]["code"] == "INVALID_INPUT"
    assert "File not found" in res["error"]["message"]


def test_upload_creative_asset_file_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "my_cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "123")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "abc")

    empty_file = tmp_path / "empty.png"
    empty_file.write_bytes(b"")

    res = upload_creative_asset(file_path=str(empty_file))
    assert res["success"] is False
    assert res["error"]["code"] == "INVALID_INPUT"
    assert "empty" in res["error"]["message"]


def test_upload_creative_asset_file_invalid_mime(tmp_path, monkeypatch):
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "my_cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "123")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "abc")

    pdf_file = tmp_path / "document.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 test")

    res = upload_creative_asset(file_path=str(pdf_file))
    assert res["success"] is False
    assert res["error"]["code"] == "INVALID_INPUT"
    assert "Invalid mime_type" in res["error"]["message"]


def test_upload_creative_asset_file_oversized(tmp_path, monkeypatch):
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "my_cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "123")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "abc")

    large_file = tmp_path / "huge.png"
    # Write 11MB file
    large_file.write_bytes(b"X" * (11 * 1024 * 1024))

    res = upload_creative_asset(file_path=str(large_file))
    assert res["success"] is False
    assert res["error"]["code"] == "INVALID_INPUT"
    assert "exceeds maximum 10MB limit" in res["error"]["message"]


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

