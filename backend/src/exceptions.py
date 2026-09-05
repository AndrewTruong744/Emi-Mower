"""
Custom Domain Exceptions for Emi-Mower Backend.
"""


class BaseAppException(Exception):
    """Base exception for all application domain errors."""

    pass


class RepositoryError(BaseAppException):
    """Raised when a database query or Valkey operation fails."""

    pass


class NotFoundError(BaseAppException):
    """Raised when a requested resource (User, Mower, Yard) is not found."""

    pass


class UserNotFoundError(NotFoundError):
    """Raised when a specified user does not exist."""

    pass


class MowerNotFoundError(NotFoundError):
    """Raised when a specified mower does not exist."""

    pass


class ForbiddenError(BaseAppException):
    """Raised when a user performs an operation they do not have permission for."""

    pass


class OwnershipError(ForbiddenError):
    """Raised when ownership verification fails."""

    pass


class ValidationError(BaseAppException):
    """Raised when input validation fails (e.g., non-alphanumeric names)."""

    pass


class ExternalServiceError(BaseAppException):
    """Raised when an external service call fails (e.g., the Zenoh REST API)."""

    pass


class TokenGenerationError(BaseAppException):
    """Raised when JWT or security token generation fails."""

    pass


class AuthenticationError(BaseAppException):
    """Raised when user token verification or GCP Identity authentication fails."""

    pass

