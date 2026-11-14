"""
Rate limiting middleware for API protection against DDoS and abuse.

Keys on tenant_id when the route is authenticated, otherwise on client IP, so
multi-user tenants (owner + technicians) share one limit pool.

Design Specification: dev-docs/analysis/phase-4-5-implementation-roadmap.md Task #22
Architecture: Gap #42 - Rate Limiting for DDoS Protection
Implementation Plan: dev-docs/analysis/phase-1-5-tasks/task-22-rate-limiting-impl-plan.md

Key Features:
- Tenant-based limiting where a route opts in (multi-user tenants share limits)
- Tier table defined (free: 100/hour, standard: 1000/hour, premium: 5000/hour) but not wired; routes use fixed per-route limits
- Redis storage backend (reuses existing ElastiCache)
- RFC 7807-compliant 429 error responses
- Limits apply only to routes decorated with @limiter.limit (no SlowAPIMiddleware)
- <5ms performance overhead

Usage:
    # In main.py
    from core.rate_limit import limiter, rate_limit_error_handler
    from slowapi.errors import RateLimitExceeded

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)

    # In routes
    from core.rate_limit import limiter

    @router.post("/quotes")
    @limiter.limit("1000/hour")
    async def create_quote(...):
        ...

Performance:
    - Redis INCR operation: ~0.5ms
    - Redis EXPIRE operation: ~0.5ms
    - Total overhead: ~1ms per request (well under 5ms target)

Cost:
    - Reuses existing ElastiCache Redis instance (database 0)
    - Memory: ~72 bytes per tenant per hour (negligible)
    - Additional infrastructure cost: $0/month
"""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from core.config import settings

logger = logging.getLogger(__name__)

# Tier-based rate limits
# MVP: All tenants use "standard" tier (1000/hour)
# Post-MVP: Query tenant.subscription_tier from database
RATE_LIMITS = {
    "free": "100/hour",
    "standard": "1000/hour",  # MVP default for all tenants
    "premium": "5000/hour",
    "enterprise": None,  # unlimited (no rate limiting)
}

# Default limit for MVP (all tenants)
DEFAULT_RATE_LIMIT = "1000/hour"


def get_tenant_identifier(request: Request) -> str:
    """
    Extract tenant_id from authenticated user for rate limiting.

    Multi-user tenants (owner + technicians) share the same limit pool.
    This ensures that a tenant's aggregate API usage is tracked, not
    individual user usage.

    For unauthenticated requests (e.g., /auth/login), falls back to
    IP-based rate limiting to prevent credential stuffing attacks.

    Args:
        request: FastAPI request object

    Returns:
        String identifier for rate limiting:
        - "tenant:{tenant_id}" for authenticated requests
        - "ip:{ip_address}" for unauthenticated requests

    Performance:
        - No database queries (tenant_id from JWT in request.state)
        - <0.1ms execution time

    Security:
        - Tenant isolation: Different tenants have independent counters
        - No PII exposure: tenant_id is a UUID, not email/name
    """
    # Use tenant_id from request state (set by auth middleware)
    tenant_id = getattr(request.state, "tenant_id", None)

    if tenant_id:
        return f"tenant:{tenant_id}"

    # Fall back to IP for unauthenticated requests (auth endpoints)
    # This prevents credential stuffing attacks on /auth/login
    return f"ip:{get_remote_address(request)}"


def get_rate_limit_for_tenant(request: Request) -> str:
    """
    Get rate limit string for the current tenant.

    MVP Implementation:
        Returns DEFAULT_RATE_LIMIT ("1000/hour") for all tenants.

    Post-MVP Enhancement:
        Query tenant.subscription_tier from database and return
        corresponding limit from RATE_LIMITS dict.

    Args:
        request: FastAPI request object

    Returns:
        Rate limit string (e.g., "1000/hour")

    Example:
        # MVP: Always returns "1000/hour"
        limit = get_rate_limit_for_tenant(request)
        # limit = "1000/hour"

        # Post-MVP: Dynamic based on tenant tier
        # tenant = db.query(Tenant).filter_by(id=tenant_id).first()
        # return RATE_LIMITS.get(tenant.subscription_tier, DEFAULT_RATE_LIMIT)
    """
    # MVP: Single tier for all tenants
    # Post-MVP: Query tenant.subscription_tier and return tier-specific limit
    return DEFAULT_RATE_LIMIT


# Redis connection URL (reuse existing ElastiCache)
# Use database 0 for rate limiting (separate from Celery databases 1 & 2)
REDIS_URL = settings.CELERY_BROKER_URL.replace("/1", "/0")

# Create Limiter instance
# This is the main rate limiting object used across all routes
limiter = Limiter(
    key_func=get_tenant_identifier,
    storage_uri=REDIS_URL,
    default_limits=[DEFAULT_RATE_LIMIT],  # Not enforced globally: SlowAPIMiddleware is not installed (Known Limitations #28)
    enabled=True,  # Can be disabled in tests
)


def rate_limit_error_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Return RFC 7807-compliant error response for rate limit exceeded.

    Implements RFC 7807 "Problem Details for HTTP APIs" standard for
    consistent error reporting across the API.

    Args:
        request: FastAPI request object
        exc: RateLimitExceeded exception from Slowapi

    Returns:
        JSONResponse with:
        - 429 status code
        - RFC 7807-compliant error body
        - Retry-After header (seconds until limit resets)
        - X-RateLimit-* headers (limit, remaining, reset)

    Example Response:
        HTTP/1.1 429 Too Many Requests
        Retry-After: 1800
        X-RateLimit-Limit: 1000
        X-RateLimit-Remaining: 0
        X-RateLimit-Reset: 1679430000

        {
            "type": "rate_limit_exceeded",
            "title": "Rate Limit Exceeded",
            "status": 429,
            "detail": "Tenant has exceeded rate limit of 1000 requests per hour",
            "retry_after": 1800,
            "instance": "/api/v1/quotes"
        }

    References:
        - RFC 7807: https://www.rfc-editor.org/rfc/rfc7807.html
        - RFC 6585 Section 4: 429 Too Many Requests
    """
    # Extract retry_after from exception (seconds until reset)
    retry_after = int(exc.retry_after) if exc.retry_after else 3600  # Default: 1 hour

    # Build RFC 7807-compliant error response
    error_body = {
        "type": "rate_limit_exceeded",
        "title": "Rate Limit Exceeded",
        "status": 429,
        "detail": f"Rate limit exceeded: {exc.detail}",
        "retry_after": retry_after,
        "instance": str(request.url.path),
    }

    # Build response headers
    headers = {
        "Retry-After": str(retry_after),
    }

    # Add rate limit headers if available
    # These are set by Slowapi but may not be present in all error conditions
    if hasattr(exc, "limit"):
        headers["X-RateLimit-Limit"] = str(exc.limit)
    if hasattr(exc, "remaining"):
        headers["X-RateLimit-Remaining"] = "0"  # Always 0 when limit exceeded
    if hasattr(exc, "reset"):
        headers["X-RateLimit-Reset"] = str(exc.reset)

    logger.warning(
        f"Rate limit exceeded for {get_tenant_identifier(request)}: "
        f"{exc.detail} (retry_after={retry_after}s)"
    )

    return JSONResponse(
        status_code=429,
        content=error_body,
        headers=headers,
    )


def get_redis_client():
    """
    Get Redis client for manual rate limit operations.

    This is useful for:
    - Clearing rate limits in tests
    - Manual rate limit inspection/debugging
    - Custom rate limit logic

    Returns:
        Redis client connected to rate limiting database (db 0)

    Example:
        # Clear all rate limits
        redis = get_redis_client()
        redis.flushdb()

        # Check current limit for tenant
        redis = get_redis_client()
        keys = redis.keys("tenant:00000000-0000-0000-0000-000000000001:*")
        for key in keys:
            count = redis.get(key)
            print(f"{key}: {count}")
    """
    import redis

    return redis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)


def reset_rate_limits(identifier: str | None = None) -> int:
    """
    Reset rate limits for a specific identifier or all identifiers.

    Useful for:
    - Testing (clear limits between tests)
    - Admin operations (manually reset tenant limits)
    - Emergency mitigation (clear all limits during incident)

    Args:
        identifier: Optional identifier to reset (e.g., "tenant:uuid")
                   If None, resets ALL rate limits (use with caution!)

    Returns:
        Number of keys deleted

    Example:
        # Reset specific tenant
        reset_rate_limits("tenant:00000000-0000-0000-0000-000000000001")

        # Reset all tenants (testing only!)
        reset_rate_limits()  # Deletes all rate limit keys

    Warning:
        Calling without identifier in production will reset ALL rate limits!
        Only use this in testing or emergency situations.
    """
    redis = get_redis_client()

    if identifier:
        # Reset specific identifier
        pattern = f"{identifier}:*"
        keys = redis.keys(pattern)
        if keys:
            return redis.delete(*keys)
        return 0
    else:
        # Reset ALL rate limits (dangerous in production!)
        logger.warning(
            "Resetting ALL rate limits - this should only happen in testing!"
        )
        redis.flushdb()
        return -1  # Unknown count, full flush


# Export public API
__all__ = [
    "DEFAULT_RATE_LIMIT",
    "RATE_LIMITS",
    "get_rate_limit_for_tenant",
    "get_redis_client",
    "get_tenant_identifier",
    "limiter",
    "rate_limit_error_handler",
    "reset_rate_limits",
]
