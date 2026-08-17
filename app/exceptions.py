"""Standardized exception hierarchy and error formatting for Facebook Ads Intelligence MCP."""

import uuid
from typing import Any


def generate_correlation_id() -> str:
    """Generate a unique 16-character hexadecimal correlation ID for request tracing."""
    return uuid.uuid4().hex[:16]


class MCPBaseException(Exception):
    """Base exception for all domain and security errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        correlation_id: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.correlation_id = correlation_id or generate_correlation_id()

    def to_dict(self) -> dict[str, Any]:
        from app.security.redaction import sanitize_for_output

        return sanitize_for_output(
            {
                "success": False,
                "error": {
                    "code": self.code,
                    "message": self.message,
                    "correlation_id": self.correlation_id,
                },
            }
        )


class MetaAPIError(MCPBaseException):
    """Raised when Meta Graph API returns an error or unexpected status code."""

    def __init__(self, message: str, correlation_id: str | None = None):
        super().__init__(
            message=message,
            code="META_API_ERROR",
            correlation_id=correlation_id,
        )


class CreativeFetchError(MCPBaseException):
    """Raised when crawling or fetching creative elements fails."""

    def __init__(self, message: str = "Creative fetch failed", correlation_id: str | None = None):
        super().__init__(
            message=message,
            code="CREATIVE_FETCH_ERROR",
            correlation_id=correlation_id,
        )


class ResponseTooLargeError(MCPBaseException):
    """Raised when a response exceeds the maximum allowed payload byte size."""

    def __init__(
        self,
        message: str = "Response payload exceeds maximum allowed size (1MB). Please reduce limit.",
        correlation_id: str | None = None,
    ):
        super().__init__(
            message=message,
            code="RESPONSE_TOO_LARGE",
            correlation_id=correlation_id,
        )


class CloudinaryNotConfiguredError(MCPBaseException):
    """Raised when an asset upload tool is called but Cloudinary credentials are missing."""

    def __init__(
        self,
        message: str = "Cloudinary credentials are not configured",
        correlation_id: str | None = None,
    ):
        super().__init__(
            message=message,
            code="CLOUDINARY_NOT_CONFIGURED",
            correlation_id=correlation_id,
        )


class CloudinaryUploadError(MCPBaseException):
    """Raised when the Cloudinary upload request fails, times out, or is unreachable."""

    def __init__(self, message: str, correlation_id: str | None = None):
        super().__init__(
            message=message,
            code="CLOUDINARY_UPLOAD_ERROR",
            correlation_id=correlation_id,
        )


class InvalidInputError(MCPBaseException):
    """Raised when an input parameter violates schema, type, or security validation rules."""

    def __init__(self, message: str, correlation_id: str | None = None):
        super().__init__(
            message=message,
            code="INVALID_INPUT",
            correlation_id=correlation_id,
        )


class AdAccountNotFoundError(MCPBaseException):
    """Raised when an ad account ID is not found in authorized user accounts."""

    def __init__(self, message: str, correlation_id: str | None = None):
        super().__init__(
            message=message,
            code="AD_ACCOUNT_NOT_FOUND",
            correlation_id=correlation_id,
        )


class BudgetExceededError(MCPBaseException):
    """Raised when a campaign or ad set daily budget exceeds MAX_CAMPAIGN_BUDGET."""

    def __init__(self, message: str, correlation_id: str | None = None):
        super().__init__(
            message=message,
            code="BUDGET_EXCEEDED",
            correlation_id=correlation_id,
        )


def format_error_response(
    code: str,
    message: str,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Format standardized error dictionary without exposing sensitive internal details."""
    from app.security.redaction import sanitize_for_output

    raw_response = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "correlation_id": correlation_id or generate_correlation_id(),
        },
    }
    return sanitize_for_output(raw_response)
