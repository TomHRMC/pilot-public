"""
Tech Color Assignment Service — B3/A18.

Auto-assigns dispatch board avatar colors to new users from a cycling palette.
Consumed by: B3 A18 (user creation hook + manual override endpoint).
"""

import re
from uuid import UUID

from sqlmodel import Session, select

from app.models.auth import TenantUser
from app.models.core import User

# System default 12-hue WCAG AA-compliant palette (hex strings)
DEFAULT_PALETTE: list[str] = [
    "#3B43D6",
    "#D64343",
    "#43D68B",
    "#D6A143",
    "#8B43D6",
    "#43BDD6",
    "#D6438B",
    "#6BD643",
    "#D6435F",
    "#435FD6",
    "#D6C243",
    "#43D6C2",
]

# Regex pattern for valid hex color validation (used in route layer)
HEX_COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


def is_valid_hex_color(value: str) -> bool:
    """Return True when value matches a 6-digit hex color string like #3B43D6.

    Args:
        value: The string to validate.
    Returns:
        bool: True if valid hex color, False otherwise.
    """
    return bool(re.match(HEX_COLOR_PATTERN, value))


def _get_palette(db: Session, tenant_id: UUID) -> list[str]:
    """Return the effective palette for a tenant.

    Uses platform_setting tech_color_palette if set and non-empty;
    falls back to DEFAULT_PALETTE.

    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID.
    Returns:
        list[str]: Ordered list of hex color strings.
    """
    from services.setting_resolver import (
        get_effective_setting,  # lazy to avoid circular
    )

    palette_val, _ = get_effective_setting(db, tenant_id, "tech_color_palette")

    if (
        palette_val is not None
        and isinstance(palette_val, list)
        and len(palette_val) > 0
    ):
        return list(palette_val)

    return DEFAULT_PALETTE


def assign_next_color(
    db: Session,
    tenant_id: UUID,
    palette: list[str] | None = None,
) -> str:
    """Select the next available color for a new user within a tenant.

    Cycles through the palette ensuring no two active users in the same
    tenant share a color. Wraps around when all colors are in use.

    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID — color uniqueness is per-tenant, not global.
        palette:   Override palette (from tenant_settings.tech_color_palette).
                   Falls back to DEFAULT_PALETTE if None or empty.
    Returns:
        str: Hex color string, e.g. '#3B43D6'.
    """
    effective_palette = (
        palette if (palette and len(palette) > 0) else _get_palette(db, tenant_id)
    )

    # Get colors already used by active users in this tenant
    used_rows = db.exec(
        select(User.display_color)
        .join(TenantUser, TenantUser.user_id == User.id)
        .where(TenantUser.tenant_id == tenant_id)
        .where(TenantUser.is_active == True)
        .where(User.is_active == True)
        .where(User.display_color.is_not(None))  # type: ignore[union-attr]
    ).all()
    used_colors: set[str] = {c for c in used_rows if c is not None}

    # Find first color not currently in use
    for color in effective_palette:
        if color not in used_colors:
            return color

    # All palette slots occupied — wrap around using modulo cycling
    count = len(used_colors)
    return effective_palette[count % len(effective_palette)]
