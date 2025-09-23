"""Central application exception hierarchy.

This module defines the base application exception ``AppError`` and a set of
specialized subclasses used throughout the codebase to represent common
failure modes (configuration, data validation, user input, external services,
timeouts and retry exhaustion). Using a centralized hierarchy makes error
handling and testing consistent.
"""

from __future__ import annotations

from typing import Any, Mapping


class AppError(Exception):
    """Base exception for all application-level errors.

    Parameters
    ----------
    code : str
        Machine-readable error code (e.g., ``'DATA_VALIDATION_ERROR'``).
    message : str
        Human-readable message describing the error.
    context : Mapping[str, Any] | None, optional
        Optional structured context for logging.
    transient : bool, optional
        Whether the error is temporary and may be retried.

    Attributes
    ----------
    code : str
        Stable machine-readable error code.
    message : str
        Human-readable message.
    context : dict
        Structured, non-sensitive context for logging.
    transient : bool
        True if the error is transient.

    Examples
    --------
    >>> e = AppError('CODE', 'message', context={'k': 'v'}, transient=True)
    >>> e.code
    'CODE'
    """

    __slots__ = ("code", "message", "context", "transient")

    def __init__(
        self,
        code: str,
        message: str,
        *,
        context: Mapping[str, Any] | None = None,
        transient: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = dict(context or {})
        self.transient = bool(transient)

    def __str__(self) -> str:
        """Return a compact string representation of the error."""
        return f"{self.code}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Return a log-safe dictionary representation of the error."""
        return {
            "error_code": self.code,
            "message": self.message,
            "context": self.context,
            "is_transient": self.transient,
        }


class ConfigurationError(AppError):
    """Raised for invalid or missing configuration."""

    def __init__(
        self, message: str, *, context: Mapping[str, Any] | None = None
    ) -> None:
        super().__init__(
            "CONFIGURATION_ERROR", message, context=context, transient=False
        )


class DataValidationError(AppError):
    """Raised for data that fails schema or content validation."""

    def __init__(
        self, message: str, *, context: Mapping[str, Any] | None = None
    ) -> None:
        super().__init__(
            "DATA_VALIDATION_ERROR", message, context=context, transient=False
        )


class UserInputError(AppError):
    """Raised when user input is invalid or exceeds attempt limits."""

    def __init__(
        self, message: str, *, context: Mapping[str, Any] | None = None
    ) -> None:
        super().__init__("USER_INPUT_ERROR", message, context=context, transient=False)


class APIRateLimitError(AppError):
    """Raised when an external API indicates a rate limit condition."""

    def __init__(
        self, message: str, *, context: Mapping[str, Any] | None = None
    ) -> None:
        super().__init__(
            "API_RATE_LIMIT_ERROR", message, context=context, transient=True
        )


class RetryExhaustedError(AppError):
    """Raised when retry attempts for a transient error have been exhausted."""

    def __init__(
        self, message: str, *, context: Mapping[str, Any] | None = None
    ) -> None:
        super().__init__(
            "RETRY_EXHAUSTED_ERROR", message, context=context, transient=False
        )


class TimeoutExceededError(AppError):
    """Raised when a configured timeout or deadline is exceeded."""

    def __init__(
        self, message: str, *, context: Mapping[str, Any] | None = None
    ) -> None:
        super().__init__(
            "TIMEOUT_EXCEEDED_ERROR", message, context=context, transient=True
        )


class ExternalServiceError(AppError):
    """Raised for unexpected failures from an external service."""

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, Any] | None = None,
        transient: bool = True,
    ) -> None:
        super().__init__(
            "EXTERNAL_SERVICE_ERROR", message, context=context, transient=transient
        )

