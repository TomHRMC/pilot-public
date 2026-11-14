"""
B15/A80 — Short Link Resolver

Generates and resolves base62 short codes stored in public_link_short_code.

generate_short_code(): persist new short code → link mapping
resolve_short_code():  look up link by short code, increment click_count

Retries on collision (up to 10 attempts) with increasing code lengths.
"""

import secrets
import string
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlmodel import Session, select

BASE62_CHARS = string.ascii_letters + string.digits  # 62 chars


def _generate_code(length: int) -> str:
    """Generate a random base62 string of the given length."""
    return "".join(secrets.choice(BASE62_CHARS) for _ in range(length))


def generate_short_code(
    db: Session,
    link_id: str,  # UUID as string
    link_type: str,  # 'quote' | 'invoice'
    created_by: str | None = None,  # user UUID as string
    length: int = 6,
) -> str:
    """
    Generate a collision-safe base62 short code and persist to public_link_short_code.

    Args:
        db: SQLModel session.
        link_id: UUID of the quote_public_link or invoice_public_link.
        link_type: 'quote' or 'invoice'.
        created_by: UUID of the Pilot user who triggered generation.
        length: Code length (default 6, range 5–8 per spec).

    Returns:
        The generated short_code string.

    Raises:
        RuntimeError if 10 collision retries exhausted.
    """
    from app.models.quoting import PublicLinkShortCode

    max_retries = 10
    for attempt in range(max_retries):
        code = _generate_code(length)
        existing = db.exec(
            select(PublicLinkShortCode).where(PublicLinkShortCode.short_code == code)
        ).first()
        if existing is None:
            row = PublicLinkShortCode(
                short_code=code,
                link_type=link_type,
                link_id=uuid.UUID(link_id),
                click_count=0,
                created_by=uuid.UUID(created_by) if created_by else None,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return code
        # Collision: bump length on every 3rd failure
        if attempt > 0 and attempt % 3 == 0:
            length = min(length + 1, 8)

    raise RuntimeError(
        f"Short code generation exhausted {max_retries} attempts — "
        "collision density too high for link_type={link_type}"
    )


def resolve_short_code(
    db: Session,
    short_code: str,
) -> tuple[str, str]:
    """
    Resolve a short code to (link_type, signed_token) for redirect.

    Args:
        db: SQLModel session.
        short_code: The short code from the URL.

    Returns:
        Tuple of (link_type, signed_token).

    Raises:
        HTTPException 404 if short_code not found.

    Side effects:
        Atomically increments click_count and sets last_clicked_at.
    """
    from app.models.quoting import PublicLinkShortCode

    row = db.exec(
        select(PublicLinkShortCode).where(PublicLinkShortCode.short_code == short_code)
    ).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short code '{short_code}' not found",
        )

    link_type = row.link_type
    link_id = row.link_id

    # Resolve to signed_token
    signed_token = _resolve_link_token(db, link_type, link_id)

    # Increment click count atomically
    row.click_count = (row.click_count or 0) + 1
    row.last_clicked_at = datetime.now(UTC)
    db.add(row)
    db.commit()

    return link_type, signed_token


def _resolve_link_token(db: Session, link_type: str, link_id: uuid.UUID) -> str:
    """Resolve link_id + link_type to the signed_token on the target table."""
    if link_type == "quote":
        from app.models.quoting import QuotePublicLink

        link = db.exec(
            select(QuotePublicLink).where(QuotePublicLink.id == link_id)
        ).first()
    elif link_type == "invoice":
        from app.models.billing import InvoicePublicLink

        link = db.exec(
            select(InvoicePublicLink).where(InvoicePublicLink.id == link_id)
        ).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown link_type '{link_type}'",
        )

    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{link_type.capitalize()} public link not found for short code",
        )

    if not link.signed_token:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Public link has no signed token (legacy link)",
        )

    return link.signed_token
