"""Local MCP consumption and end-to-end integration test script.

Demonstrates and verifies:
1. Registration and schemas of all 12 MCP tools on the FastMCP server.
2. Public /health check endpoint over HTTP.
3. Bearer authentication middleware on the HTTP transport (401 / 403 / authenticated).
4. Direct FastMCP protocol tool execution via `mcp.call_tool` for campaign management with dry-run and financial limits.
"""

import asyncio
import json
import os

import responses
from starlette.testclient import TestClient

# Set local environment variables for the test run
os.environ["FACEBOOK_ACCESS_TOKEN"] = "EAA_TEST_LOCAL_TOKEN_12345"
os.environ["META_GRAPH_API_VERSION"] = "v26.0"
os.environ["MCP_AUTH_TOKEN"] = "local-mcp-secret-token-abcdef"
os.environ["MAX_CAMPAIGN_BUDGET"] = "10.00"
os.environ["CLOUDINARY_CLOUD_NAME"] = "local-demo-cloud"
os.environ["CLOUDINARY_API_KEY"] = "123456789"
os.environ["CLOUDINARY_API_SECRET"] = "local_secret_xyz"
os.environ["CLOUDINARY_FOLDER"] = "facebook_ads_creatives"

from app.server import app, mcp


@responses.activate
def run_local_mcp_consumption_test() -> None:
    # Setup mock for /me/adaccounts
    responses.add(
        responses.GET,
        "https://graph.facebook.com/v26.0/me/adaccounts",
        json={
            "data": [
                {
                    "account_id": "1234567890",
                    "name": "Conta Principal Brasil",
                    "currency": "BRL",
                    "account_status": 1,
                }
            ]
        },
        status=200,
    )
    print("=" * 70)
    print(" 🚀 INICIANDO TESTE DE CONSUMO LOCAL DO MCP")
    print("=" * 70)

    # 1. Inspect registered tools on FastMCP
    print("\n[1] Verificando Tools registradas no FastMCP Server...")
    tools = asyncio.run(mcp.list_tools())
    tool_names = [t.name for t in tools]
    print(f"    Total de tools registradas: {len(tool_names)}")
    for idx, name in enumerate(tool_names, start=1):
        print(f"    {idx:02d}. {name}")
    assert len(tool_names) == 12, f"Expected 12 tools, found {len(tool_names)}"

    # 2. Test Public Health Endpoint over HTTP
    print("\n[2] Testando endpoint público /health (HTTP)...")
    with TestClient(app) as client:
        health_resp = client.get("/health")
        print(f"    Status: {health_resp.status_code}")
        print(f"    Payload: {health_resp.json()}")
        assert health_resp.status_code == 200
        assert health_resp.json() == {"status": "ok"}

    # 3. Test HTTP Transport Bearer Auth
    print("\n[3] Testando segurança da camada HTTP (Bearer Token)...")
    with TestClient(app) as client:
        # Sem header de autorização -> 401
        unauth_resp = client.get("/mcp")
        print(
            f"    Requisição sem token -> Status {unauth_resp.status_code} ({unauth_resp.json().get('error')})"
        )
        assert unauth_resp.status_code == 401

        # Com token inválido -> 403
        forbidden_resp = client.get("/mcp", headers={"Authorization": "Bearer token_incorreto"})
        print(
            f"    Requisição com token inválido -> Status {forbidden_resp.status_code} ({forbidden_resp.json().get('error')})"
        )
        assert forbidden_resp.status_code == 403

        # Com token válido -> Autenticado
        auth_resp = client.get(
            "/mcp", headers={"Authorization": "Bearer local-mcp-secret-token-abcdef"}
        )
        print(
            f"    Requisição com token correto -> Autenticado com sucesso (Status {auth_resp.status_code})"
        )
        assert auth_resp.status_code != 401
        assert auth_resp.status_code != 403

    # 4. Consume Management Tools via FastMCP Protocol `mcp.call_tool`
    print("\n[4] Executando chamada FastMCP à tool 'create_campaign' (dry-run=True)...")
    camp_result = asyncio.run(
        mcp.call_tool(
            "create_campaign",
            {
                "ad_account_id": "1234567890",
                "name": "Campanha Black Friday 2026",
                "objective": "OUTCOME_SALES",
                "daily_budget": 9.90,
                "special_ad_categories": ["NONE"],
                "dry_run": True,
            },
        )
    )
    camp_data = camp_result.structured_content
    print("    Retorno estruturado via protocolo MCP:")
    print(f"    {json.dumps(camp_data, indent=6, ensure_ascii=False)}")
    assert camp_data["success"] is True
    assert camp_data["campaign"]["dry_run"] is True
    assert camp_data["campaign"]["daily_budget_subunit"] == 990

    print("\n[5] Executando chamada FastMCP à tool 'create_ad_set' com targeting validado...")
    ad_set_result = asyncio.run(
        mcp.call_tool(
            "create_ad_set",
            {
                "ad_account_id": "1234567890",
                "campaign_id": "camp_dry_run_123",
                "name": "Conjunto Brasil 25-45 Instagram/Facebook",
                "countries": ["BR"],
                "age_min": 25,
                "age_max": 45,
                "genders": 0,
                "publisher_platforms": ["facebook", "instagram"],
                "daily_budget": 5.00,
                "dry_run": True,
            },
        )
    )
    ad_set_data = ad_set_result.structured_content
    print("    Retorno estruturado via protocolo MCP:")
    print(f"    {json.dumps(ad_set_data, indent=6, ensure_ascii=False)}")
    assert ad_set_data["success"] is True
    assert ad_set_data["ad_set"]["targeting"]["age_min"] == 25
    assert ad_set_data["ad_set"]["targeting"]["age_max"] == 45

    print("\n[6] Executando chamada FastMCP à tool 'create_ad' com criativo e CTA allowlist...")
    ad_result = asyncio.run(
        mcp.call_tool(
            "create_ad",
            {
                "ad_account_id": "1234567890",
                "ad_set_id": "adset_dry_run_456",
                "image_url": "https://res.cloudinary.com/local-demo-cloud/image/upload/v1/facebook_ads_creatives/hero_banner.jpg",
                "title": "Oferta Especial de Lançamento",
                "body": "Garanta 20% de desconto hoje mesmo com frete grátis para todo o Brasil.",
                "link_url": "https://minhaloja.com.br/promocao",
                "call_to_action": "SHOP_NOW",
                "dry_run": True,
            },
        )
    )
    ad_data = ad_result.structured_content
    print("    Retorno estruturado via protocolo MCP:")
    print(f"    {json.dumps(ad_data, indent=6, ensure_ascii=False)}")
    assert ad_data["success"] is True
    assert ad_data["ad"]["call_to_action"] == "SHOP_NOW"

    print("\n" + "=" * 70)
    print(" ✅ TODOS OS TESTES DE CONSUMO LOCAL DO MCP FORAM CONCLUÍDOS COM SUCESSO!")
    print("=" * 70)


if __name__ == "__main__":
    run_local_mcp_consumption_test()
