/**
 * FE-B26 — DrillDownPanel Job # + Customer Columns Integration Tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b26/drilldown_panel_columns.integration.test.tsx
 *
 * Tests:
 * 1. Column header "Job #" is present
 * 2. Column header "Customer" is present
 * 3. Renders job_number value in Job # column
 * 4. Renders customer_name value in Customer column
 * 5. Renders "—" when customer_name is null
 */

import { render, screen } from "@testing-library/react";
import React from "react";
import { describe, it, expect } from "vitest";
import { DrillDownPanel } from "@/features/profitability/components/DrillDownPanel";
import type { ClosedJob } from "@/features/profitability/hooks/useProfitability";

const mockJobs: ClosedJob[] = [
  {
    id: "job-prof-001",
    title: "JOB-000001",
    job_number: "JOB-000001",
    customer_name: "Acme Electric",
    close_date: "2026-07-01",
    revenue_cents: 135000,
    margin_pct: 42,
    margin_bucket: "high",
  },
  {
    id: "job-prof-002",
    title: "JOB-000002",
    job_number: "JOB-000002",
    customer_name: null,
    close_date: "2026-06-28",
    revenue_cents: 28000,
    margin_pct: 18,
    margin_bucket: "low",
  },
  {
    id: "job-prof-003",
    title: "JOB-000003",
    job_number: null,
    customer_name: "Martinez Properties",
    close_date: "2026-06-15",
    revenue_cents: 95000,
    margin_pct: 31,
    margin_bucket: "medium",
  },
];

function renderPanel(bucket: string, jobs: ClosedJob[] = mockJobs) {
  return render(
    <DrillDownPanel bucket={bucket} jobs={jobs} onClose={() => {}} />,
  );
}

describe("FE-B26 DrillDownPanel Job # + Customer Columns", () => {
  it("1. Column header 'Job #' is present", () => {
    renderPanel("high");
    expect(screen.getByText("Job #")).toBeInTheDocument();
  });

  it("2. Column header 'Customer' is present", () => {
    renderPanel("high");
    expect(screen.getByText("Customer")).toBeInTheDocument();
  });

  it("3. Column header 'Job' (old name) is NOT present", () => {
    renderPanel("high");
    // Exact text "Job" should NOT be a column header anymore
    const headers = screen.getAllByRole("columnheader");
    const jobHeader = headers.find((h) => h.textContent === "Job");
    expect(jobHeader).toBeUndefined();
  });

  it("4. Renders job_number value in Job # column", () => {
    renderPanel("high");
    expect(screen.getByText("JOB-000001")).toBeInTheDocument();
  });

  it("5. Renders customer_name value in Customer column", () => {
    renderPanel("high");
    expect(screen.getByText("Acme Electric")).toBeInTheDocument();
  });

  it("6. Renders '—' when customer_name is null", () => {
    renderPanel("low");
    // job-prof-002 has customer_name: null
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("7. Renders title as fallback when job_number is null", () => {
    renderPanel("medium");
    // job-prof-003 has job_number: null, title: "JOB-000003"
    expect(screen.getByText("JOB-000003")).toBeInTheDocument();
  });

  it("8. Renders customer_name in Customer column when job_number is null", () => {
    renderPanel("medium");
    // job-prof-003 has customer_name: "Martinez Properties"
    expect(screen.getByText("Martinez Properties")).toBeInTheDocument();
  });
});
