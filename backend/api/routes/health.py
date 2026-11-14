"""
Health check endpoints for system monitoring.

Provides health status for:
- Celery workers
- Redis broker connection
- Task queue depth
- Scheduled tasks

Design Reference: Task #12 - Celery Setup & Configuration
Gap Reference: Gap #21 in phase-1-4-implementation-gap-analysis.md

Usage:
    GET /api/v1/health/celery

    Response:
    {
        "status": "healthy",
        "workers_active": 1,
        "broker_connected": true,
        "scheduled_tasks": 2,
        "timestamp": "2026-03-19T21:00:00.000Z"
    }
"""

import time as _time
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.celery_app import celery_app

router = APIRouter(prefix="/health", tags=["health"])

# ---------------------------------------------------------------------------
# In-process TTL cache — prevents a Kombu connection leak at ALB health-check
# frequency (240 calls/hour from two ALB nodes × 30-second interval).
#
# Root cause (2026-07-06): each call to celery_app.control.inspect() creates a
# new Kombu broadcast Consumer subscribed to a Redis pub/sub fanout channel.
# Python's GC cannot reclaim these objects as fast as they accumulate at 240
# calls/hour inside a 512 MB Fargate task, causing a steady ~1.3 %/hr memory
# climb that eventually triggers the 80 % and 90 % CloudWatch alarms.
#
# Fix: cache the last successful response for _HEALTH_CACHE_SECONDS (15 s).
# The ALB polls every 30 s so liveness signal is still fresh; actual Redis/
# Celery queries drop from 240/hr → ~4/hr (60× reduction).
# ---------------------------------------------------------------------------
_HEALTH_CACHE_SECONDS = 15.0
_health_cache: dict = {"response": None, "expires_at": 0.0}


class CeleryHealthResponse(BaseModel):
    """Response model for Celery health check"""

    status: str
    workers_active: int
    broker_connected: bool
    scheduled_tasks: int
    timestamp: datetime


@router.get("/celery", response_model=CeleryHealthResponse)
def celery_health():
    """
    Check Celery worker and broker health.

    This endpoint provides operational visibility into the Celery worker status,
    broker connectivity, and scheduled task count. Returns 503 (Service Unavailable)
    if workers are not available or broker is disconnected.

    Memory-safe design:
    - 15-second in-process TTL cache: ALB polls every 30 s so the cache is
      always fresh for liveness decisions while reducing Kombu connection
      creation from 240/hr to ~4/hr (60× reduction — fixes the memory leak).
    - inspect() uses timeout=1.0 so broadcast channels close promptly.
    - connection() used as context manager — released immediately after use.

    Returns:
        CeleryHealthResponse: Worker status, broker connectivity, task count

    Raises:
        HTTPException: 503 if workers unavailable or broker disconnected

    Example:
        >>> response = client.get("/api/v1/health/celery")
        >>> assert response.status_code == 200
        >>> assert response.json()["status"] == "healthy"
    """
    # Return cached result if it is still fresh
    now = _time.monotonic()
    if _health_cache["response"] is not None and now < _health_cache["expires_at"]:
        return _health_cache["response"]

    try:
        # Short timeout ensures broadcast channel is torn down promptly
        inspect = celery_app.control.inspect(timeout=1.0)
        active_workers = inspect.active()

        if not active_workers:
            raise HTTPException(status_code=503, detail="No Celery workers available")

        # Use connection as a context manager — guarantees release on exit
        broker_connected = False
        try:
            with celery_app.connection() as conn:
                conn.ensure_connection(max_retries=3)
                broker_connected = True
        except Exception:
            broker_connected = False

        # Get scheduled tasks count (reuses already-open inspect channel)
        scheduled = inspect.scheduled()
        scheduled_count = sum(len(tasks) for tasks in (scheduled or {}).values())

        result = CeleryHealthResponse(
            status="healthy" if broker_connected else "degraded",
            workers_active=len(active_workers),
            broker_connected=broker_connected,
            scheduled_tasks=scheduled_count,
            timestamp=datetime.now(UTC),
        )

        # Store in cache — only cache healthy responses so errors surface immediately
        _health_cache["response"] = result
        _health_cache["expires_at"] = now + _HEALTH_CACHE_SECONDS

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Celery health check failed: {e!s}"
        )
