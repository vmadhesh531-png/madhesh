"""Custom exceptions for the application."""

from typing import Optional


class AIBillException(Exception):
    """Base exception for AI Bill module."""

    def __init__(self, message: str, status_code: int = 500, details: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ImageValidationError(AIBillException):
    """Raised when image validation fails."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, status_code=400, details=details)


class ImageProcessingError(AIBillException):
    """Raised when image preprocessing fails."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, status_code=422, details=details)


class AIExtractionError(AIBillException):
    """Raised when AI extraction fails."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, status_code=502, details=details)


class ValidationError(AIBillException):
    """Raised when bill validation fails."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, status_code=422, details=details)


class NotFoundError(AIBillException):
    """Raised when requested resource is not found."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, status_code=404, details=details)
