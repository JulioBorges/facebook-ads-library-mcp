"""Configuration and secure secret loading for Facebook Ads Intelligence MCP."""

import os
from dataclasses import dataclass
from pathlib import Path

# Gracefully load dotenv in local/dev environments if available
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def read_secret(
    file_path: str | None = None,
    env_name: str | None = None,
    default: str | None = None,
) -> str | None:
    """Load secret with dual-path strategy: file path first, then environment variable, then default."""
    if file_path:
        path = Path(file_path)
        if path.is_file():
            try:
                secret = path.read_text(encoding="utf-8").strip()
                if secret:
                    return secret
            except OSError:
                pass

    if env_name:
        env_val = os.environ.get(env_name)
        if env_val is not None and env_val.strip() != "":
            return env_val.strip()

    return default


@dataclass(frozen=True)
class Settings:
    """Application runtime settings and security boundaries."""

    # Meta Graph API
    facebook_access_token: str | None
    meta_graph_api_version: str

    # MCP Server Auth & Transport
    mcp_auth_token: str | None
    mcp_transport: str  # "stdio" or "http"
    host: str
    port: int

    # Cloudinary Credentials (Scope C)
    cloudinary_cloud_name: str | None
    cloudinary_api_key: str | None
    cloudinary_api_secret: str | None

    # Operational Limits & Financial Safeguards
    max_campaign_budget: float  # In account currency (default R$10.00)
    crawler_concurrency: int
    crawler_timeout: int
    http_connect_timeout: int
    http_read_timeout: int

    @property
    def is_cloudinary_configured(self) -> bool:
        """Check whether all required Cloudinary credentials are provided."""
        return bool(
            self.cloudinary_cloud_name and self.cloudinary_api_key and self.cloudinary_api_secret
        )

    def validate_for_startup(self) -> None:
        """Validate required configuration depending on the selected transport."""
        errors: list[str] = []

        if not self.facebook_access_token:
            errors.append("FACEBOOK_ACCESS_TOKEN is required")

        if not self.meta_graph_api_version:
            errors.append("META_GRAPH_API_VERSION is required")

        if self.mcp_transport.lower() == "http":
            if not self.mcp_auth_token:
                errors.append("MCP_AUTH_TOKEN is required in HTTP transport mode")
            if not self.is_cloudinary_configured:
                errors.append(
                    "CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, and CLOUDINARY_API_SECRET "
                    "are required in HTTP production mode"
                )

        if errors:
            raise ValueError(f"Startup configuration error: {'; '.join(errors)}")


def load_settings() -> Settings:
    """Load settings from environment variables and secret files."""
    fb_token = read_secret(
        file_path=os.environ.get("FACEBOOK_ACCESS_TOKEN_FILE"),
        env_name="FACEBOOK_ACCESS_TOKEN",
    )

    mcp_token = read_secret(
        file_path=os.environ.get("MCP_AUTH_TOKEN_FILE"),
        env_name="MCP_AUTH_TOKEN",
    )

    cloud_name = read_secret(
        file_path=os.environ.get("CLOUDINARY_CLOUD_NAME_FILE"),
        env_name="CLOUDINARY_CLOUD_NAME",
    )
    cloud_key = read_secret(
        file_path=os.environ.get("CLOUDINARY_API_KEY_FILE"),
        env_name="CLOUDINARY_API_KEY",
    )
    cloud_secret = read_secret(
        file_path=os.environ.get("CLOUDINARY_API_SECRET_FILE"),
        env_name="CLOUDINARY_API_SECRET",
    )

    meta_version = os.environ.get("META_GRAPH_API_VERSION", "v26.0").strip()

    try:
        max_budget = float(os.environ.get("MAX_CAMPAIGN_BUDGET", "10.00"))
    except ValueError:
        max_budget = 10.00

    try:
        port = int(os.environ.get("PORT", "8000"))
    except ValueError:
        port = 8000

    return Settings(
        facebook_access_token=fb_token,
        meta_graph_api_version=meta_version,
        mcp_auth_token=mcp_token,
        mcp_transport=os.environ.get("MCP_TRANSPORT", "stdio").lower().strip(),
        host=os.environ.get("HOST", "0.0.0.0").strip(),
        port=port,
        cloudinary_cloud_name=cloud_name,
        cloudinary_api_key=cloud_key,
        cloudinary_api_secret=cloud_secret,
        max_campaign_budget=max_budget,
        crawler_concurrency=int(os.environ.get("CRAWLER_CONCURRENCY", "1")),
        crawler_timeout=int(os.environ.get("CRAWLER_TIMEOUT", "45")),
        http_connect_timeout=int(os.environ.get("HTTP_CONNECT_TIMEOUT", "5")),
        http_read_timeout=int(os.environ.get("HTTP_READ_TIMEOUT", "30")),
    )
