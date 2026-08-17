"""Pytest configuration and shared test fixtures."""

import os

# Ensure safe default environment variables for testing
import pathlib

_local_home = pathlib.Path(__file__).parent.parent / ".scratch" / "home"
_local_home.mkdir(parents=True, exist_ok=True)
os.environ["HOME"] = str(_local_home)

os.environ["FACEBOOK_ACCESS_TOKEN"] = "TEST_TOKEN_SAFE_ENVIRONMENT_12345"
os.environ["META_GRAPH_API_VERSION"] = "v26.0"
os.environ["MCP_AUTH_TOKEN"] = "test-mcp-auth-token-1234567890abcdef"
os.environ["CLOUDINARY_CLOUD_NAME"] = "test-cloud"
os.environ["CLOUDINARY_API_KEY"] = "123456789012345"
os.environ["CLOUDINARY_API_SECRET"] = "test-secret-abcdef12345"
os.environ["MAX_CAMPAIGN_BUDGET"] = "10.00"
