"""
Idempotency middleware for preventing duplicate transactions.

Implements RFC-compliant idempotency using the Idempotency-Key header
and caches responses in the idempotency_key table for 24 hours.

Design Specification: pilot-db-process-v2.6h.md Section 7
Architecture: Gap #28B - Idempotency Key Handling

Key Features:
- Optional Idempotency-Key header (recommended for all mutating operations)
- 24-hour response caching
- Conflict detection (same key + different body = 409)
- Duplicate inserts rejected by the primary key (no explicit row lock; a concurrent duplicate can surface as an error)
- Status state machine: in_progress → succeeded/failed

Usage:
    # Client sends POST request with idempotency key
    POST /v1/customers
    Headers:
        Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000

    # Duplicate request returns cached response
    Response:
        X-Idempotency-Replay: true
"""

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from sqlmodel import Session, select

from app.models.system import IdempotencyKey
from core.db import get_db

# Constants
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
IDEMPOTENCY_TTL_HOURS = 24
LOCK_TIMEOUT_MINUTES = 5


def hash_request_body(body: bytes) -> str:
    """
    Generate SHA-256 hash of request body for conflict detection.

    Args:
        body: Raw request body bytes

    Returns:
        Hex digest of SHA-256 hash
    """
    return hashlib.sha256(body).hexdigest()


def hash_response_body(body: dict) -> str:
    """
    Generate SHA-256 hash of response body.

    Args:
        body: Response body as dictionary

    Returns:
        Hex digest of SHA-256 hash
    """
    body_str = json.dumps(body, sort_keys=True)
    return hashlib.sha256(body_str.encode()).hexdigest()


async def idempotency_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to handle idempotency for POST/PATCH/DELETE requests.

    Flow:
    1. Check if request has Idempotency-Key header
    2. If not, pass through normally (optional for MVP)
    3. If yes, check if key exists in database
    4. If exists and succeeded, return cached response
    5. If exists and in_progress, wait or return 409 Conflict
    6. If new, lock key, execute, cache response

    Args:
        request: FastAPI request object
        call_next: Next middleware/handler in chain

    Returns:
        Response (cached or fresh)

    Raises:
        HTTPException:
            400 - Invalid idempotency key format
            409 - Conflict (same key with different body OR request in progress)
    """
    # Only apply to mutating operations
    if request.method not in ["POST", "PATCH", "PUT", "DELETE"]:
        return await call_next(request)

    # Get idempotency key from header
    idempotency_key = request.headers.get(IDEMPOTENCY_KEY_HEADER)

    # If no key provided, pass through (optional for MVP)
    if not idempotency_key:
        return await call_next(request)

    # Validate key format (UUID recommended)
    try:
        uuid.UUID(idempotency_key)
    except ValueError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": f"Invalid {IDEMPOTENCY_KEY_HEADER}: must be a valid UUID"
            },
        )

    # Read request body for hashing (conflict detection)
    # Note: We need to cache the body so FastAPI can read it again
    body = await request.body()
    request_hash = hash_request_body(body) if body else None

    # Important: Create a new receive callable that can replay the body
    async def receive():
        return {"type": "http.request", "body": body}

    # Replace request's receive with our cached version
    request._receive = receive

    # Get database session
    db: Session = next(get_db())

    # tenant_id / user_id from request state: route-level auth runs after this middleware,
    # so these are normally None here (keys are not caller-scoped; Known Limitations #28)
    tenant_id = getattr(request.state, "tenant_id", None)
    user_id = getattr(request.state, "user_id", None)

    try:
        # Check if idempotency key already exists
        existing_key = db.exec(
            select(IdempotencyKey).where(IdempotencyKey.key == idempotency_key)
        ).first()

        if existing_key:
            # Key exists - check status
            if existing_key.status == "succeeded":
                # Check if request body matches (conflict detection)
                if request_hash and existing_key.request_hash != request_hash:
                    return JSONResponse(
                        status_code=status.HTTP_409_CONFLICT,
                        content={
                            "detail": (
                                f"Idempotency key '{idempotency_key}' already used "
                                "with different request body"
                            )
                        },
                    )

                # Return cached response
                return JSONResponse(
                    content=existing_key.response_body,
                    status_code=200,
                    headers={"X-Idempotency-Replay": "true"},
                )

            elif existing_key.status == "in_progress":
                # Request already in progress - check lock timeout
                if (
                    existing_key.locked_until
                    and existing_key.locked_until > datetime.now(UTC)
                ):
                    return JSONResponse(
                        status_code=status.HTTP_409_CONFLICT,
                        content={
                            "detail": (
                                f"Request with idempotency key '{idempotency_key}' "
                                "already in progress. Please retry in a few moments."
                            )
                        },
                    )
                # Lock expired, allow retry
                existing_key.status = "in_progress"
                existing_key.locked_until = datetime.now(UTC) + timedelta(
                    minutes=LOCK_TIMEOUT_MINUTES
                )
                db.add(existing_key)
                db.commit()

            elif existing_key.status == "failed":
                # Previous request failed, allow retry
                existing_key.status = "in_progress"
                existing_key.locked_until = datetime.now(UTC) + timedelta(
                    minutes=LOCK_TIMEOUT_MINUTES
                )
                db.add(existing_key)
                db.commit()

        else:
            # New idempotency key - create record
            new_key = IdempotencyKey(
                key=idempotency_key,
                tenant_id=tenant_id,
                user_id=user_id,
                first_seen_at=datetime.now(UTC),
                status="in_progress",
                request_hash=request_hash,
                locked_until=datetime.now(UTC)
                + timedelta(minutes=LOCK_TIMEOUT_MINUTES),
                expires_at=datetime.now(UTC) + timedelta(hours=IDEMPOTENCY_TTL_HOURS),
            )
            db.add(new_key)
            db.commit()
            db.refresh(new_key)
            existing_key = new_key

        # Execute the actual request
        try:
            response = await call_next(request)

            # Cache successful response
            if 200 <= response.status_code < 300:
                # Read response body
                response_body = b""
                async for chunk in response.body_iterator:
                    response_body += chunk

                # Parse JSON
                try:
                    response_data = json.loads(response_body.decode())
                except json.JSONDecodeError:
                    # Non-JSON response (e.g., file download)
                    response_data = {"raw": response_body.decode(errors="ignore")}

                # Update idempotency key with success
                existing_key.status = "succeeded"
                existing_key.response_body = response_data
                existing_key.response_hash = hash_response_body(response_data)
                existing_key.locked_until = None
                db.add(existing_key)
                db.commit()

                # Return response (reconstruct with body)
                return JSONResponse(
                    content=response_data,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                )
            else:
                # Non-successful response (4xx, 5xx)
                existing_key.status = "failed"
                existing_key.locked_until = None
                db.add(existing_key)
                db.commit()
                return response

        except Exception:
            # Request execution failed (exception thrown)
            existing_key.status = "failed"
            existing_key.locked_until = None
            db.add(existing_key)
            db.commit()
            raise

    finally:
        db.close()
