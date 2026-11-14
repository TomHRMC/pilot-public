"""
report_service.py — B5/A5

Aggregation functions for all six MVP report types.
All functions are read-only SQL aggregations; no writes occur here.
Consumes: job.actual_labor_cost_cents/material/profit (cached by profitability_rollup task)

# TODO: Redis cache if p95 > 2s at production volume (B5/F8 deferral note)
"""

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def get_report_chart_threshold(db: Session, tenant_id: UUID) -> int:
    """Read report_chart_threshold from platform_setting.

    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID.
    Returns:
        int: threshold value (platform default 8 if no seed row found).
    """
    from services.setting_resolver import get_effective_setting

    val, _ = get_effective_setting(db, tenant_id, "report_chart_threshold", fallback=8)
    return int(val)


def get_margin_settings(db: Session, tenant_id: UUID) -> tuple[list[int], int]:
    """Read margin_bucket_boundaries and margin_target_pct from platform_setting.

    Returns:
        (boundaries, target_pct) — e.g. ([10, 20, 30], 20)
    """
    from services.setting_resolver import get_effective_setting

    boundaries_val, _ = get_effective_setting(
        db, tenant_id, "margin_bucket_boundaries", fallback=[10, 20, 30]
    )
    target_val, _ = get_effective_setting(
        db, tenant_id, "margin_target_pct", fallback=20
    )
    boundaries = (
        list(boundaries_val) if isinstance(boundaries_val, list) else [10, 20, 30]
    )
    return boundaries, int(target_val)


def compute_display_mode(row_count: int, threshold: int) -> str:
    """Return 'chart' if row_count < threshold, else 'table'.

    Args:
        row_count: Number of data rows in the report response.
        threshold: Value from get_report_chart_threshold().
    Returns:
        str: 'chart' | 'table'
    """
    return "chart" if row_count < threshold else "table"


def classify_margin_bucket(
    margin_pct: float | None, boundaries: list[int]
) -> str | None:
    """Classify a margin percentage into tenant-configured buckets.

    Args:
        margin_pct: Computed margin percentage; None if quoted_total_cents = 0.
        boundaries: Sorted list from tenant_settings.margin_bucket_boundaries.
    Returns:
        str: Bucket label (e.g., '<10', '10–20', '30+') or None if margin_pct is None.
    """
    if margin_pct is None:
        return None
    sorted_b = sorted(boundaries)
    for i, bound in enumerate(sorted_b):
        if margin_pct < bound:
            if i == 0:
                return f"<{bound}"
            return f"{sorted_b[i - 1]}–{bound}"
    return f"{sorted_b[-1]}+"


# ---------------------------------------------------------------------------
# 1. Profitability report
# ---------------------------------------------------------------------------


def get_profitability_report(
    db: Session,
    tenant_id: UUID,
    date_from: date,
    date_to: date,
    group_by: str = "job",
    filter_status: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Aggregate job profitability data from cached job financial columns.

    Uses job.actual_labor_cost_cents/material_cost_cents (written by profitability_rollup task)
    and job.quote_id → quote.total_cents as margin denominator (per F2 resolution).

    Args:
        db:            Open SQLModel session.
        tenant_id:     Tenant UUID (enforces isolation).
        date_from:     Report period start (inclusive), filters on job.scheduled_start_at.
        date_to:       Report period end (inclusive).
        group_by:      'job' | 'customer' | 'site'
        filter_status: Optional list of job_status.code values to include.
    Returns:
        list of dicts with keys: group_key, group_label, job_count, quoted_total_cents,
        actual_labor_cost_cents, actual_material_cost_cents, actual_profit_cents,
        margin_pct, margin_bucket, below_margin_target.
    """
    boundaries, target_pct = get_margin_settings(db, tenant_id)

    if group_by == "customer":
        group_select = "c.id::text AS group_key, c.name AS group_label"
        group_clause = "c.id, c.name"
        join_clause = "JOIN customer c ON c.id = j.customer_id"
    elif group_by == "site":
        group_select = "s.id::text AS group_key, s.name AS group_label"
        group_clause = "s.id, s.name"
        join_clause = "JOIN site s ON s.id = j.site_id"
    else:  # default: job
        group_select = (
            "j.id::text AS group_key, "
            "COALESCE(j.job_number, j.id::text) AS group_label, "
            "c.display_name AS customer_name"
        )
        group_clause = "j.id, j.job_number, c.display_name"
        join_clause = "LEFT JOIN customer c ON c.id = j.customer_id"

    status_filter_sql = ""
    if filter_status:
        codes_list = ", ".join(f"'{c}'" for c in filter_status)
        status_filter_sql = f"AND js.code IN ({codes_list})"

    sql = f"""
        SELECT
            {group_select},
            COUNT(DISTINCT j.id) AS job_count,
            COALESCE(SUM(q.total_cents), 0) AS quoted_total_cents,
            COALESCE(SUM(j.actual_labor_cost_cents), 0) AS actual_labor_cost_cents,
            COALESCE(SUM(j.actual_material_cost_cents), 0) AS actual_material_cost_cents,
            COALESCE(SUM(j.actual_profit_cents), 0) AS actual_profit_cents
        FROM job j
        LEFT JOIN quote q ON q.id = j.quote_id
        LEFT JOIN job_status js ON js.id = j.status_id
        {join_clause}
        WHERE j.tenant_id = :tenant_id
          AND j.is_active = true
          AND j.scheduled_start_at::date >= :date_from
          AND j.scheduled_start_at::date <= :date_to
          {status_filter_sql}
        GROUP BY {group_clause}
        ORDER BY {group_clause}
    """
    rows = db.exec(
        text(sql).bindparams(
            tenant_id=str(tenant_id),
            date_from=str(date_from),
            date_to=str(date_to),
        )
    ).fetchall()

    result = []
    for row in rows:
        quoted = int(row.quoted_total_cents or 0)
        labor = int(row.actual_labor_cost_cents or 0)
        material = int(row.actual_material_cost_cents or 0)

        if quoted > 0:
            margin_pct = round((quoted - labor - material) / quoted * 100, 2)
        else:
            margin_pct = None

        bucket = classify_margin_bucket(margin_pct, boundaries)
        below_target = margin_pct is not None and margin_pct < target_pct

        result.append(
            {
                "group_key": row.group_key,
                "group_label": row.group_label,
                "customer_name": getattr(row, "customer_name", None),
                "job_count": int(row.job_count),
                "quoted_total_cents": quoted,
                "actual_labor_cost_cents": labor,
                "actual_material_cost_cents": material,
                "actual_profit_cents": int(row.actual_profit_cents or 0),
                "margin_pct": margin_pct,
                "margin_bucket": bucket,
                "below_margin_target": below_target,
            }
        )
    return result


# ---------------------------------------------------------------------------
# 2. Revenue report
# ---------------------------------------------------------------------------


def get_revenue_report(
    db: Session,
    tenant_id: UUID,
    date_from: date,
    date_to: date,
    group_by: str = "month",
) -> list[dict[str, Any]]:
    """Aggregate invoiced vs collected revenue by period.

    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID.
        date_from: Period start (inclusive), filters on invoice.issued_at / payment.paid_at.
        date_to:   Period end (inclusive).
        group_by:  'month' | 'week' | 'quarter'
    Returns:
        list of dicts with keys: period_label, period_start, period_end,
        invoiced_cents, collected_cents, outstanding_cents, invoice_count, payment_count.
    """
    if group_by == "week":
        trunc_fn = "week"
        label_fmt = "IYYY-IW"  # ISO year-week
    elif group_by == "quarter":
        trunc_fn = "quarter"
        label_fmt = "YYYY-Q"
    else:
        trunc_fn = "month"
        label_fmt = "YYYY-MM"

    sql = f"""
        WITH invoice_periods AS (
            SELECT
                DATE_TRUNC('{trunc_fn}', issued_at)::date AS period_start,
                COALESCE(SUM(total_cents), 0) AS invoiced_cents,
                COUNT(*) AS invoice_count
            FROM invoice
            WHERE tenant_id = :tenant_id
              AND is_active = true
              AND issued_at::date >= :date_from
              AND issued_at::date <= :date_to
            GROUP BY DATE_TRUNC('{trunc_fn}', issued_at)
        ),
        payment_periods AS (
            SELECT
                DATE_TRUNC('{trunc_fn}', paid_at)::date AS period_start,
                COALESCE(SUM(amount_cents), 0) AS collected_cents,
                COUNT(*) AS payment_count
            FROM payment
            WHERE tenant_id = :tenant_id
              AND is_active = true
              AND paid_at::date >= :date_from
              AND paid_at::date <= :date_to
            GROUP BY DATE_TRUNC('{trunc_fn}', paid_at)
        ),
        all_periods AS (
            SELECT period_start FROM invoice_periods
            UNION
            SELECT period_start FROM payment_periods
        )
        SELECT
            ap.period_start,
            COALESCE(ip.invoiced_cents, 0) AS invoiced_cents,
            COALESCE(ip.invoice_count, 0) AS invoice_count,
            COALESCE(pp.collected_cents, 0) AS collected_cents,
            COALESCE(pp.payment_count, 0) AS payment_count
        FROM all_periods ap
        LEFT JOIN invoice_periods ip ON ip.period_start = ap.period_start
        LEFT JOIN payment_periods pp ON pp.period_start = ap.period_start
        ORDER BY ap.period_start
    """
    rows = db.exec(
        text(sql).bindparams(
            tenant_id=str(tenant_id),
            date_from=str(date_from),
            date_to=str(date_to),
        )
    ).fetchall()

    result = []
    for row in rows:
        period_start = row.period_start
        invoiced = int(row.invoiced_cents or 0)
        collected = int(row.collected_cents or 0)

        # Compute period_end: last day of the trunc period
        if group_by == "week":
            from datetime import timedelta

            period_end = period_start + timedelta(days=6)
            label = period_start.strftime("%Y-W%W")
        elif group_by == "quarter":
            import math

            q = math.ceil(period_start.month / 3)
            period_end_month = q * 3
            import calendar

            _, last_day = calendar.monthrange(period_start.year, period_end_month)
            period_end = date(period_start.year, period_end_month, last_day)
            label = f"{period_start.year}-Q{q}"
        else:
            import calendar

            _, last_day = calendar.monthrange(period_start.year, period_start.month)
            period_end = date(period_start.year, period_start.month, last_day)
            label = period_start.strftime("%Y-%m")

        result.append(
            {
                "period_label": label,
                "period_start": period_start,
                "period_end": period_end,
                "invoiced_cents": invoiced,
                "collected_cents": collected,
                "outstanding_cents": invoiced - collected,
                "invoice_count": int(row.invoice_count or 0),
                "payment_count": int(row.payment_count or 0),
            }
        )
    return result


# ---------------------------------------------------------------------------
# 3. AR Aging report
# ---------------------------------------------------------------------------


def get_ar_aging_report(
    db: Session,
    tenant_id: UUID,
    as_of_date: date,
) -> dict[str, Any]:
    """Compute accounts-receivable aging buckets as of a given date.

    Args:
        db:          Open SQLModel session.
        tenant_id:   Tenant UUID.
        as_of_date:  Aging computed as of this date (typically date_to from request).
    Returns:
        dict with keys: as_of_date, summary, data.
        Only includes invoices with balance_due_cents > 0 and is_active = true.
        due_at IS NULL → current bucket (not overdue).
    """
    sql = """
        SELECT
            c.id AS customer_id,
            c.display_name AS customer_name,
            -- current: not yet due or null due_at
            COALESCE(SUM(
                CASE WHEN i.due_at IS NULL
                       OR (CAST(:as_of_date AS date) - i.due_at::date) <= 0
                     THEN i.balance_due_cents ELSE 0 END
            ), 0) AS current_cents,
            -- 31-60 days overdue
            COALESCE(SUM(
                CASE WHEN (CAST(:as_of_date AS date) - i.due_at::date) BETWEEN 1 AND 60
                         AND (CAST(:as_of_date AS date) - i.due_at::date) >= 31
                     THEN i.balance_due_cents ELSE 0 END
            ), 0) AS bucket_31_60_cents,
            -- 61-90 days overdue
            COALESCE(SUM(
                CASE WHEN (CAST(:as_of_date AS date) - i.due_at::date) BETWEEN 61 AND 90
                     THEN i.balance_due_cents ELSE 0 END
            ), 0) AS bucket_61_90_cents,
            -- 91+ days overdue
            COALESCE(SUM(
                CASE WHEN (CAST(:as_of_date AS date) - i.due_at::date) > 90
                     THEN i.balance_due_cents ELSE 0 END
            ), 0) AS bucket_91_plus_cents,
            SUM(i.balance_due_cents) AS total_outstanding_cents,
            MIN(i.due_at::date) FILTER (WHERE i.due_at IS NOT NULL) AS oldest_invoice_due_at
        FROM invoice i
        JOIN customer c ON c.id = i.customer_id
        WHERE i.tenant_id = :tenant_id
          AND i.is_active = true
          AND i.balance_due_cents > 0
        GROUP BY c.id, c.display_name
        HAVING SUM(i.balance_due_cents) > 0
        ORDER BY c.display_name
    """
    rows = db.exec(
        text(sql).bindparams(
            tenant_id=str(tenant_id),
            as_of_date=str(as_of_date),
        )
    ).fetchall()

    data = []
    summary = {
        "current_cents": 0,
        "bucket_31_60_cents": 0,
        "bucket_61_90_cents": 0,
        "bucket_91_plus_cents": 0,
        "total_outstanding_cents": 0,
    }

    for row in rows:
        current = int(row.current_cents or 0)
        b31 = int(row.bucket_31_60_cents or 0)
        b61 = int(row.bucket_61_90_cents or 0)
        b91 = int(row.bucket_91_plus_cents or 0)
        total = int(row.total_outstanding_cents or 0)

        summary["current_cents"] += current
        summary["bucket_31_60_cents"] += b31
        summary["bucket_61_90_cents"] += b61
        summary["bucket_91_plus_cents"] += b91
        summary["total_outstanding_cents"] += total

        oldest_due = row.oldest_invoice_due_at
        data.append(
            {
                "customer_id": row.customer_id,
                "customer_name": row.customer_name,
                "current_cents": current,
                "bucket_31_60_cents": b31,
                "bucket_61_90_cents": b61,
                "bucket_91_plus_cents": b91,
                "total_outstanding_cents": total,
                "oldest_invoice_due_at": oldest_due,
            }
        )

    return {"as_of_date": as_of_date, "summary": summary, "data": data}


# ---------------------------------------------------------------------------
# 4. Tech productivity report
# ---------------------------------------------------------------------------


def get_tech_productivity_report(
    db: Session,
    tenant_id: UUID,
    date_from: date,
    date_to: date,
    group_by: str = "user",
    user_id: UUID | None = None,
) -> list[dict[str, Any]]:
    """Aggregate technician productivity from job_time_entry.

    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID.
        date_from: Period start (inclusive), filters on job_time_entry.started_at.
        date_to:   Period end (inclusive).
        group_by:  'user' | 'job_status'
        user_id:   Optional filter to single technician.
    Returns:
        list of dicts with keys: user_id, user_full_name, jobs_worked,
        jobs_completed, total_hours_logged, avg_hours_per_job, total_labor_cost_cents.
    """
    user_filter_sql = ""
    if user_id:
        user_filter_sql = "AND jte.user_id = :user_id"

    sql = f"""
        SELECT
            u.id AS user_id,
            CONCAT(COALESCE(u.first_name, ''), ' ', COALESCE(u.last_name, '')) AS user_full_name,
            COUNT(DISTINCT jte.job_id) AS jobs_worked,
            COUNT(DISTINCT j.id) FILTER (WHERE js.is_terminal = true) AS jobs_completed,
            COALESCE(SUM(jte.hours)::float, 0) AS total_hours_logged,
            COALESCE(SUM(jte.total_cost_cents), 0) AS total_labor_cost_cents
        FROM job_time_entry jte
        JOIN "user" u ON u.id = jte.user_id
        JOIN job j ON j.id = jte.job_id
        JOIN job_status js ON js.id = j.status_id
        WHERE jte.tenant_id = :tenant_id
          AND jte.started_at::date >= :date_from
          AND jte.started_at::date <= :date_to
          {user_filter_sql}
        GROUP BY u.id, u.first_name, u.last_name
        ORDER BY u.last_name, u.first_name
    """
    params: dict[str, Any] = {
        "tenant_id": str(tenant_id),
        "date_from": str(date_from),
        "date_to": str(date_to),
    }
    if user_id:
        params["user_id"] = str(user_id)

    rows = db.exec(text(sql).bindparams(**params)).fetchall()

    result = []
    for row in rows:
        jobs_worked = int(row.jobs_worked or 0)
        total_hours = float(row.total_hours_logged or 0)
        avg_hours = round(total_hours / jobs_worked, 2) if jobs_worked > 0 else None

        result.append(
            {
                "user_id": row.user_id,
                "user_full_name": row.user_full_name.strip(),
                "jobs_worked": jobs_worked,
                "jobs_completed": int(row.jobs_completed or 0),
                "total_hours_logged": total_hours,
                "avg_hours_per_job": avg_hours,
                "total_labor_cost_cents": int(row.total_labor_cost_cents or 0),
            }
        )
    return result


# ---------------------------------------------------------------------------
# 5. Tax liability report
# ---------------------------------------------------------------------------


def get_tax_liability_report(
    db: Session,
    tenant_id: UUID,
    date_from: date,
    date_to: date,
    group_by: str = "month",
) -> list[dict[str, Any]]:
    """Aggregate tax liability from invoice.tax_cents by period.

    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID.
        date_from: Period start (inclusive), filters on invoice.issued_at.
        date_to:   Period end (inclusive).
        group_by:  'month' | 'quarter'
    Returns:
        list of dicts with keys: period_label, period_start, period_end,
        invoice_count, total_invoiced_cents, total_tax_cents, effective_tax_rate_pct.
    """
    trunc_fn = "quarter" if group_by == "quarter" else "month"

    sql = f"""
        SELECT
            DATE_TRUNC('{trunc_fn}', issued_at)::date AS period_start,
            COUNT(*) AS invoice_count,
            COALESCE(SUM(total_cents), 0) AS total_invoiced_cents,
            COALESCE(SUM(tax_cents), 0) AS total_tax_cents
        FROM invoice
        WHERE tenant_id = :tenant_id
          AND is_active = true
          AND issued_at::date >= :date_from
          AND issued_at::date <= :date_to
        GROUP BY DATE_TRUNC('{trunc_fn}', issued_at)
        ORDER BY period_start
    """
    rows = db.exec(
        text(sql).bindparams(
            tenant_id=str(tenant_id),
            date_from=str(date_from),
            date_to=str(date_to),
        )
    ).fetchall()

    result = []
    for row in rows:
        period_start = row.period_start
        total_invoiced = int(row.total_invoiced_cents or 0)
        total_tax = int(row.total_tax_cents or 0)

        if group_by == "quarter":
            import calendar
            import math

            q = math.ceil(period_start.month / 3)
            period_end_month = q * 3
            _, last_day = calendar.monthrange(period_start.year, period_end_month)
            period_end = date(period_start.year, period_end_month, last_day)
            label = f"{period_start.year}-Q{q}"
        else:
            import calendar

            _, last_day = calendar.monthrange(period_start.year, period_start.month)
            period_end = date(period_start.year, period_start.month, last_day)
            label = period_start.strftime("%Y-%m")

        effective_rate = None
        if total_invoiced > 0:
            effective_rate = round(total_tax / total_invoiced * 100, 2)

        result.append(
            {
                "period_label": label,
                "period_start": period_start,
                "period_end": period_end,
                "invoice_count": int(row.invoice_count or 0),
                "total_invoiced_cents": total_invoiced,
                "total_tax_cents": total_tax,
                "effective_tax_rate_pct": effective_rate,
            }
        )
    return result


# ---------------------------------------------------------------------------
# 6. Voice analytics report
# ---------------------------------------------------------------------------


def get_voice_analytics_report(
    db: Session,
    tenant_id: UUID,
    date_from: date,
    date_to: date,
    group_by: str = "intent",
) -> dict[str, Any]:
    """Aggregate voice command analytics from voice_command_log.

    Args:
        db:        Open SQLModel session.
        tenant_id: Tenant UUID.
        date_from: Period start (inclusive), filters on voice_command_log.created_at.
        date_to:   Period end (inclusive).
        group_by:  'intent' | 'user' | 'day'
    Returns:
        dict with keys: summary and data.
        P95 latency computed via PostgreSQL PERCENTILE_CONT(0.95).
        Null latency rows excluded from averages per F5 resolution.
    """
    # Summary aggregation
    summary_sql = """
        SELECT
            COUNT(*) AS total_commands,
            COUNT(*) FILTER (WHERE is_successful = true) AS successful_commands,
            AVG(whisper_latency_ms) FILTER (WHERE whisper_latency_ms IS NOT NULL) AS avg_whisper_latency_ms,
            AVG(ollama_latency_ms)  FILTER (WHERE ollama_latency_ms IS NOT NULL)  AS avg_ollama_latency_ms,
            AVG(total_latency_ms)   FILTER (WHERE total_latency_ms IS NOT NULL)   AS avg_total_latency_ms,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_latency_ms)
                FILTER (WHERE total_latency_ms IS NOT NULL) AS p95_total_latency_ms
        FROM voice_command_log
        WHERE tenant_id = :tenant_id
          AND created_at::date >= :date_from
          AND created_at::date <= :date_to
    """
    summary_row = db.exec(
        text(summary_sql).bindparams(
            tenant_id=str(tenant_id),
            date_from=str(date_from),
            date_to=str(date_to),
        )
    ).first()

    total = int(summary_row.total_commands or 0)
    successful = int(summary_row.successful_commands or 0)
    success_rate = round(successful / total * 100, 2) if total > 0 else None

    def _round_or_none(v: Any) -> float | None:
        return round(float(v), 2) if v is not None else None

    summary = {
        "total_commands": total,
        "successful_commands": successful,
        "success_rate_pct": success_rate,
        "avg_whisper_latency_ms": _round_or_none(summary_row.avg_whisper_latency_ms),
        "avg_ollama_latency_ms": _round_or_none(summary_row.avg_ollama_latency_ms),
        "avg_total_latency_ms": _round_or_none(summary_row.avg_total_latency_ms),
        "p95_total_latency_ms": _round_or_none(summary_row.p95_total_latency_ms),
    }

    # Grouped data
    if group_by == "user":
        group_key_expr = "u.id::text AS group_key"
        group_label_expr = "CONCAT(COALESCE(u.first_name,''), ' ', COALESCE(u.last_name,'')) AS group_label"
        from_clause = 'voice_command_log vcl JOIN "user" u ON u.id = vcl.user_id'
        group_by_clause = "u.id, u.first_name, u.last_name"
    elif group_by == "day":
        group_key_expr = "vcl.created_at::date::text AS group_key"
        group_label_expr = "vcl.created_at::date::text AS group_label"
        from_clause = "voice_command_log vcl"
        group_by_clause = "vcl.created_at::date"
    else:  # intent (default)
        group_key_expr = "COALESCE(vcl.intent_detected, 'unknown') AS group_key"
        group_label_expr = "COALESCE(vcl.intent_detected, 'unknown') AS group_label"
        from_clause = "voice_command_log vcl"
        group_by_clause = "COALESCE(vcl.intent_detected, 'unknown')"

    data_sql = f"""
        SELECT
            {group_key_expr},
            {group_label_expr},
            COUNT(*) AS command_count,
            COUNT(*) FILTER (WHERE vcl.is_successful = true) AS success_count,
            AVG(vcl.total_latency_ms) FILTER (WHERE vcl.total_latency_ms IS NOT NULL) AS avg_total_latency_ms
        FROM {from_clause}
        WHERE vcl.tenant_id = :tenant_id
          AND vcl.created_at::date >= :date_from
          AND vcl.created_at::date <= :date_to
        GROUP BY {group_by_clause}
        ORDER BY command_count DESC
    """
    data_rows = db.exec(
        text(data_sql).bindparams(
            tenant_id=str(tenant_id),
            date_from=str(date_from),
            date_to=str(date_to),
        )
    ).fetchall()

    data = []
    for row in data_rows:
        cnt = int(row.command_count or 0)
        succ = int(row.success_count or 0)
        sr = round(succ / cnt * 100, 2) if cnt > 0 else None
        data.append(
            {
                "group_key": row.group_key,
                "group_label": row.group_label.strip()
                if group_by == "user"
                else row.group_label,
                "command_count": cnt,
                "success_count": succ,
                "success_rate_pct": sr,
                "avg_total_latency_ms": _round_or_none(row.avg_total_latency_ms),
            }
        )

    return {"summary": summary, "data": data}
