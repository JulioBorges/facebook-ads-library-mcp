"""FastMCP Server initialization, tool registration, HTTP Bearer auth, and entrypoints (Q4, Q32, Q33, Q34)."""

import secrets
from typing import Any

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import load_settings
from app.tools.competitive import competitive_ad_analysis, discover_competitor_brands
from app.tools.creative import analyze_ad_creative_elements
from app.tools.export import export_facebook_ads_data
from app.tools.management import (
    create_ad,
    create_ad_set,
    create_campaign,
    list_ad_accounts,
    upload_creative_asset,
)
from app.tools.reporting import (
    analyze_ad_performance_metrics,
    generate_facebook_intelligence_report,
)
from app.tools.search import search_facebook_ads

# Initialize FastMCP Server with official name from spec (Q32)
mcp = FastMCP("Facebook Ads Intelligence MCP")


# --- Public Health Route (Q33) ---
@mcp.custom_route("/health", methods=["GET"])
async def health_endpoint(request: Request) -> Response:
    """Public health endpoint returning strictly {'status': 'ok'} (Q33)."""
    return JSONResponse({"status": "ok"})


# --- Register Reading Tools (Q2, §17.1) ---
mcp.tool(
    name="search_facebook_ads",
    description="Search Facebook Ads Library by brand name or keyword.",
)(search_facebook_ads)

mcp.tool(
    name="discover_competitor_brands",
    description="Discover active competitor brands running ads in an industry.",
)(discover_competitor_brands)

mcp.tool(
    name="analyze_ad_creative_elements",
    description="Analyze ad creative copy, CTAs, and urgency triggers by ad ID.",
)(analyze_ad_creative_elements)

mcp.tool(
    name="analyze_ad_performance_metrics",
    description="Calculate aggregated ad metrics and platform distributions across a time period.",
)(analyze_ad_performance_metrics)

mcp.tool(
    name="competitive_ad_analysis",
    description="Compare ad volume, platforms, and creative samples across up to 10 brands.",
)(competitive_ad_analysis)

mcp.tool(
    name="generate_facebook_intelligence_report",
    description="Consolidate brand intelligence and competitor landscape into a report.",
)(generate_facebook_intelligence_report)

mcp.tool(
    name="export_facebook_ads_data",
    description="Export ad records in JSON, CSV (formula-injection safe), or Markdown format.",
)(export_facebook_ads_data)


# --- Register Management & Writing Tools (Scope C, Q13, Q15, §17.2) ---
mcp.tool(
    name="list_ad_accounts",
    description="List authorized Meta ad accounts (read-only, cached 5 min).",
)(list_ad_accounts)

mcp.tool(
    name="upload_creative_asset",
    description="Upload an image via Base64 to Cloudinary and receive a public CDN URL (max 10MB).",
)(upload_creative_asset)

mcp.tool(
    name="create_campaign",
    description="Create a new Facebook Ads Campaign with daily budget limits and dry-run safety default.",
)(create_campaign)

mcp.tool(
    name="create_ad_set",
    description="Create a new Ad Set with server-side targeting validation and dry-run safety default.",
)(create_ad_set)

mcp.tool(
    name="create_ad",
    description="Create an Ad with image, copy, link destination, and CTA allowlist (dry-run default).",
)(create_ad)


class BearerAuthMiddleware:
    """ASGI Middleware enforcing constant-time Bearer token verification against MCP_AUTH_TOKEN (Q4, §29)."""

    def __init__(self, app_instance: Any, auth_token: str | None = None):
        self.app = app_instance
        self.auth_token = auth_token

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return

        if scope["type"] == "http":
            path = scope.get("path", "")
            # /health route is strictly public (Q33)
            if path == "/health":
                await self.app(scope, receive, send)
                return

            if not self.auth_token:
                response = JSONResponse(
                    {"error": "MCP_AUTH_TOKEN is not configured on the server"},
                    status_code=401,
                )
                await response(scope, receive, send)
                return

            headers = dict(scope.get("headers", []))
            auth_header = headers.get(b"authorization", b"").decode("utf-8").strip()

            if not auth_header.startswith("Bearer "):
                response = JSONResponse(
                    {"error": "Missing or invalid Authorization header. Expected Bearer token."},
                    status_code=401,
                )
                await response(scope, receive, send)
                return

            incoming_token = auth_header[7:].strip()
            if not secrets.compare_digest(incoming_token, self.auth_token):
                response = JSONResponse(
                    {"error": "Forbidden: Invalid MCP authentication token"}, status_code=403
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


def create_asgi_app() -> Any:
    """Create ASGI application for HTTP transport with Bearer token authentication."""
    settings = load_settings()
    raw_http_app = mcp.http_app(path="/mcp")
    return BearerAuthMiddleware(raw_http_app, auth_token=settings.mcp_auth_token)


# Expose `app` at module level for uvicorn runtime: `uvicorn app.server:app`
app = create_asgi_app()


def main() -> None:
    """Entrypoint supporting stdio and http transports (Q4, Q34)."""
    settings = load_settings()
    settings.validate_for_startup()

    if settings.mcp_transport == "http":
        import uvicorn

        uvicorn.run(
            "app.server:app",
            host=settings.host,
            port=settings.port,
            log_level="info",
        )
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
