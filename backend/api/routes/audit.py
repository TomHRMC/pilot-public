"""
Audit event logging API endpoints.

This module provides REST API endpoints for querying audit event history and
analyzing field-level changes to entities. All endpoints enforce tenant isolation
to prevent cross-tenant data leakage.

Design Specification: Task #20 - Audit Event Logging
Gap Reference: Gap #29 in phase-1-4-implementation-gap-analysis.md
Database Design: Section 8 - Audit Event Logging (pilot-db-process-v2.6h.md)

Endpoints:
    GET /audit/events - Query audit events with filtering and pagination
    GET /audit/diff/{entity_type}/{entity_id} - Field-level change history for specific entity

Security:
    - All endpoints require authentication
    - Tenant isolation enforced on all queries
    - RBAC permissions: audit.view
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func
from sqlmodel import Session, select

from app.models.system import AuditEvent
from core.auth import AuthenticatedUser
from core.db import get_db
from core.permissions import require_permission

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================


class AuditEventResponse(BaseModel):
    """Single audit event with metadata and change data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    occurred_at: datetime
    tenant_id: uuid.UUID
    user_id: uuid.UUID | None
    entity_name: str = Field(description="Table name (e.g., 'customer', 'quote')")
    entity_id: str = Field(description="Primary key of the entity")
    action: str = Field(description="Operation type: INSERT, UPDATE, DELETE")
    old_values: dict[str, Any] | None = Field(
        description="State before change (UPDATE/DELETE)"
    )
    new_values: dict[str, Any] | None = Field(
        description="State after change (INSERT/UPDATE)"
    )
    request_id: str | None = Field(description="HTTP request ID for tracing")


class AuditEventsListResponse(BaseModel):
    """Paginated list of audit events."""

    events: list[AuditEventResponse]
    total: int = Field(description="Total count of events matching filters")
    limit: int = Field(description="Page size used")
    offset: int = Field(description="Starting offset used")
    has_more: bool = Field(description="Whether more results exist beyond this page")


class FieldChange(BaseModel):
    """Single field-level change with old and new values."""

    field_name: str
    old_value: Any
    new_value: Any
    changed_at: datetime
    changed_by: uuid.UUID | None
    action: str = Field(description="INSERT, UPDATE, or DELETE")


class AuditDiffResponse(BaseModel):
    """Field-level change history for a specific entity."""

    entity_type: str
    entity_id: str
    changes: list[FieldChange]
    total_changes: int
    first_seen: datetime | None = Field(description="Earliest change timestamp")
    last_modified: datetime | None = Field(description="Latest change timestamp")


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/audit/events", response_model=AuditEventsListResponse)
def query_audit_events(
    entity_type: str | None = Query(
        None, description="Filter by table name (e.g., 'customer')"
    ),
    entity_id: str | None = Query(None, description="Filter by specific entity UUID"),
    user_id: uuid.UUID | None = Query(
        None, description="Filter by user who made the change"
    ),
    action: str | None = Query(
        None, description="Filter by operation: INSERT, UPDATE, DELETE"
    ),
    start_date: datetime | None = Query(
        None, description="Filter by occurred_at >= start_date"
    ),
    end_date: datetime | None = Query(
        None, description="Filter by occurred_at <= end_date"
    ),
    limit: int = Query(50, ge=1, le=500, description="Max records to return (1-500)"),
    offset: int = Query(
        0, ge=0, description="Number of records to skip for pagination"
    ),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("audit.view")),
):
    """
    Query audit events with filtering and pagination.

    Requires audit.view permission (typically accountant or owner roles).

    Returns a paginated list of audit events for the authenticated user's tenant.
    All queries are automatically scoped to the user's tenant to prevent data leakage.

    **Filters:**
    - `entity_type`: Table name (e.g., "customer", "quote", "invoice")
    - `entity_id`: Specific record UUID
    - `user_id`: Who made the change
    - `action`: Operation type (INSERT, UPDATE, DELETE)
    - `start_date`, `end_date`: Time range filters

    **Pagination:**
    - `limit`: Page size (default 50, max 500)
    - `offset`: Starting position (default 0)

    **Example:**
    ```
    GET /api/v1/audit/events?entity_type=customer&limit=100
    GET /api/v1/audit/events?entity_id=123e4567-e89b-12d3-a456-426614174000
    GET /api/v1/audit/events?start_date=2026-03-01T00:00:00Z&action=DELETE
    ```

    **Returns:** Paginated list of audit events with metadata
    """

    # Build query with tenant isolation (CRITICAL for security)
    query = select(AuditEvent).where(AuditEvent.tenant_id == current_user.tenant_id)

    # Apply optional filters
    if entity_type:
        query = query.where(AuditEvent.entity_name == entity_type)
    if entity_id:
        query = query.where(AuditEvent.entity_id == entity_id)
    if user_id:
        query = query.where(AuditEvent.user_id == user_id)
    if action:
        query = query.where(AuditEvent.action == action.upper())
    if start_date:
        query = query.where(AuditEvent.occurred_at >= start_date)
    if end_date:
        query = query.where(AuditEvent.occurred_at <= end_date)

    # Count total results (for pagination metadata)
    count_query = select(func.count()).select_from(query.subquery())
    total = db.exec(count_query).one()

    # Apply ordering and pagination
    query = query.order_by(AuditEvent.occurred_at.desc()).offset(offset).limit(limit)

    # Execute query
    events = db.exec(query).all()

    # Calculate has_more flag
    has_more = (offset + limit) < total

    return AuditEventsListResponse(
        events=[AuditEventResponse.model_validate(event) for event in events],
        total=total,
        limit=limit,
        offset=offset,
        has_more=has_more,
    )


@router.get("/audit/diff/{entity_type}/{entity_id}", response_model=AuditDiffResponse)
def get_field_level_diff(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("audit.view")),
):
    """
    Get field-level change history for a specific entity.

    Requires audit.view permission (typically accountant or owner roles).

    Returns a chronological list of all field changes for the specified entity,
    showing exactly what changed, when, and by whom. Useful for:
    - Debugging data issues ("Who changed the customer email?")
    - Compliance audits ("Show all changes to this invoice")
    - User accountability ("What did this user modify?")

    **Path Parameters:**
    - `entity_type`: Table name (e.g., "customer", "quote")
    - `entity_id`: UUID of the specific record

    **Example:**
    ```
    GET /api/v1/audit/diff/customer/123e4567-e89b-12d3-a456-426614174000
    ```

    **Returns:**
    Field-by-field change history showing:
    - field_name: Which field changed
    - old_value: Value before change
    - new_value: Value after change
    - changed_at: Timestamp of change
    - changed_by: User who made the change
    - action: INSERT, UPDATE, or DELETE

    **Example Response:**
    ```json
    {
      "entity_type": "customer",
      "entity_id": "123e4567-e89b-12d3-a456-426614174000",
      "changes": [
        {
          "field_name": "email",
          "old_value": "old@example.com",
          "new_value": "new@example.com",
          "changed_at": "2026-03-26T10:30:00Z",
          "changed_by": "user-uuid",
          "action": "UPDATE"
        }
      ],
      "total_changes": 5,
      "first_seen": "2026-03-20T08:00:00Z",
      "last_modified": "2026-03-26T10:30:00Z"
    }
    ```
    """

    # Query all events for this entity (tenant-isolated)
    query = (
        select(AuditEvent)
        .where(
            AuditEvent.tenant_id == current_user.tenant_id,
            AuditEvent.entity_name == entity_type,
            AuditEvent.entity_id == entity_id,
        )
        .order_by(AuditEvent.occurred_at.asc())
    )

    events = db.exec(query).all()

    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No audit history found for {entity_type} {entity_id}",
        )

    # Extract field-level changes
    field_changes: list[FieldChange] = []

    for event in events:
        if event.action == "INSERT":
            # All fields in new_values are "new" (no old values)
            for field_name, new_val in (event.new_values or {}).items():
                field_changes.append(
                    FieldChange(
                        field_name=field_name,
                        old_value=None,
                        new_value=new_val,
                        changed_at=event.occurred_at,
                        changed_by=event.user_id,
                        action="INSERT",
                    )
                )

        elif event.action == "UPDATE":
            # Compare old vs new to find changed fields
            old_vals = event.old_values or {}
            new_vals = event.new_values or {}

            # Get all fields that exist in either old or new
            all_fields = set(old_vals.keys()) | set(new_vals.keys())

            for field_name in all_fields:
                old_val = old_vals.get(field_name)
                new_val = new_vals.get(field_name)

                # Only include if the value actually changed
                if old_val != new_val:
                    field_changes.append(
                        FieldChange(
                            field_name=field_name,
                            old_value=old_val,
                            new_value=new_val,
                            changed_at=event.occurred_at,
                            changed_by=event.user_id,
                            action="UPDATE",
                        )
                    )

        elif event.action == "DELETE":
            # All fields in old_values are "deleted" (no new values)
            for field_name, old_val in (event.old_values or {}).items():
                field_changes.append(
                    FieldChange(
                        field_name=field_name,
                        old_value=old_val,
                        new_value=None,
                        changed_at=event.occurred_at,
                        changed_by=event.user_id,
                        action="DELETE",
                    )
                )

    # Calculate metadata
    first_seen = events[0].occurred_at if events else None
    last_modified = events[-1].occurred_at if events else None

    return AuditDiffResponse(
        entity_type=entity_type,
        entity_id=entity_id,
        changes=field_changes,
        total_changes=len(field_changes),
        first_seen=first_seen,
        last_modified=last_modified,
    )


@router.get("/audit/summary", response_model=dict[str, Any])
def get_audit_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_permission("audit.view")),
):
    """
    Get audit activity summary for the tenant.

    Returns aggregated statistics about audit events over the specified time period.
    Useful for:
    - Monitoring system activity
    - Identifying unusual patterns
    - Compliance reporting

    **Query Parameters:**
    - `days`: Number of days to analyze (1-365, default 30)

    **Example:**
    ```
    GET /api/v1/audit/summary?days=7
    ```

    **Returns:**
    ```json
    {
      "period_days": 30,
      "total_events": 1250,
      "by_action": {
        "INSERT": 500,
        "UPDATE": 600,
        "DELETE": 150
      },
      "by_entity_type": {
        "customer": 300,
        "quote": 450,
        "invoice": 250,
        "job": 250
      },
      "top_users": [
        {"user_id": "uuid", "event_count": 500},
        {"user_id": "uuid", "event_count": 300}
      ],
      "most_active_day": "2026-03-25",
      "events_per_day_avg": 41.7
    }
    ```
    """
    from datetime import UTC as utc
    from datetime import timedelta

    # Calculate date range
    end_date = datetime.now(utc)
    start_date = end_date - timedelta(days=days)

    # Base query with tenant isolation and date filter
    base_query = select(AuditEvent).where(
        AuditEvent.tenant_id == current_user.tenant_id,
        AuditEvent.occurred_at >= start_date,
        AuditEvent.occurred_at <= end_date,
    )

    # Total events count
    total_query = select(func.count()).select_from(base_query.subquery())
    total_events = db.exec(total_query).one()

    # Count by action type
    action_query = (
        select(AuditEvent.action, func.count(AuditEvent.id).label("count"))
        .where(
            AuditEvent.tenant_id == current_user.tenant_id,
            AuditEvent.occurred_at >= start_date,
        )
        .group_by(AuditEvent.action)
    )

    by_action = {row[0]: row[1] for row in db.exec(action_query).all()}

    # Count by entity type
    entity_query = (
        select(AuditEvent.entity_name, func.count(AuditEvent.id).label("count"))
        .where(
            AuditEvent.tenant_id == current_user.tenant_id,
            AuditEvent.occurred_at >= start_date,
        )
        .group_by(AuditEvent.entity_name)
        .order_by(func.count(AuditEvent.id).desc())
        .limit(10)
    )

    by_entity_type = {row[0]: row[1] for row in db.exec(entity_query).all()}

    # Top 5 most active users
    user_query = (
        select(AuditEvent.user_id, func.count(AuditEvent.id).label("count"))
        .where(
            AuditEvent.tenant_id == current_user.tenant_id,
            AuditEvent.occurred_at >= start_date,
            AuditEvent.user_id.isnot(None),
        )
        .group_by(AuditEvent.user_id)
        .order_by(func.count(AuditEvent.id).desc())
        .limit(5)
    )

    top_users = [
        {"user_id": str(row[0]), "event_count": row[1]}
        for row in db.exec(user_query).all()
    ]

    # Events per day average
    events_per_day_avg = round(total_events / days, 1) if days > 0 else 0

    return {
        "period_days": days,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_events": total_events,
        "by_action": by_action,
        "by_entity_type": by_entity_type,
        "top_users": top_users,
        "events_per_day_avg": events_per_day_avg,
    }
