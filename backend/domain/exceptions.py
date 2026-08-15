class PlatformBaseException(Exception):
    """Base exception class for AI Learning Platform domain."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(PlatformBaseException):
    """Raised when user input fails domain validation rules."""


class ConfigurationError(PlatformBaseException):
    """Raised when configuration files or environment variables are invalid or missing."""


class ProviderError(PlatformBaseException):
    """Raised when the LLM gateway or provider API encounters an error."""


class AuthenticationError(PlatformBaseException):
    """Raised when authentication or authorization fails."""


class InternalError(PlatformBaseException):
    """Raised when an unhandled server error occurs."""
