"""
wip_service.py — UP-1 (Part A)

Work-In-Progress (WIP) report: per-active-job actuals + ETC-projected cost
vs quoted budget, with deviation % and projected margin %.

Read-only SQL aggregation; no writes. Tenant-scoped throughout (Rule 6).
Money math via Decimal + ROUND_HALF_UP; never float on cents (Rule 13).

Consumes:
  - job.actual_labor_cost_cents / actual_material_cost_cents (maintained by
    profitability_rollup task)
  - job_time_entry.hours_remaining_estimate / hourly_rate_cents / etc_captured_at
    (latest per job via DISTINCT ON — anti-N+1)
  - quote.total_cents via job.quote_id (LEFT JOIN; nullable)
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACTIVE_STATUS_CODES = ["scheduled", "in_progress"]

# All known platform-level job_status codes (MCP-verified 2026-07-29).
# Used to validate the ?status= CSV before hitting the DB.
KNOWN_STATUS_CODES = {"draft", "scheduled", "in_progress", "completed", "cancelled"}

VALID_SORT = {
    "deviation_pct",
    "projected_margin_pct",
    "actual_cost_cents",
    "scheduled_start_at",
}

VALID_ORDER = {"asc", "desc"}

# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_WIP_SQL = """
WITH latest_etc AS (
    SELECT DISTINCT ON (jte.job_id)
        jte.job_id,
        jte.hours_remaining_estimate,
        jte.hourly_rate_cents
    FROM job_time_entry jte
    WHERE jte.tenant_id = :tenant_id
      AND jte.hours_remaining_estimate IS NOT NULL
      AND jte.etc_captured_at IS NOT NULL
    ORDER BY jte.job_id, jte.etc_captured_at DESC
)
SELECT
    j.id::text                                   AS job_id,
    j.job_number                                 AS job_number,
    j.title                                      AS title,
    js.code                                      AS status_code,
    j.scheduled_start_at                         AS scheduled_start_at,
    COALESCE(
        NULLIF(c.display_name, ''),
        NULLIF(c.company_name, ''),
        NULLIF(TRIM(CONCAT(COALESCE(c.first_name,''), ' ', COALESCE(c.last_name,''))), '')
    )                                            AS customer_name,
    s.name                                       AS site_name,
    q.total_cents                                AS quoted_budget_cents,
    j.actual_labor_cost_cents                    AS actual_labor_cost_cents,
    j.actual_material_cost_cents                 AS actual_material_cost_cents,
    le.hours_remaining_estimate                  AS etc_hours_remaining,
    le.hourly_rate_cents                         AS etc_hourly_rate_cents
FROM job j
JOIN job_status js ON js.id = j.status_id
LEFT JOIN customer c ON c.id = j.customer_id
LEFT JOIN site s ON s.id = j.site_id
LEFT JOIN quote q ON q.id = j.quote_id
LEFT JOIN latest_etc le ON le.job_id = j.id
WHERE j.tenant_id = :tenant_id
  AND j.is_active = true
  AND js.code = ANY(:status_codes)
"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_wip_report(
    db: Session,
    tenant_id: UUID,
    status_codes: list[str] | None = None,
    sort: str = "deviation_pct",
    order: str = "desc",
) -> dict[str, Any]:
    """Compute the WIP report for all active jobs in a tenant.

    For each active job (job_status.code IN status_codes):
      actual_cost      = actual_labor_cost_cents + actual_material_cost_cents
      etc_cost         = round(latest_etc_hours_remaining * etc_hourly_rate_cents)
                         via Decimal ROUND_HALF_UP
      projected_cost   = actual_cost + etc_cost
      budget           = quote.total_cents (None if no quote)
      projected_margin = (budget - projected_cost) / budget * 100  (None if no budget)
      deviation_pct    = same as projected_margin (negative = over budget)
      has_etc          = latest ETC row exists with non-null hours_remaining_estimate

    Args:
        db:           Open SQLModel Session (sync).
        tenant_id:    Tenant UUID (enforces isolation).
        status_codes: Job status codes to include; defaults to ACTIVE_STATUS_CODES.
        sort:         Sort field (one of VALID_SORT).
        order:        'asc' | 'desc'.

    Returns:
        dict with keys:
          margin_target_pct (int),
          summary (dict),
          rows (list[dict]).
    """
    from services.report_service import get_margin_settings

    codes = status_codes if status_codes else ACTIVE_STATUS_CODES

    # Margin target (WIP does not bucket — only needs target_pct)
    _boundaries, target_pct = get_margin_settings(db, tenant_id)

    # --- Fetch active jobs + latest ETC in one batched query (no N+1) ---
    rows_raw = db.exec(
        text(_WIP_SQL).bindparams(
            tenant_id=str(tenant_id),
            status_codes=codes,
        )
    ).fetchall()

    # --- Python-side computation per row (Decimal money math) ---
    rows: list[dict[str, Any]] = []
    for row in rows_raw:
        actual_labor = int(row.actual_labor_cost_cents or 0)
        actual_material = int(row.actual_material_cost_cents or 0)
        actual_cost = actual_labor + actual_material

        etc_hours = row.etc_hours_remaining  # Decimal | None
        etc_rate = row.etc_hourly_rate_cents  # int | None

        if etc_hours is not None and etc_rate is not None:
            etc_cost = int(
                (Decimal(str(etc_hours)) * Decimal(etc_rate)).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            )
            has_etc = True
            etc_hours_float = float(etc_hours)
        else:
            etc_cost = 0
            has_etc = False
            etc_hours_float = None

        projected_cost = actual_cost + etc_cost

        budget = row.quoted_budget_cents  # int | None
        if budget is not None and budget > 0:
            margin_pct = round(
                float(Decimal(budget - projected_cost) / Decimal(budget) * 100),
                2,
            )
            projected_margin_pct: float | None = margin_pct
            budget_deviation_pct: float | None = margin_pct
            below_margin_target = margin_pct < target_pct
        else:
            projected_margin_pct = None
            budget_deviation_pct = None
            below_margin_target = False

        rows.append(
            {
                "job_id": row.job_id,
                "job_number": row.job_number,
                "title": row.title,
                "customer_name": row.customer_name,
                "site_name": row.site_name,
                "status_code": row.status_code,
                "scheduled_start_at": row.scheduled_start_at,
                "quoted_budget_cents": budget,
                "actual_cost_cents": actual_cost,
                "etc_hours_remaining": etc_hours_float,
                "etc_cost_cents": etc_cost,
                "projected_cost_cents": projected_cost,
                "projected_margin_pct": projected_margin_pct,
                "budget_deviation_pct": budget_deviation_pct,
                "has_etc": has_etc,
                "below_margin_target": below_margin_target,
            }
        )

    # --- Sort in Python (None values always sort last) ---
    rows = _sort_rows(rows, sort, order)

    # --- Summary block ---
    summary = {
        "active_job_count": len(rows),
        "total_actual_cost_cents": sum(r["actual_cost_cents"] for r in rows),
        "total_quoted_budget_cents": sum(r["quoted_budget_cents"] or 0 for r in rows),
        "total_projected_cost_cents": sum(r["projected_cost_cents"] for r in rows),
        "jobs_over_budget_count": sum(
            1
            for r in rows
            if r["budget_deviation_pct"] is not None and r["budget_deviation_pct"] < 0
        ),
        "jobs_below_margin_target_count": sum(
            1 for r in rows if r["below_margin_target"]
        ),
    }

    return {
        "margin_target_pct": target_pct,
        "summary": summary,
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _sort_rows(
    rows: list[dict[str, Any]], sort_field: str, order: str
) -> list[dict[str, Any]]:
    """Sort rows by ``sort_field``. ``None`` values always sort last.

    Args:
        rows:       List of row dicts.
        sort_field: Key to sort by (one of VALID_SORT).
        order:      'asc' | 'desc'.
    """
    with_value = [r for r in rows if r.get(sort_field) is not None]
    without_value = [r for r in rows if r.get(sort_field) is None]
    with_value.sort(key=lambda r: r[sort_field], reverse=(order == "desc"))
    return with_value + without_value
