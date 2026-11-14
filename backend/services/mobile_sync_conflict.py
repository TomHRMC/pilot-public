"""
services/mobile_sync_conflict.py

Conflict Severity Classification Engine for mobile offline sync.
Established in B7b/A40. Consumed by A42, A45, A46 within this batch,
and by B8/A47, B8/A48 in the next batch.

Pattern: §16.6 Four-Class Severity
    auto_silent | auto_notice | tech_resolvable | owner_escalation

Resolution order in classify_sync_conflict():
    1. Tenant-specific override row (tenant_id matches, is_active=True)
    2. Platform default row (tenant_id IS NULL, is_active=True)
    3. Fallback: 'tech_resolvable' with generic reason if no matching row

§F.8 (design doc): Tenant overrides supported in schema but disabled in MVP UI.
Only Operator role can insert non-NULL tenant rows directly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlmodel import Session, select

from app.models.system import SyncConflictClassificationMatrix

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SyncResolution:
    """
    Output of classify_sync_conflict(). Drives all downstream routing decisions.

    Fields:
        severity: The four-class classification result.
        auto_resolved: True if system resolves without user action
            (auto_silent / auto_notice).
        tech_action_required: True if tech must choose a resolution
            (tech_resolvable).
        owner_escalation_required: True if the conflict must route to owner.
        classification_reason: Human-readable reason returned in API response
            and stored in mobile_sync_owner_escalation.escalation_reason_explainer.
        payload: Resolution-specific data (e.g. renamed category mapping
            for auto_notice).
    """

    severity: str  # 'auto_silent'|'auto_notice'|'tech_resolvable'|'owner_escalation'
    auto_resolved: bool
    tech_action_required: bool
    owner_escalation_required: bool
    classification_reason: str
    payload: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Classification engine
# ---------------------------------------------------------------------------


def classify_sync_conflict(
    operation_type: str,
    trigger_condition: str,
    tenant_id: uuid.UUID,
    db: Session,
) -> SyncResolution:
    """
    Look up the classification matrix for the given operation_type + trigger_condition.

    Resolution order:
        1. Tenant-specific override row (tenant_id matches, is_active=True)
        2. Platform default row (tenant_id IS NULL, is_active=True)
        3. Fallback: 'tech_resolvable' with generic reason if no matching row.

    Args:
        operation_type: e.g. 'time_entry', 'expense', 'photo',
                        'status_change', 'change_order', 'loto_check'
        trigger_condition: e.g. 'job_still_assigned', 'job_reassigned',
                           'job_deleted', 'time_overlap'
        tenant_id: Active tenant UUID (for tenant override lookup)
        db: SQLModel Session

    Returns:
        SyncResolution dataclass with all routing flags populated.
    """
    # Step 1: Try tenant-specific override first
    matrix_row = db.exec(
        select(SyncConflictClassificationMatrix)
        .where(SyncConflictClassificationMatrix.operation_type == operation_type)
        .where(SyncConflictClassificationMatrix.trigger_condition == trigger_condition)
        .where(SyncConflictClassificationMatrix.tenant_id == tenant_id)
        .where(SyncConflictClassificationMatrix.is_active == True)
    ).first()

    # Step 2: Fall back to platform default (tenant_id IS NULL)
    if matrix_row is None:
        matrix_row = db.exec(
            select(SyncConflictClassificationMatrix)
            .where(SyncConflictClassificationMatrix.operation_type == operation_type)
            .where(
                SyncConflictClassificationMatrix.trigger_condition == trigger_condition
            )
            .where(SyncConflictClassificationMatrix.tenant_id == None)
            .where(SyncConflictClassificationMatrix.is_active == True)
        ).first()

    # Step 3: Generic fallback if no rule found
    if matrix_row is None:
        severity = "tech_resolvable"
        reason = f"No classification rule found for {operation_type}/{trigger_condition} — manual review required"
    else:
        severity = matrix_row.severity
        reason = matrix_row.classification_reason

    return _build_resolution(severity=severity, classification_reason=reason)


def _build_resolution(severity: str, classification_reason: str) -> SyncResolution:
    """Construct a SyncResolution from a severity string."""
    return SyncResolution(
        severity=severity,
        auto_resolved=(severity in ("auto_silent", "auto_notice")),
        tech_action_required=(severity == "tech_resolvable"),
        owner_escalation_required=(severity == "owner_escalation"),
        classification_reason=classification_reason,
        payload={},
    )


# ---------------------------------------------------------------------------
# Field diff engine
# ---------------------------------------------------------------------------


def compute_field_diffs(
    tech_version: dict[str, Any] | None,
    server_version: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """
    Compute field-level diffs between tech's captured payload and current server state.

    Follows the platform-wide track-changes diff vocabulary (mvp-arch.md §16.2):
        'unchanged' | 'modified' | 'added' | 'removed'

    Returns a list of field diff objects in the shape consumed by the frontend
    <DiffView> component — same format as A32 (B6) calendar conflict field_diffs:

    [
        {
            "field_name": str,
            "tech_value": Any | None,
            "server_value": Any | None,
            "tech_change": "unchanged" | "modified" | "added" | "removed",
            "server_change": "unchanged" | "modified" | "added" | "removed",
        },
        ...
    ]

    Args:
        tech_version: Payload from mobile_sync_event.operation_payload_summary
        server_version: Current server-side state fetched at conflict read time

    Returns:
        List of field diff dicts for the API response.
    """
    tech = tech_version or {}
    server = server_version or {}

    all_keys = set(tech.keys()) | set(server.keys())
    diffs: list[dict[str, Any]] = []

    for key in sorted(all_keys):
        tech_val = tech.get(key)
        server_val = server.get(key)
        in_tech = key in tech
        in_server = key in server

        if in_tech and in_server:
            if tech_val == server_val:
                tech_change = "unchanged"
                server_change = "unchanged"
            else:
                tech_change = "modified"
                server_change = "modified"
        elif in_tech and not in_server:
            tech_change = "removed"
            server_change = "added"
        else:
            tech_change = "added"
            server_change = "removed"

        diffs.append(
            {
                "field_name": key,
                "tech_value": tech_val,
                "server_value": server_val,
                "tech_change": tech_change,
                "server_change": server_change,
            }
        )

    return diffs


# ---------------------------------------------------------------------------
# Escalation explainer
# ---------------------------------------------------------------------------


def build_escalation_explainer(
    operation_type: str,
    trigger_condition: str,
    classification_reason: str,
) -> str:
    """
    Generate a human-readable escalation explainer string stored at creation time
    in mobile_sync_owner_escalation.escalation_reason_explainer.

    Deviates from the calendar conflict pattern (diff computed live) because the
    originating context can be lost between escalation creation and owner resolution.
    Storing the explainer at creation time preserves context for the owner.

    Args:
        operation_type: The operation type string (e.g. 'time_entry')
        trigger_condition: The trigger condition (e.g. 'job_deleted')
        classification_reason: The classification_reason from the matrix row

    Returns:
        Human-readable string, e.g.:
        "time_entry (job_deleted): Job deleted while you worked it — owner action required"
    """
    return (
        f"{operation_type} ({trigger_condition}): "
        f"{classification_reason} — owner action required"
    )
