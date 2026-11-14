"""
reports.py — B5/A5

Pydantic request/response schemas for reports domain and dashboard widget CRUD.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.reports import WidgetType

# ---------------------------------------------------------------------------
# Common report envelope
# ---------------------------------------------------------------------------


class ReportEnvelope(BaseModel):
    """Common wrapper present on all 6 report responses."""

    report_type: str
    date_from: date
    date_to: date
    display_mode: str  # 'chart' | 'table'
    row_count: int
    report_chart_threshold: int


# ---------------------------------------------------------------------------
# Profitability report
# ---------------------------------------------------------------------------


class ProfitabilityRow(BaseModel):
    group_key: str
    group_label: str
    # B19: customer_name populated when group_by=job; None for customer/site group modes
    customer_name: str | None = None
    job_count: int
    quoted_total_cents: int
    actual_labor_cost_cents: int
    actual_material_cost_cents: int
    actual_profit_cents: int
    margin_pct: float | None = None
    margin_bucket: str | None = None
    below_margin_target: bool


class ProfitabilityReportResponse(ReportEnvelope):
    report_type: str = "profitability"
    data: list[ProfitabilityRow]


# ---------------------------------------------------------------------------
# Revenue report
# ---------------------------------------------------------------------------


class RevenueRow(BaseModel):
    period_label: str
    period_start: date
    period_end: date
    invoiced_cents: int
    collected_cents: int
    outstanding_cents: int
    invoice_count: int
    payment_count: int


class RevenueReportResponse(ReportEnvelope):
    report_type: str = "revenue"
    data: list[RevenueRow]


# ---------------------------------------------------------------------------
# AR Aging report
# ---------------------------------------------------------------------------


class ARAgingCustomerRow(BaseModel):
    customer_id: UUID
    customer_name: str
    current_cents: int
    bucket_31_60_cents: int
    bucket_61_90_cents: int
    bucket_91_plus_cents: int
    total_outstanding_cents: int
    oldest_invoice_due_at: date | None = None


class ARAgingSummary(BaseModel):
    current_cents: int
    bucket_31_60_cents: int
    bucket_61_90_cents: int
    bucket_91_plus_cents: int
    total_outstanding_cents: int


class ARAgingReportResponse(BaseModel):
    report_type: str = "ar_aging"
    as_of_date: date
    display_mode: str
    row_count: int
    report_chart_threshold: int
    summary: ARAgingSummary
    data: list[ARAgingCustomerRow]


# ---------------------------------------------------------------------------
# Tech productivity report
# ---------------------------------------------------------------------------


class TechProductivityRow(BaseModel):
    user_id: UUID
    user_full_name: str
    jobs_worked: int
    jobs_completed: int
    total_hours_logged: float
    avg_hours_per_job: float | None = None
    total_labor_cost_cents: int


class TechProductivityReportResponse(ReportEnvelope):
    report_type: str = "tech_productivity"
    data: list[TechProductivityRow]


# ---------------------------------------------------------------------------
# Tax liability report
# ---------------------------------------------------------------------------


class TaxLiabilityRow(BaseModel):
    period_label: str
    period_start: date
    period_end: date
    invoice_count: int
    total_invoiced_cents: int
    total_tax_cents: int
    effective_tax_rate_pct: float | None = None


class TaxLiabilityReportResponse(ReportEnvelope):
    report_type: str = "tax_liability"
    data: list[TaxLiabilityRow]


# ---------------------------------------------------------------------------
# Voice analytics report
# ---------------------------------------------------------------------------


class VoiceAnalyticsRow(BaseModel):
    group_key: str
    group_label: str
    command_count: int
    success_count: int
    success_rate_pct: float | None = None
    avg_total_latency_ms: float | None = None


class VoiceAnalyticsSummary(BaseModel):
    total_commands: int
    successful_commands: int
    success_rate_pct: float | None = None
    avg_whisper_latency_ms: float | None = None
    avg_ollama_latency_ms: float | None = None
    avg_total_latency_ms: float | None = None
    p95_total_latency_ms: float | None = None


class VoiceAnalyticsReportResponse(BaseModel):
    report_type: str = "voice_analytics"
    date_from: date
    date_to: date
    display_mode: str
    row_count: int
    report_chart_threshold: int
    summary: VoiceAnalyticsSummary
    data: list[VoiceAnalyticsRow]


# ---------------------------------------------------------------------------
# WIP (Work-In-Progress) report — UP-1
# ---------------------------------------------------------------------------


class WipSummary(BaseModel):
    """Aggregate metrics across all active jobs in the WIP report."""

    active_job_count: int
    total_actual_cost_cents: int
    total_quoted_budget_cents: int
    total_projected_cost_cents: int
    jobs_over_budget_count: int
    jobs_below_margin_target_count: int


class WipReportRow(BaseModel):
    """Per-active-job WIP row: actuals + ETC-projected cost vs quoted budget."""

    job_id: str
    job_number: str
    title: str | None = None
    customer_name: str | None = None
    site_name: str | None = None
    status_code: str
    scheduled_start_at: datetime | None = None
    quoted_budget_cents: int | None = None
    actual_cost_cents: int
    etc_hours_remaining: float | None = None
    etc_cost_cents: int
    projected_cost_cents: int
    projected_margin_pct: float | None = None
    budget_deviation_pct: float | None = None
    has_etc: bool
    below_margin_target: bool


class WipReportResponse(BaseModel):
    """WIP report response — no date range (WIP is "now"); does not extend ReportEnvelope."""

    report_type: str = "wip"
    generated_at: datetime
    margin_target_pct: float
    row_count: int
    summary: WipSummary
    rows: list[WipReportRow]


# ---------------------------------------------------------------------------
# Dashboard widget CRUD schemas
# ---------------------------------------------------------------------------


class UserDashboardWidgetCreate(BaseModel):
    widget_type: WidgetType
    widget_config_json: dict[str, Any] = Field(default_factory=dict)
    position_x: int = Field(default=0, ge=0)
    position_y: int = Field(default=0, ge=0)
    width: int = Field(default=2, ge=1, le=12)
    height: int = Field(default=2, ge=1, le=8)


class UserDashboardWidgetUpdate(BaseModel):
    """All fields optional — PATCH semantics."""

    widget_config_json: dict[str, Any] | None = None
    position_x: int | None = Field(default=None, ge=0)
    position_y: int | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, ge=1, le=12)
    height: int | None = Field(default=None, ge=1, le=8)


class UserDashboardWidgetResponse(BaseModel):
    id: UUID
    user_id: UUID
    tenant_id: UUID
    widget_type: str
    widget_config_json: dict[str, Any]
    position_x: int
    position_y: int
    width: int
    height: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
