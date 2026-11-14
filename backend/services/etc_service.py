"""
ETC (Estimate-to-Complete) Service — B3/A14.

Computes projected margin for jobs with ETC entries.
Consumed by: B3 A14 (projected-margin endpoint), B3 A16 (variance notification task).
"""

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session


def get_latest_etc_entries(
    db: Session,
    tenant_id: UUID,
    job_id: UUID,
) -> list[dict]:
    """Return the most recent ETC entry per (job_id, quote_line_id) combination.

    Uses DISTINCT ON pattern:
        DISTINCT ON (job_id, quote_line_id) ... ORDER BY job_id, quote_line_id, created_at DESC

    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID for IDOR isolation.
        job_id:    Target job UUID.
    Returns:
        list of dicts with keys: quote_line_id (UUID|None), hours_remaining_estimate (Decimal),
        captured_at (datetime). Empty list if no ETC entries exist.
    """
    # Raw SQL for DISTINCT ON pattern (SQLModel doesn't support DISTINCT ON natively)
    result = db.execute(
        text(
            """
            SELECT DISTINCT ON (quote_line_id)
                quote_line_id,
                hours_remaining_estimate,
                etc_captured_at,
                created_at
            FROM job_time_entry
            WHERE job_id = :job_id
              AND tenant_id = :tenant_id
              AND hours_remaining_estimate IS NOT NULL
            ORDER BY quote_line_id, created_at DESC
            """
        ),
        {"job_id": str(job_id), "tenant_id": str(tenant_id)},
    ).fetchall()

    return [
        {
            "quote_line_id": row.quote_line_id,
            "hours_remaining": Decimal(str(row.hours_remaining_estimate)),
            "captured_at": row.etc_captured_at or row.created_at,
        }
        for row in result
    ]


def compute_projected_margin(
    db: Session,
    tenant_id: UUID,
    job_id: UUID,
    hourly_rate_cents: int,
    quoted_total_cents: int,
    actual_labor_cost_cents: int,
    actual_material_cost_cents: int,
    margin_target_pct: int,
) -> dict:
    """Compute projected margin incorporating latest ETC values.

    Fallback logic: if no ETC entries exist,
    projected_total_hours = MAX(quoted_hours, hours_worked_so_far).

    Args:
        db:                         Open SQLModel session.
        tenant_id:                  Tenant UUID.
        job_id:                     Target job UUID.
        hourly_rate_cents:          Effective labor rate for projection.
        quoted_total_cents:         Original quote total in cents.
        actual_labor_cost_cents:    Actuals from job.actual_labor_cost_cents.
        actual_material_cost_cents: Actuals from job.actual_material_cost_cents.
        margin_target_pct:          From tenant_settings.margin_target_pct.
    Returns:
        dict with keys: projected_labor_cost_cents, projected_total_cents,
        projected_margin_pct (Decimal), below_margin_target (bool),
        etc_source ('per_task'|'per_job'|'fallback'), latest_etc_entries (list).
    """
    latest_entries = get_latest_etc_entries(db, tenant_id, job_id)

    hours_worked = (
        Decimal(str(actual_labor_cost_cents)) / Decimal(str(hourly_rate_cents))
        if hourly_rate_cents > 0
        else Decimal("0")
    )

    if latest_entries:
        # Sum remaining hours from all latest ETC entries
        total_remaining = sum(e["hours_remaining"] for e in latest_entries)

        # Determine source
        has_per_task = any(e["quote_line_id"] is not None for e in latest_entries)
        etc_source = "per_task" if has_per_task else "per_job"

        # Projected total = hours worked + hours remaining
        projected_total_hours = hours_worked + Decimal(str(total_remaining))
    else:
        # Fallback: use MAX(quoted_hours, hours_worked_so_far)
        etc_source = "fallback"
        quoted_hours = (
            Decimal(str(quoted_total_cents)) / Decimal(str(hourly_rate_cents))
            if hourly_rate_cents > 0
            else Decimal("0")
        )
        projected_total_hours = max(quoted_hours, hours_worked)

    projected_labor_cost_cents = int(
        (projected_total_hours * Decimal(str(hourly_rate_cents))).to_integral_value(
            ROUND_HALF_UP
        )
    )
    projected_total_cents = projected_labor_cost_cents + actual_material_cost_cents

    # Margin = (revenue - cost) / revenue
    if quoted_total_cents > 0:
        projected_margin_pct = (
            (Decimal(str(quoted_total_cents)) - Decimal(str(projected_total_cents)))
            / Decimal(str(quoted_total_cents))
            * 100
        ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    else:
        projected_margin_pct = Decimal("0")

    below_margin_target = projected_margin_pct < Decimal(str(margin_target_pct))

    return {
        "projected_labor_cost_cents": projected_labor_cost_cents,
        "projected_total_cents": projected_total_cents,
        "projected_margin_pct": projected_margin_pct,
        "below_margin_target": below_margin_target,
        "etc_source": etc_source,
        "latest_etc_entries": [
            {
                "quote_line_id": str(e["quote_line_id"])
                if e["quote_line_id"]
                else None,
                "hours_remaining": float(e["hours_remaining"]),
                "captured_at": e["captured_at"].isoformat()
                if e["captured_at"]
                else None,
            }
            for e in latest_entries
        ],
    }


def check_etc_variance(
    projected_total_hours: Decimal,
    quoted_hours: Decimal,
    notify_pct: int,
) -> tuple[bool, Decimal]:
    """Check whether ETC variance exceeds the owner notification threshold.

    Args:
        projected_total_hours: Sum of actuals + latest ETC.
        quoted_hours:          Original quoted labor hours.
        notify_pct:            tenant_settings.etc_variance_owner_notify_pct.
    Returns:
        tuple: (should_notify: bool, variance_pct: Decimal)
    """
    if quoted_hours == 0:
        return False, Decimal("0")
    variance_pct = (projected_total_hours / quoted_hours - 1) * 100
    return variance_pct >= notify_pct, variance_pct
