"""
Calendar Conflict Resolution Service — B6 (A32, A33, A34, A35)

Provides diff computation, staleness checking, resolution execution,
effective-setting resolution for auto-expiry, and notification rate-limit
enforcement.

Referenced by:
  - backend/api/routes/calendar_conflicts.py (A32, A33, A35)
  - backend/tasks/expire_stale_calendar_conflicts.py (A34)
  - backend/services/voice_action_router.py (A36)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlmodel import Session, select

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Change-vocabulary constants (§16.2)
# ---------------------------------------------------------------------------

CHANGE_UNCHANGED = "unchanged"
CHANGE_MODIFIED = "modified"
CHANGE_ADDED = "added"
CHANGE_REMOVED = "removed"

# ---------------------------------------------------------------------------
# Legal resolutions per conflict_type (§C.3)
# ---------------------------------------------------------------------------

LEGAL_RESOLUTIONS: dict[str, set] = {
    "modified_modified": {"accept_local", "accept_remote"},
    "deleted_modified": {"restore_from_calendar", "delete_calendar_too"},
    "modified_deleted": {"recreate_calendar_event", "delete_pilot_job"},
}


class CalendarConflictService:
    """All calendar conflict business logic extracted from routes."""

    # -----------------------------------------------------------------------
    # A32: Field-level diff computation (§D.1, §16.2)
    # -----------------------------------------------------------------------

    @staticmethod
    def compute_field_diffs(
        pilot_snapshot: dict[str, Any],
        external_snapshot: dict[str, Any],
        base_snapshot: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """
        Compute server-side field-level diff from three snapshots.

        Note: local_snapshot = pilot_snapshot, remote_snapshot = external_snapshot
        in the live DB column naming.

        Args:
            pilot_snapshot: Current Pilot state at detection (local_snapshot).
            external_snapshot: Current calendar state at detection (remote_snapshot).
            base_snapshot: Last shared state before conflict (may be None).

        Returns:
            List of field-diff dicts conforming to §16.2 vocabulary.
        """
        # Collect all unique keys across all snapshots
        all_keys: set = set()
        all_keys.update(pilot_snapshot.keys())
        all_keys.update(external_snapshot.keys())
        if base_snapshot:
            all_keys.update(base_snapshot.keys())

        diffs: list[dict[str, Any]] = []

        for key in sorted(all_keys):
            pilot_val = pilot_snapshot.get(key)
            external_val = external_snapshot.get(key)
            base_val = base_snapshot.get(key) if base_snapshot else None

            # Skip fields that are identical in both snapshots with no base diff
            if pilot_val == external_val:
                continue

            # Compute per-side change relative to base
            if base_snapshot is not None:
                pilot_change = _compute_change(base_val, pilot_val, key, base_snapshot)
                external_change = _compute_change(
                    base_val, external_val, key, base_snapshot
                )
            else:
                # No base: treat pilot as reference
                pilot_change = CHANGE_UNCHANGED
                external_change = (
                    CHANGE_MODIFIED if external_val is not None else CHANGE_REMOVED
                )

            diffs.append(
                {
                    "field_name": key,
                    "pilot_value": pilot_val,
                    "external_value": external_val,
                    "base_value": base_val,
                    "pilot_change": pilot_change,
                    "external_change": external_change,
                }
            )

        return diffs

    # -----------------------------------------------------------------------
    # A33: Canonical staleness check (§D.2, §16.4)
    # -----------------------------------------------------------------------

    @staticmethod
    def check_staleness(
        conflict: Any,  # CalendarSyncConflict ORM object
        expected_pilot_modified_at: datetime,
        expected_external_modified_at: datetime,
    ) -> bool:
        """
        A33 canonical staleness check pattern.

        Returns True if the conflict has been modified since the client last viewed it.
        Caller returns HTTP 409 with refreshed conflict payload when True.

        Reused verbatim by: A45 (B7b), A48 (B8), A50 (B8), A62 (B11).
        """
        actual_pilot = conflict.pilot_modified_at.replace(microsecond=0)
        actual_external = conflict.external_modified_at.replace(microsecond=0)
        expected_pilot = expected_pilot_modified_at.replace(microsecond=0)
        expected_external = expected_external_modified_at.replace(microsecond=0)

        return actual_pilot != expected_pilot or actual_external != expected_external

    # -----------------------------------------------------------------------
    # A33: Resolution-type validation
    # -----------------------------------------------------------------------

    @staticmethod
    def validate_resolution_for_conflict_type(
        conflict_type: str,
        resolution: str,
    ) -> bool:
        """
        Validate that the requested resolution action is legal for this conflict type.

        Returns True if valid.
        """
        return resolution in LEGAL_RESOLUTIONS.get(conflict_type, set())

    # -----------------------------------------------------------------------
    # A34: Two-tier effective setting resolvers (§D.3, §16.5)
    # -----------------------------------------------------------------------

    @staticmethod
    def get_effective_expire_days(db: Session, tenant_id: UUID) -> int | None:
        """
        Two-tier resolution for auto-expire days (post-FIND-086).

        Resolution chain (via platform_setting):
          1. Check calendar_conflict_auto_expire_enabled → if False return None
          2. Return effective calendar_conflict_auto_expire_days (tenant or platform default 60)

        Returns:
            int: effective expire days, or None if auto-expiry is disabled.
        """
        from services.setting_resolver import get_effective_setting

        enabled, _ = get_effective_setting(
            db, tenant_id, "calendar_conflict_auto_expire_enabled", fallback=True
        )
        if not enabled:
            return None
        days, _ = get_effective_setting(
            db, tenant_id, "calendar_conflict_auto_expire_days", fallback=60
        )
        return int(days)

    @staticmethod
    def get_effective_pre_warning_days(db: Session, tenant_id: UUID) -> int | None:
        """
        Two-tier resolution for pre-warning days (post-FIND-086).

        Returns:
            int: effective pre-warning days, or None if auto-expiry is disabled.
        """
        from services.setting_resolver import get_effective_setting

        enabled, _ = get_effective_setting(
            db, tenant_id, "calendar_conflict_auto_expire_enabled", fallback=True
        )
        if not enabled:
            return None
        days, _ = get_effective_setting(
            db, tenant_id, "calendar_conflict_pre_warning_days", fallback=14
        )
        return int(days)

    # -----------------------------------------------------------------------
    # A35: Pending conflicts count (used by status endpoint extension)
    # -----------------------------------------------------------------------

    @staticmethod
    def get_pending_conflicts_count(db: Session, tenant_id: UUID) -> int:
        """
        Return count of unresolved calendar_sync_conflict rows for a tenant.
        Used by A35 status endpoint extension.

        Note: Uses len() over func.count() to avoid SQLModel exec() issues
        with aggregate queries in transactional test sessions.
        """
        from app.models.scheduling import CalendarSyncConflict

        rows = db.exec(
            select(CalendarSyncConflict.id).where(  # type: ignore[arg-type]
                CalendarSyncConflict.tenant_id == tenant_id,
                CalendarSyncConflict.resolution.is_(None),  # type: ignore[union-attr]
            )
        ).all()
        return len(rows)

    # -----------------------------------------------------------------------
    # A35: Rate-limit check for conflict-detection push notifications
    # -----------------------------------------------------------------------

    @staticmethod
    def count_recent_conflict_notifications(
        db: Session,
        tenant_id: UUID,
        window_hours: int = 1,
    ) -> int:
        """
        A35 rate-limit check: count push notifications for calendar conflict-detection
        events in the last `window_hours` for a tenant.

        Rate limit: max 4 per tenant per hour. Fifth+ collapse to batched notification.

        Returns:
            int: count of conflict-detection push notifications in window.
        """
        from app.models.system import NotificationOutbox

        # B8/A51: 'push' channel (APNs/FCM) is deferred to B8. Use 'in_app' for B6.
        cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
        rows = db.exec(
            select(NotificationOutbox.id).where(  # type: ignore[arg-type]
                NotificationOutbox.tenant_id == tenant_id,
                NotificationOutbox.channel == "in_app",
                NotificationOutbox.created_at >= cutoff,
                NotificationOutbox.contextdata[  # type: ignore[index]
                    "event_type"
                ].as_string()
                == "calendar_conflict_detected",
            )
        ).all()
        return len(rows)

    # -----------------------------------------------------------------------
    # A36: Voice readback summary
    # -----------------------------------------------------------------------

    @staticmethod
    def build_voice_readback_summary(
        conflict: Any,  # CalendarSyncConflict ORM object
        field_diffs: list[dict[str, Any]],
        chosen_side: str,  # 'pilot' | 'external'
    ) -> str:
        """
        A36 server-side voice readback copy template.

        Renders the confirm-as-turn spoken summary from the field_diffs payload.

        Template:
          "Accepting the {side} version of {conflict_identifier}.
           That keeps: {summary of chosen side}.
           That discards: {summary of rejected side}.
           Confirm?"
        """
        side_label = "Pilot" if chosen_side == "pilot" else "Google Calendar"
        rejected_label = "Google Calendar" if chosen_side == "pilot" else "Pilot"

        # Build human-readable summary of changes per side
        kept_changes = []
        discarded_changes = []

        for diff in field_diffs:
            field = diff["field_name"].replace("_", " ")
            kept_val = (
                diff["pilot_value"]
                if chosen_side == "pilot"
                else diff["external_value"]
            )
            discarded_val = (
                diff["external_value"]
                if chosen_side == "pilot"
                else diff["pilot_value"]
            )

            if kept_val is not None:
                kept_changes.append(f"{field}: {kept_val}")
            if discarded_val is not None:
                discarded_changes.append(f"{field}: {discarded_val}")

        kept_summary = ", ".join(kept_changes[:3]) if kept_changes else "no changes"
        discarded_summary = (
            ", ".join(discarded_changes[:3]) if discarded_changes else "no changes"
        )

        # Build identifier from job context if available in snapshot
        pilot_snapshot = conflict.local_snapshot or {}
        job_title = (
            pilot_snapshot.get("title")
            or pilot_snapshot.get("summary")
            or str(conflict.job_id)[:8]
        )

        return (
            f"Accepting the {side_label} version of {job_title}. "
            f"That keeps: {kept_summary}. "
            f"That discards the {rejected_label} version: {discarded_summary}. "
            f"Confirm?"
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _compute_change(
    base_val: Any,
    current_val: Any,
    key: str,
    base_snapshot: dict[str, Any],
) -> str:
    """Determine the §16.2 change vocabulary for a single field."""
    key_in_base = key in base_snapshot

    if not key_in_base and current_val is not None:
        return CHANGE_ADDED
    if key_in_base and current_val is None:
        return CHANGE_REMOVED
    if base_val == current_val:
        return CHANGE_UNCHANGED
    return CHANGE_MODIFIED
