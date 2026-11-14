"""
Map Provider Abstraction Service — Task 1-C-1 + B3/A20

Wraps the Google Maps Distance Matrix API (or a deterministic dev mock) and
returns the estimated drive time in minutes between two Address records.

B3/A20 addition: Redis cache layer for drive-time results.
  Cache key: drive_time:{origin_lat}:{origin_lng}:{dest_lat}:{dest_lng}:{hour_of_day}
  TTL: 24h (settings.MAP_CACHE_TTL_SECONDS)
  Cache hit ratio is tracked via module-level counters for CloudWatch metric:
    map_provider.cache_hit_ratio

Design decisions
----------------
* **Provider selection** is controlled by ``settings.MAP_PROVIDER``:
  - ``"google"`` — live HTTP call to the Distance Matrix API (requires
    ``GOOGLE_MAPS_API_URL`` and ``GOOGLE_MAPS_API_KEY`` to be set).
  - ``"mock"``   — deterministic formula using the Haversine great-circle
    distance between stored lat/lon coordinates.  Falls back to a flat
    estimate (``MAP_MOCK_FALLBACK_MINUTES``) when either address lacks
    coordinates.  Safe for local dev and CI without any API quota.

* The public surface is intentionally narrow: callers pass two
  ``address_id`` UUIDs and receive a single integer (minutes).  All
  provider-specific logic is encapsulated here so the Conflict Detection
  Service (1-B-4 / 1-C-2) can call ``get_drive_time_minutes()`` without
  knowing anything about the underlying transport.

* Errors from the Google API are surfaced as ``MapServiceError`` so
  callers can decide whether to treat them as hard failures or soft
  warnings (the Conflict Detection Service treats them as soft).
"""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime
from uuid import UUID

import httpx
from sqlmodel import Session, select

from app.models.crm import Address
from core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# B3/A20: Cache hit ratio counters (module-level for CloudWatch reporting)
# ---------------------------------------------------------------------------

_cache_hits: int = 0
_cache_misses: int = 0


def get_cache_hit_ratio() -> float:
    """Return the current cache hit ratio (0.0 – 1.0).

    Returns:
        float: hit_count / total_count, or 0.0 if no requests yet.
    """
    total = _cache_hits + _cache_misses
    if total == 0:
        return 0.0
    return _cache_hits / total


def reset_cache_counters() -> None:
    """Reset hit/miss counters. Called by CloudWatch reporter after flush."""
    global _cache_hits, _cache_misses
    _cache_hits = 0
    _cache_misses = 0


# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------


class MapServiceError(Exception):
    """Raised when the map provider returns an unrecoverable error."""


# ---------------------------------------------------------------------------
# B3/A20: Redis cache helpers
# ---------------------------------------------------------------------------


def _make_cache_key(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
    hour_of_day: int,
) -> str:
    """Build the Redis key for a drive-time lookup.

    Key format: drive_time:{origin_lat}:{origin_lng}:{dest_lat}:{dest_lng}:{hour}
    Coordinates are rounded to 4 decimal places (~11m precision) to maximise
    cache reuse without introducing meaningful spatial error.

    Args:
        origin_lat:   Origin latitude.
        origin_lng:   Origin longitude.
        dest_lat:     Destination latitude.
        dest_lng:     Destination longitude.
        hour_of_day:  UTC hour (0-23) — allows mild time-of-day differentiation.
    Returns:
        str: Redis key.
    """
    return (
        f"drive_time:"
        f"{round(origin_lat, 4)}:"
        f"{round(origin_lng, 4)}:"
        f"{round(dest_lat, 4)}:"
        f"{round(dest_lng, 4)}:"
        f"{hour_of_day}"
    )


# Module-level Redis singleton — avoids creating a new TCP connection per cache call.
# Reset to None in tests via: import services.map_service; services.map_service._redis_client_instance = None
_redis_client_instance = None


def _get_redis_client():
    """Return a module-level singleton synchronous Redis client.

    Creates the client once and reuses it for all cache GETs and SETs.
    Returns None if redis package is unavailable (graceful degradation).
    """
    global _redis_client_instance
    if _redis_client_instance is not None:
        return _redis_client_instance
    try:
        import redis

        _redis_client_instance = redis.from_url(
            settings.REDIS_URL, socket_connect_timeout=1
        )
        return _redis_client_instance
    except Exception:
        return None


def _cache_get(key: str) -> int | None:
    """Return cached drive-time minutes or None on cache miss / Redis error."""
    global _cache_hits, _cache_misses

    if not settings.MAP_CACHE_ENABLED:
        _cache_misses += 1
        return None

    client = _get_redis_client()
    if client is None:
        _cache_misses += 1
        return None

    try:
        raw = client.get(key)
        if raw is not None:
            _cache_hits += 1
            logger.debug("map_service.cache HIT key=%s value=%s", key, raw)
            return int(raw)
    except Exception as exc:
        logger.warning("map_service.cache GET error: %s", exc)

    _cache_misses += 1
    return None


def _cache_set(key: str, minutes: int) -> None:
    """Write drive-time minutes to Redis. Silently no-ops on any error."""
    if not settings.MAP_CACHE_ENABLED:
        return

    client = _get_redis_client()
    if client is None:
        return

    try:
        client.setex(key, settings.MAP_CACHE_TTL_SECONDS, minutes)
        logger.debug(
            "map_service.cache SET key=%s value=%d ttl=%d",
            key,
            minutes,
            settings.MAP_CACHE_TTL_SECONDS,
        )
    except Exception as exc:
        logger.warning("map_service.cache SET error: %s", exc)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in kilometres between two WGS-84 points."""
    R = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def _km_to_drive_minutes(distance_km: float, avg_speed_kmh: float = 40.0) -> int:
    """Convert a road-distance estimate to drive minutes at an average speed."""
    return max(1, round((distance_km / avg_speed_kmh) * 60))


def _mock_drive_time(origin: Address, destination: Address) -> int:
    """Compute a deterministic drive-time estimate without any API call.

    Uses Haversine distance and an assumed 40 km/h average urban speed when
    both addresses have lat/lon stored.  Falls back to the configured flat
    fallback value when coordinates are absent.
    """
    if (
        origin.latitude is not None
        and origin.longitude is not None
        and destination.latitude is not None
        and destination.longitude is not None
    ):
        distance_km = _haversine_km(
            float(origin.latitude),
            float(origin.longitude),
            float(destination.latitude),
            float(destination.longitude),
        )
        minutes = _km_to_drive_minutes(distance_km)
        logger.debug(
            "map_service.mock: haversine %.2f km → %d min (origin=%s, destination=%s)",
            distance_km,
            minutes,
            origin.id,
            destination.id,
        )
        return minutes

    # No coordinates — use the configured flat fallback
    fallback = settings.MAP_MOCK_FALLBACK_MINUTES
    logger.debug(
        "map_service.mock: no coordinates — using fallback %d min "
        "(origin=%s, destination=%s)",
        fallback,
        origin.id,
        destination.id,
    )
    return fallback


def _google_drive_time(origin: Address, destination: Address) -> int:
    """Call the Google Maps Distance Matrix API and return drive time in minutes.

    Args:
        origin:      Origin Address ORM record (must have a full street address).
        destination: Destination Address ORM record.

    Returns:
        Estimated drive time in minutes (integer, ≥ 1).

    Raises:
        MapServiceError: on HTTP error, quota exhaustion, or ZERO_RESULTS.
    """

    def _format_address(addr: Address) -> str:
        """Build a URL-safe address string from ORM fields."""
        parts = [addr.line1, addr.city, addr.state, addr.postal_code, addr.country]
        return ", ".join(p for p in parts if p)

    params = {
        "origins": _format_address(origin),
        "destinations": _format_address(destination),
        "mode": "driving",
        "units": "metric",
        "key": settings.GOOGLE_MAPS_API_KEY,
    }

    try:
        with httpx.Client(timeout=settings.MAP_HTTP_TIMEOUT_SECONDS) as client:
            response = client.get(
                settings.GOOGLE_MAPS_API_URL,
                params=params,
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise MapServiceError(f"Google Maps API HTTP error: {exc}") from exc

    payload = response.json()
    status = payload.get("status")
    if status != "OK":
        raise MapServiceError(f"Google Maps API returned status '{status}'")

    try:
        element = payload["rows"][0]["elements"][0]
    except (KeyError, IndexError) as exc:
        raise MapServiceError(
            f"Unexpected Google Maps API response shape: {exc}"
        ) from exc

    element_status = element.get("status")
    if element_status != "OK":
        raise MapServiceError(
            f"Google Maps element status '{element_status}' "
            f"(origin={origin.id}, destination={destination.id})"
        )

    duration_seconds: int = element["duration"]["value"]
    minutes = max(1, round(duration_seconds / 60))
    logger.debug(
        "map_service.google: %d sec → %d min (origin=%s, destination=%s)",
        duration_seconds,
        minutes,
        origin.id,
        destination.id,
    )
    return minutes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_drive_time_minutes(
    db: Session,
    tenant_id: UUID,
    origin_address_id: UUID,
    destination_address_id: UUID,
    provider: str | None = None,
) -> int:
    """Return the estimated drive time in minutes between two Address records.

    B3/A20: Wraps result with Redis cache (key = coordinates + hour_of_day, TTL 24h).
    Cache is bypassed when MAP_CACHE_ENABLED=False (tests) or Redis is unavailable.

    This is the single public entry-point for map distance queries used by
    the Conflict Detection Service (Task 1-C-2).

    Args:
        db:                     Open SQLModel session.
        tenant_id:              Tenant scope — enforces IDOR isolation; both
                                addresses must belong to this tenant.
        origin_address_id:      UUID of the origin ``Address`` record.
        destination_address_id: UUID of the destination ``Address`` record.
        provider:               Override the configured provider for testing.
                                Accepts ``"google"`` or ``"mock"``.  Defaults
                                to ``settings.MAP_PROVIDER``.

    Returns:
        Estimated drive time as a positive integer (minutes, ≥ 1).

    Raises:
        MapServiceError: If an address UUID is not found, does not belong to
                         the tenant, or the Google API call fails.
    """
    effective_provider = provider or settings.MAP_PROVIDER

    # --- Fetch and validate both addresses (IDOR isolation) ----------------
    origin = db.exec(
        select(Address)
        .where(Address.id == origin_address_id)
        .where(Address.tenant_id == tenant_id)
        .where(Address.is_active == True)
    ).first()

    if origin is None:
        raise MapServiceError(
            f"Origin address {origin_address_id} not found for tenant {tenant_id}"
        )

    destination = db.exec(
        select(Address)
        .where(Address.id == destination_address_id)
        .where(Address.tenant_id == tenant_id)
        .where(Address.is_active == True)
    ).first()

    if destination is None:
        raise MapServiceError(
            f"Destination address {destination_address_id} not found for tenant {tenant_id}"
        )

    # --- Same-address short-circuit ----------------------------------------
    if origin_address_id == destination_address_id:
        logger.debug(
            "map_service: same address — returning 0 min (address=%s)",
            origin_address_id,
        )
        return 0

    # --- B3/A20: Redis cache check (only when both addresses have coordinates) --
    cache_key: str | None = None
    if (
        origin.latitude is not None
        and origin.longitude is not None
        and destination.latitude is not None
        and destination.longitude is not None
    ):
        hour_of_day = datetime.now(UTC).hour
        cache_key = _make_cache_key(
            float(origin.latitude),
            float(origin.longitude),
            float(destination.latitude),
            float(destination.longitude),
            hour_of_day,
        )
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

    # --- Dispatch to provider -----------------------------------------------
    if effective_provider == "google":
        minutes = _google_drive_time(origin, destination)
    else:
        # Default: mock
        minutes = _mock_drive_time(origin, destination)

    # --- B3/A20: Populate cache ---------------------------------------------
    if cache_key is not None:
        _cache_set(cache_key, minutes)

    return minutes
