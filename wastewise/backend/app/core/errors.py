"""Consistent error shape + application exceptions.

Every error response uses the contract shape:
{"error": {"code": "...", "message": "...", "request_id": "..."}}
"""
from typing import Any


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: Any = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


def not_found(resource: str, resource_id: str) -> AppError:
    return AppError(
        code=f"{resource.upper().replace(' ', '_')}_NOT_FOUND",
        message=f"The requested {resource.lower()} does not exist: {resource_id}",
        status_code=404,
    )


def bad_request(code: str, message: str) -> AppError:
    return AppError(code=code, message=message, status_code=400)


def conflict(code: str, message: str) -> AppError:
    return AppError(code=code, message=message, status_code=409)
