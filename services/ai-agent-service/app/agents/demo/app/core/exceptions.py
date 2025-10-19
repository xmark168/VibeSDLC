"""
Custom exception classes for the application.
Provides structured error handling with proper HTTP status codes.
"""

from typing import Any


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(AppException):
    """Validation error exception."""

    def __init__(
        self,
        message: str = "Validation failed",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details,
        )


class AuthenticationException(AppException):
    """Authentication error exception."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details,
        )


class AuthorizationException(AppException):
    """Authorization error exception."""

    def __init__(
        self,
        message: str = "Access denied",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            details=details,
        )


class NotFoundException(AppException):
    """Resource not found exception."""

    def __init__(
        self,
        message: str = "Resource not found",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=details,
        )


class ConflictException(AppException):
    """Resource conflict exception."""

    def __init__(
        self,
        message: str = "Resource conflict",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details,
        )


class RateLimitException(AppException):
    """Rate limit exceeded exception."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details,
        )


class ExternalServiceException(AppException):
    """External service error exception."""

    def __init__(
        self,
        message: str = "External service error",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=502,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=details,
        )

class EmailVerificationException(AppException):
    """Email verification error exception."""

    def __init__(
        self,
        message: str = "Email verification failed",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code="EMAIL_VERIFICATION_ERROR",
            details=details,
        )


class PasswordResetException(AppException):
    """Password reset error exception."""

    def __init__(
        self,
        message: str = "Password reset failed",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=400,
            error_code="PASSWORD_RESET_ERROR",
            details=details,
        )