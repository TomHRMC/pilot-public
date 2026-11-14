"""
utils/staleness_check.py

Shared pre-commit staleness check utility (§20 / §16.4 / §7.9).

Established in B7b (canonical shared utility per design doc D.3).
Consumed by: A45 (tech conflict resolve), A46 (owner escalation resolve),
and future batches (A48, A50, A62, A80) per §1.5 shared module table.

Pattern:
    Call assert_not_stale() BEFORE any write operation on a resource
    the user has been viewing. If the client's expected version doesn't
    match the DB, raise HTTP 409 with the refreshed payload.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, status


def assert_not_stale(
    expected_updated_at: datetime | None,
    actual_updated_at: datetime,
    refreshed_payload: dict[str, Any],
    entity_label: str = "record",
) -> None:
    """
    Raise 409 Conflict if the client's expected version doesn't match the DB.

    Call this BEFORE any write operation on a resource the user has been viewing.

    Args:
        expected_updated_at: Timestamp the client last saw (from request body).
                             If None, skip the check (caller opted out).
        actual_updated_at:   Current `updated_at` from the freshly-fetched DB row.
        refreshed_payload:   The full refreshed entity dict to include in the 409 response.
        entity_label:        Human-readable label for the error message.

    Raises:
        HTTPException(409): With the refreshed payload so the client can re-render.
    """
    if expected_updated_at is None:
        return  # caller opted out of staleness check for this request

    # Strip microseconds to match serialization precision
    expected = expected_updated_at.replace(microsecond=0)
    actual = actual_updated_at.replace(microsecond=0)

    if expected != actual:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://pilotfortrades.com/errors/stale-state",
                "title": "Record Updated",
                "status": 409,
                "detail": (
                    f"This {entity_label} was updated since you last viewed it. "
                    "Please refresh and re-submit."
                ),
                "refreshed": refreshed_payload,
            },
        )


def assert_not_stale_dual(
    expected_pilot_modified_at: datetime | None,
    actual_pilot_modified_at: datetime,
    expected_qb_modified_at: datetime | None,
    actual_qb_modified_at: datetime,
    refreshed_payload: dict[str, Any],
) -> None:
    """
    Dual-timestamp variant for QB conflicts where both sides can drift.

    B8/A50: Raises 409 if either timestamp mismatches.
    Established per design doc §D (staleness_check.py extension).

    Args:
        expected_pilot_modified_at: Pilot-side timestamp the client last saw.
        actual_pilot_modified_at:   Current pilot_modified_at from DB.
        expected_qb_modified_at:    QB-side timestamp the client last saw.
        actual_qb_modified_at:      Current qb_modified_at from DB.
        refreshed_payload:          Full refreshed entity dict for 409 response.

    Raises:
        HTTPException(409): If either side has drifted.
    """
    pilot_stale = (
        expected_pilot_modified_at is not None
        and expected_pilot_modified_at.replace(microsecond=0)
        != actual_pilot_modified_at.replace(microsecond=0)
    )
    qb_stale = expected_qb_modified_at is not None and expected_qb_modified_at.replace(
        microsecond=0
    ) != actual_qb_modified_at.replace(microsecond=0)
    if pilot_stale or qb_stale:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "type": "https://pilotfortrades.com/errors/stale-state",
                "staleness_type": "server_changed",
                "title": "Conflict Updated",
                "status": 409,
                "detail": (
                    "This QB conflict was updated on one or both sides since you last viewed it. "
                    "Please refresh and re-submit."
                ),
                "refreshed": refreshed_payload,
            },
        )
