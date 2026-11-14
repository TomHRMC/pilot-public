"""
Request ID tracing middleware for distributed debugging.

Implements Section 1.1 of pilot-db-process-v2.6h.md:
Every request must have unique trace ID for distributed debugging.

Design Specification: dev-docs/db-design/pilot-db-process-v2.6h.md Section 1.1
Architecture: Gap #1 - X-Request-ID Tracing Middleware

Key Features:
- Accepts X-Request-ID header from clients
- Generates UUID4 if not provided
- Validates UUID format (generates new on invalid)
- Populates request.state.request_id for downstream use
- Returns X-Request-ID in response headers
- Provides logging helpers for request tracing

Usage:
    # In main.py
    app.add_middleware(RequestIDMiddleware)

    # In routes
    from core.middleware import get_request_id, log_with_request_id

    @router.post("/customers")
    async def create_customer(request: Request, data: CustomerCreate):
        log_with_request_id(request, f"Creating customer: {data.email}")
        # ... rest of logic
"""

import logging
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request IDs for distributed tracing.

    Implements Section 1.1 of pilot-db-process-v2.6h.md:
    Every request must have unique trace ID for distributed debugging.

    Features:
    - Accepts X-Request-ID header from clients
    - Generates UUID4 if not provided
    - Validates UUID format (generates new on invalid)
    - Populates request.state.request_id for downstream use
    - Returns X-Request-ID in response headers

    Usage:
        # In main.py
        app.add_middleware(RequestIDMiddleware)

        # In routes
        request_id = request.state.request_id
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and inject/validate request ID.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with X-Request-ID header
        """
        request_id = request.headers.get("X-Request-ID")

        if request_id:
            # Validate client-provided ID
            if not self._is_valid_uuid(request_id):
                original_id = request_id
                request_id = str(uuid.uuid4())
                logger.warning(
                    f"Invalid X-Request-ID '{original_id}' provided. "
                    f"Generated new ID: {request_id}"
                )
        else:
            # Generate new UUID
            request_id = str(uuid.uuid4())

        # Populate request state for downstream use
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add to response headers
        response.headers["X-Request-ID"] = request_id

        return response

    @staticmethod
    def _is_valid_uuid(value: str) -> bool:
        """
        Validate that string is properly formatted UUID.

        Args:
            value: String to validate

        Returns:
            True if valid UUID, False otherwise
        """
        try:
            uuid.UUID(value)
            return True
        except ValueError:
            return False


def get_request_id(request: Request) -> str:
    """
    Extract request ID from request state.

    Args:
        request: FastAPI request object

    Returns:
        Request ID or "UNKNOWN" if not set
    """
    return getattr(request.state, "request_id", "UNKNOWN")


def log_with_request_id(request: Request, message: str, level: str = "info") -> None:
    """
    Log message with request ID prefix for traceability.

    Args:
        request: FastAPI request object
        message: Log message
        level: Log level (info, warning, error, debug)

    Example:
        log_with_request_id(request, "Processing customer creation", "info")
        # Output: [a1b2c3d4-...] Processing customer creation
    """
    request_id = get_request_id(request)
    log_message = f"[{request_id}] {message}"
    getattr(logger, level)(log_message)
