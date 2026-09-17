"""Custom application exceptions and error envelopes."""

from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class AppError(HTTPException):
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        code: str = "INTERNAL_SERVER_ERROR",
        message: str = "An unexpected error occurred.",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail={"code": code, "message": message, "details": details or {}})


class NotFoundError(AppError):
    def __init__(self, resource: str = "Resource", resource_id: str = ""):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=f"{resource} '{resource_id}' was not found.",
        )


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Invalid or expired credentials."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message=message,
        )


class LLMUnavailableError(AppError):
    def __init__(self, message: str = "The local or remote LLM service is currently unreachable."):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="LLM_UNAVAILABLE",
            message=message,
        )

