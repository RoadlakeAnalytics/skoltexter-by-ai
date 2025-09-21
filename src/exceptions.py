# src/exceptions.py
"""Centralized application error hierarchy.

This module defines a consistent, structured set of exception classes for the
application. All application-level errors should inherit from the base ``AppError``.
Third-party exceptions should be caught at the application boundary and
re-raised as one of these specific types to create a clear and stable
error taxonomy.

This module is part of the core pipeline layer (``src/pipeline/``) and provides
the canonical exceptions used throughout the application.
"""

from __future__ import annotations

from typing import Any, Mapping


class AppError(Exception):
    """Base class for all application-level errors.

    Attributes
    ----------
    code : str
        A stable, machine-readable error code (e.g., 'DATA_VALIDATION_ERROR').
    message : str
        A human-readable message suitable for logs and user feedback.
    context : Mapping[str, Any]
        Structured, non-sensitive details for logging (e.g., file names, IDs).
    transient : bool
        True if the error is temporary and a retry might succeed.
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
        """Initialize the application error.

        Parameters
        ----------
        code : str
            Stable machine-readable error code.
        message : str
            Human-readable message without secrets.
        context : Mapping[str, Any] | None, optional
            Structured, non-sensitive details for logging.
        transient : bool, optional
            True if the error is temporary and retries may succeed.

        Returns
        -------
        None
            This constructor does not return a value.

        Examples
        --------
        >>> e = AppError('DATA_VALIDATION_ERROR', 'Missing column', context={'file': 'a.csv'})
        >>> isinstance(e, Exception)
        True
        """
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = dict(context or {})
        self.transient = bool(transient)

    def __str__(self) -> str:
        """Return a string representation of the error.

        The returned string contains the machine-readable error code and the
        human-readable message.

        Returns
        -------
        str
            Formatted string like ``'CODE: message'``.

        Examples
        --------
        >>> e = AppError('E', 'msg')
        >>> print(str(e))
        E: msg
        """
        return f"{self.code}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Render a log-safe dictionary payload of the error.

        Returns
        -------
        dict[str, Any]
            Dictionary with keys ``error_code``, ``message``, ``context`` and
            ``is_transient`` suitable for structured logging.

        Examples
        --------
        >>> e = AppError('CODE', 'message', context={'k': 'v'}, transient=True)
        >>> d = e.to_dict()
        >>> d['error_code']
        'CODE'
        """
        return {
            "error_code": self.code,
            "message": self.message,
            "context": self.context,
            "is_transient": self.transient,
        }


# --- Specific, concrete error types ---

class ConfigurationError(AppError):
    """Raised for invalid or missing configuration."""

    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        """Initialize a ConfigurationError.

        Parameters
        ----------
        message : str
            Human-readable error message describing what is wrong in the
            configuration.
        context : Mapping[str, Any] | None, optional
            Optional structured context for logging (e.g., which key or file
            failed validation).

        Returns
        -------
        None

        Examples
        --------
        >>> e = ConfigurationError('Missing API key')
        >>> isinstance(e, ConfigurationError)
        True
        """
        super().__init__("CONFIGURATION_ERROR", message, context=context, transient=False)


class DataValidationError(AppError):
    """Raised for data that fails schema or content validation."""

    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        """Initialize a DataValidationError.

        Parameters
        ----------
        message : str
            Description of the validation failure.
        context : Mapping[str, Any] | None, optional
            Contextual information such as row number or filename.

        Returns
        -------
        None

        Examples
        --------
        >>> e = DataValidationError('Missing column: name')
        >>> isinstance(e, DataValidationError)
        True
        """
        super().__init__("DATA_VALIDATION_ERROR", message, context=context, transient=False)


class UserInputError(AppError):
    """Raised when user input is invalid or exceeds attempt limits."""

    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        """Initialize a UserInputError.

        Parameters
        ----------
        message : str
            Explanation of why the input is invalid or which limit was
            exceeded.
        context : Mapping[str, Any] | None, optional
            Optional context about the input attempt (e.g., attempt count).

        Returns
        -------
        None

        Examples
        --------
        >>> e = UserInputError('Too many attempts')
        >>> isinstance(e, UserInputError)
        True
        """
        super().__init__("USER_INPUT_ERROR", message, context=context, transient=False)


class APIRateLimitError(AppError):
    """Raised when an external API signals a rate limit has been hit."""

    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        """Initialize an APIRateLimitError.

        Parameters
        ----------
        message : str
            Message describing the rate limit condition (e.g., headers or
            reset time if available).
        context : Mapping[str, Any] | None, optional
            Contextual details from the API response.

        Returns
        -------
        None

        Examples
        --------
        >>> e = APIRateLimitError('429 Too Many Requests')
        >>> isinstance(e, APIRateLimitError)
        True
        """
        super().__init__("API_RATE_LIMIT_ERROR", message, context=context, transient=True)


class RetryExhaustedError(AppError):
    """Raised when all retry attempts for a transient error have failed."""

    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        """Initialize a RetryExhaustedError.

        Parameters
        ----------
        message : str
            Message explaining which operation exhausted its retries.
        context : Mapping[str, Any] | None, optional
            Optional debugging context such as last exception details.

        Returns
        -------
        None

        Examples
        --------
        >>> e = RetryExhaustedError('Retries exhausted contacting AI service')
        >>> isinstance(e, RetryExhaustedError)
        True
        """
        super().__init__("RETRY_EXHAUSTED_ERROR", message, context=context, transient=False)


class TimeoutExceededError(AppError):
    """Raised when a configured timeout or deadline is exceeded."""

    def __init__(self, message: str, *, context: Mapping[str, Any] | None = None) -> None:
        """Initialize a TimeoutExceededError.

        Parameters
        ----------
        message : str
            Explanation of which timeout was exceeded (operation and value).
        context : Mapping[str, Any] | None, optional
            Optional context such as configured timeout value.

        Returns
        -------
        None

        Examples
        --------
        >>> e = TimeoutExceededError('Request timed out after 10s')
        >>> isinstance(e, TimeoutExceededError)
        True
        """
        super().__init__("TIMEOUT_EXCEEDED_ERROR", message, context=context, transient=True)


class ExternalServiceError(AppError):
    """Raised for unexpected errors from an external service (e.g., HTTP 5xx)."""

    def __init__(
        self,
        message: str,
        *,
        context: Mapping[str, Any] | None = None,
        transient: bool = True,
    ) -> None:
        """Initialize an ExternalServiceError.

        Parameters
        ----------
        message : str
            Message describing the external failure (status code, body,
            or other diagnostic information).
        context : Mapping[str, Any] | None, optional
            Optional context from the external service response.
        transient : bool, optional
            Whether this external failure is considered transient and
            therefore retryable.

        Returns
        -------
        None

        Examples
        --------
        >>> e = ExternalServiceError('HTTP 502 Bad Gateway')
        >>> isinstance(e, ExternalServiceError)
        True
        """
        super().__init__("EXTERNAL_SERVICE_ERROR", message, context=context, transient=transient)
