"""Tests for creative analysis tool, SSRF prevention, and regex copy analyzer."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.crawler.creative_analyzer import analyze_creative_text
from app.tools.creative import analyze_ad_creative_elements


def test_creative_analyzer_detects_ctas_and_urgency():
    sample_copy = (
        "Aproveite nossa promoção de verão! Compre agora e garanta o seu com desconto de 30%. "
        "Últimas unidades disponíveis! Frete grátis para todo o Brasil."
    )

    result = analyze_creative_text(sample_copy)

    assert "Compre Agora" in result["cta_detected"]
    assert "Aproveite" in result["cta_detected"]
    assert "Garanta O Seu" in result["cta_detected"]
    assert any("Últimas Unidades" in u for u in result["urgency_triggers"])
    assert "Frete Grátis" in result["value_propositions"]


@pytest.mark.asyncio
async def test_analyze_creative_rejects_ssrf_urls():
    res = await analyze_ad_creative_elements(ad_id="https://attacker.com/steal")
    assert res["success"] is False
    assert res["error"]["code"] == "INVALID_INPUT"

    res_path = await analyze_ad_creative_elements(ad_id="../../etc/passwd")
    assert res_path["success"] is False
    assert res_path["error"]["code"] == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_analyze_creative_handles_crawl_failure():
    with patch("app.tools.creative.AsyncWebCrawler") as mock_crawler_cls:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.arun = AsyncMock(side_effect=RuntimeError("Browser crash"))
        mock_crawler_cls.return_value = mock_instance

        res = await analyze_ad_creative_elements(ad_id="123456789012345")
        assert res["success"] is False
        assert res["error"]["code"] == "CREATIVE_FETCH_ERROR"
        assert "correlation_id" in res["error"]


@pytest.mark.asyncio
async def test_analyze_creative_success_mock():
    with patch("app.tools.creative.AsyncWebCrawler") as mock_crawler_cls:
        mock_instance = MagicMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)

        fake_result = MagicMock()
        fake_result.success = True
        fake_result.markdown = "Super Oferta! Compre agora com frete grátis."
        fake_result.extracted_content = ""
        mock_instance.arun = AsyncMock(return_value=fake_result)
        mock_crawler_cls.return_value = mock_instance

        res = await analyze_ad_creative_elements(ad_id="9988776655")
        assert res["success"] is True
        assert res["ad_id"] == "9988776655"
        assert res["public_ad_url"] == "https://www.facebook.com/ads/library/?id=9988776655"
        assert "Compre Agora" in res["analysis"]["cta_detected"]
