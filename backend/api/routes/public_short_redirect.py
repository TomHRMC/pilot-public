"""
B15/A80 — Short Link Redirect

GET /api/v1/short/{short_code}
  → 302 Redirect to full signed URL
  → 404 if short code not found
  → atomically increments click_count and sets last_clicked_at
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from core.db import get_db
from services.short_link_resolver import resolve_short_code

logger = logging.getLogger(__name__)
router = APIRouter()

# Base URL for redirect construction — defaults to localhost for dev
_BASE_URL = "http://localhost:8000"


def _build_redirect_url(link_type: str, signed_token: str) -> str:
    """Build the full public URL for the redirect target."""
    from core.config import settings as cfg

    base = getattr(cfg, "PUBLIC_BASE_URL", _BASE_URL).rstrip("/")
    if link_type == "quote":
        return f"{base}/api/v1/public/quotes/{signed_token}"
    elif link_type == "invoice":
        return f"{base}/api/v1/public/invoices/{signed_token}"
    else:
        return f"{base}/api/v1/public/{link_type}s/{signed_token}"


@router.get("/{short_code}")
def redirect_short_code(
    short_code: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Resolve a short code to the full signed URL and redirect.
    Increments click_count atomically.
    Returns 302 on success, 404 if short code not found.
    """
    link_type, signed_token = resolve_short_code(db, short_code)
    redirect_url = _build_redirect_url(link_type, signed_token)
    logger.info(f"Short code redirect: {short_code} → {link_type}")
    return RedirectResponse(url=redirect_url, status_code=302)
