"""C-B16 Part A — Public tenant site endpoint.

GET /api/v1/public/tenant-sites/{slug} — serve published snapshot (no JWT).

Security:
    - No JWT, no get_current_user (public read-only GET precedent: public_charter).
    - SlowAPI 60/minute per IP.
    - 404 site_not_found for unknown slug AND for draft/unpublished (no existence leak).
    - Redis cache 300s TTL, key ``tenant_site:pub:{slug}``, DB 0.
    - Cache is fail-open: on any Redis error, serve from Postgres and continue.

Design: dev-docs/architecture-design/batch-designs/batch-c-b16-design.md §D-7 + §E
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from api.schemas.tenant_site import PublicTenantSitePage, PublicTenantSiteResponse
from core.config import settings
from core.db import get_db
from core.rate_limit import limiter
from services import tenant_site_service as svc

logger = logging.getLogger(__name__)

router = APIRouter()

_CACHE_TTL = 300  # 5 minutes
_CACHE_KEY_PREFIX = "tenant_site:pub:"

# Module-level Redis singleton — fail-open pattern (map_service.py precedent)
_redis_client_instance = None


def _get_redis_client():
    """Return a module-level singleton synchronous Redis client (DB 0).

    Fail-open: returns None on any error — callers must handle None gracefully.
    """
    global _redis_client_instance
    if _redis_client_instance is not None:
        return _redis_client_instance
    try:
        import redis

        _redis_client_instance = redis.from_url(
            settings.REDIS_URL, socket_connect_timeout=1, decode_responses=True
        )
        return _redis_client_instance
    except Exception:
        logger.warning("Could not create Redis client for tenant_site public cache")
        return None


def _cache_key(slug: str) -> str:
    return f"{_CACHE_KEY_PREFIX}{slug}"


def delete_public_cache(slug: str) -> None:
    """Best-effort cache invalidation — called on publish/unpublish."""
    client = _get_redis_client()
    if client is None:
        return
    try:
        client.delete(_cache_key(slug))
    except Exception:
        pass  # Fail-open


def _from_snapshot(snapshot: dict) -> PublicTenantSiteResponse:
    """Build a PublicTenantSiteResponse from a published snapshot dict."""
    pages_raw = snapshot.get("pages", {})
    pages: dict[str, PublicTenantSitePage] = {}
    for page_name, page_data in pages_raw.items():
        pages[page_name] = PublicTenantSitePage(
            heading=page_data.get("heading"),
            title=page_data.get("title"),
            body_paragraphs=page_data.get("body_paragraphs", []),
            contact_lines=page_data.get("contact_lines"),
        )

    # Address fields only present in snapshot when show_full_address
    return PublicTenantSiteResponse(
        slug=snapshot.get("slug", ""),
        display_name=snapshot.get("display_name", ""),
        tagline=snapshot.get("tagline"),
        public_email=snapshot.get("public_email"),
        public_phone=snapshot.get("public_phone"),
        public_city=snapshot.get("public_city"),
        public_state=snapshot.get("public_state"),
        public_address_line1=snapshot.get("public_address_line1"),
        public_postal_code=snapshot.get("public_postal_code"),
        template_version=snapshot.get("template_version", "v1"),
        published_at=None,  # Set from the site row, not the snapshot
        pages=pages,
    )


@router.get(
    "/{slug}",
    response_model=PublicTenantSiteResponse,
    summary="Get published tenant site (public, no auth)",
    tags=["public"],
)
@limiter.limit("60/minute")
def get_public_tenant_site(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
):
    """Public endpoint — serves the published snapshot only.

    404 site_not_found for unknown slug AND for draft/unpublished (no existence leak).
    Redis cache 300s TTL, fail-open.
    """
    slug_lower = slug.strip().lower()
    cache_key = _cache_key(slug_lower)

    # Try Redis cache first (fail-open)
    client = _get_redis_client()
    if client is not None:
        try:
            cached = client.get(cache_key)
            if cached:
                return PublicTenantSiteResponse.model_validate_json(cached)
        except Exception:
            pass  # Fail-open — fall through to Postgres

    # Serve from Postgres
    snapshot = svc.get_published_snapshot(db, slug_lower)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "type": "https://errors.pilotfortrades.com/site_not_found",
                "title": "Site not found",
                "status": 404,
                "detail": "No published site exists at this URL.",
            },
        )

    response = _from_snapshot(snapshot)

    # Cache the response (fail-open — don't block on Redis errors)
    if client is not None:
        try:
            client.setex(cache_key, _CACHE_TTL, response.model_dump_json())
        except Exception:
            pass  # Fail-open

    return response
