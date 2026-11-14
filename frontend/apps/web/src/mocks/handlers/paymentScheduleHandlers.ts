/**
 * MSW handlers — Payment Schedules — BILLING-B1 Part B
 *
 * Location: apps/web/src/mocks/handlers/paymentScheduleHandlers.ts
 *
 * Covers all 9 endpoints under /api/v1/payment-schedules:
 *   - GET    /api/v1/payment-schedules              (list, ?quote_id= / ?job_id=)
 *   - POST   /api/v1/payment-schedules              (create, Idempotency-Key)
 *   - GET    /api/v1/payment-schedules/:id          (detail)
 *   - PATCH  /api/v1/payment-schedules/:id          (update header, draft only)
 *   - POST   /api/v1/payment-schedules/:id/activate (422 on residual ≠ 0)
 *   - POST   /api/v1/payment-schedules/:id/lines    (add line, draft only)
 *   - PATCH  /api/v1/payment-schedules/:id/lines/:lineId  (update line, draft only)
 *   - DELETE /api/v1/payment-schedules/:id/lines/:lineId  (delete line, draft only)
 *   - POST   /api/v1/payment-schedules/:id/lines/:lineId/generate-invoice (409 if invoiced)
 *
 * Fixtures:
 *   - DRAFT_SCHEDULE: deposit (seq 1) + 2 draws, residual drivable to 0
 *   - ACTIVE_SCHEDULE: 1 invoiced + 1 pending draw
 *
 * Test resilience: fixture objects are NEVER mutated. POST/PATCH handlers
 * return merged copies. Per-test overrides via server.use() for 422/409.
 */

import { http, HttpResponse } from "msw";

// ── Types (local mock shapes — mirror the backend response) ───────────────────

interface MockLine {
  id: string;
  tenant_id: string;
  payment_schedule_id: string;
  sequence: number;
  label: string;
  basis: string;
  percent: string | null;
  amount_cents: number | null;
  trigger_type: string;
  trigger_date: string | null;
  milestone_label: string | null;
  invoice_id: string | null;
  status: string;
  is_active: boolean;
  resolved_amount_cents: number;
}

interface MockSchedule {
  id: string;
  tenant_id: string;
  quote_id: string | null;
  job_id: string | null;
  customer_id: string;
  site_id: string;
  contract_total_cents: number;
  status: string;
  basis_default: string;
  is_active: boolean;
  lines: MockLine[];
  scheduled_total_cents: number;
  residual_cents: number;
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

const TENANT_ID = "t-00000001-0000-0000-0000-000000000001";
const CUSTOMER_ID = "c-00000001-0000-0000-0000-000000000001";
const SITE_ID = "s-00000001-0000-0000-0000-000000000001";

// Draft schedule: deposit (30%) + 2 draws (40% + 30% = 70%) → residual = 0 (balanced)
// Contract total: $10,000 (1,000,000 cents)
const DRAFT_SCHEDULE: MockSchedule = {
  id: "ps-draft-000-0000-0000-0000-000000000001",
  tenant_id: TENANT_ID,
  quote_id: "q-00000001-0000-0000-0000-000000000001",
  job_id: null,
  customer_id: CUSTOMER_ID,
  site_id: SITE_ID,
  contract_total_cents: 1_000_000,
  status: "draft",
  basis_default: "percent",
  is_active: true,
  lines: [
    {
      id: "psl-draft-001-0000-0000-0000-000000000001",
      tenant_id: TENANT_ID,
      payment_schedule_id: "ps-draft-000-0000-0000-0000-000000000001",
      sequence: 1,
      label: "Deposit",
      basis: "percent",
      percent: "30.00",
      amount_cents: null,
      trigger_type: "manual",
      trigger_date: null,
      milestone_label: null,
      invoice_id: null,
      status: "pending",
      is_active: true,
      resolved_amount_cents: 300_000,
    },
    {
      id: "psl-draft-002-0000-0000-0000-000000000002",
      tenant_id: TENANT_ID,
      payment_schedule_id: "ps-draft-000-0000-0000-0000-000000000001",
      sequence: 2,
      label: "Rough-in",
      basis: "percent",
      percent: "40.00",
      amount_cents: null,
      trigger_type: "milestone",
      trigger_date: null,
      milestone_label: "Rough-in complete",
      invoice_id: null,
      status: "pending",
      is_active: true,
      resolved_amount_cents: 400_000,
    },
    {
      id: "psl-draft-003-0000-0000-0000-000000000003",
      tenant_id: TENANT_ID,
      payment_schedule_id: "ps-draft-000-0000-0000-0000-000000000001",
      sequence: 3,
      label: "Final",
      basis: "percent",
      percent: "30.00",
      amount_cents: null,
      trigger_type: "milestone",
      trigger_date: null,
      milestone_label: "Job complete",
      invoice_id: null,
      status: "pending",
      is_active: true,
      resolved_amount_cents: 300_000,
    },
  ],
  scheduled_total_cents: 1_000_000,
  residual_cents: 0,
};

// Active schedule: 1 invoiced + 1 pending draw
const ACTIVE_SCHEDULE: MockSchedule = {
  id: "ps-active-000-0000-0000-0000-000000000002",
  tenant_id: TENANT_ID,
  quote_id: null,
  job_id: "j-00000001-0000-0000-0000-000000000001",
  customer_id: CUSTOMER_ID,
  site_id: SITE_ID,
  contract_total_cents: 500_000,
  status: "active",
  basis_default: "percent",
  is_active: true,
  lines: [
    {
      id: "psl-active-001-0000-0000-0000-000000000001",
      tenant_id: TENANT_ID,
      payment_schedule_id: "ps-active-000-0000-0000-0000-000000000002",
      sequence: 1,
      label: "Deposit",
      basis: "percent",
      percent: "50.00",
      amount_cents: null,
      trigger_type: "manual",
      trigger_date: null,
      milestone_label: null,
      invoice_id: "inv-00000001-0000-0000-0000-000000000001",
      status: "invoiced",
      is_active: true,
      resolved_amount_cents: 250_000,
    },
    {
      id: "psl-active-002-0000-0000-0000-000000000002",
      tenant_id: TENANT_ID,
      payment_schedule_id: "ps-active-000-0000-0000-0000-000000000002",
      sequence: 2,
      label: "Final",
      basis: "percent",
      percent: "50.00",
      amount_cents: null,
      trigger_type: "milestone",
      trigger_date: null,
      milestone_label: "Job complete",
      invoice_id: null,
      status: "pending",
      is_active: true,
      resolved_amount_cents: 250_000,
    },
  ],
  scheduled_total_cents: 500_000,
  residual_cents: 0,
};

// In-memory store (copies — never mutate the fixtures above)
const SCHEDULES: Record<string, MockSchedule> = {
  [DRAFT_SCHEDULE.id]: { ...DRAFT_SCHEDULE },
  [ACTIVE_SCHEDULE.id]: { ...ACTIVE_SCHEDULE },
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function recomputeTotals(schedule: MockSchedule): MockSchedule {
  const scheduled = schedule.lines.reduce(
    (sum, l) => sum + (l.resolved_amount_cents ?? 0),
    0,
  );
  return {
    ...schedule,
    scheduled_total_cents: scheduled,
    residual_cents: schedule.contract_total_cents - scheduled,
  };
}

function toListItem(s: MockSchedule) {
  return {
    id: s.id,
    tenant_id: s.tenant_id,
    quote_id: s.quote_id,
    job_id: s.job_id,
    customer_id: s.customer_id,
    site_id: s.site_id,
    contract_total_cents: s.contract_total_cents,
    status: s.status,
    basis_default: s.basis_default,
    is_active: s.is_active,
    created_at: "2026-07-28T10:00:00Z",
    updated_at: "2026-07-28T10:00:00Z",
  };
}

// ── Handlers ──────────────────────────────────────────────────────────────────

export const paymentScheduleHandlers = [
  // GET /api/v1/payment-schedules — list (optional ?quote_id= / ?job_id=)
  http.get("/api/v1/payment-schedules", ({ request }) => {
    const url = new URL(request.url);
    const quoteId = url.searchParams.get("quote_id");
    const jobId = url.searchParams.get("job_id");

    const items = Object.values(SCHEDULES)
      .map(toListItem)
      .filter((s) => {
        if (quoteId && s.quote_id !== quoteId) return false;
        if (jobId && s.job_id !== jobId) return false;
        return true;
      });

    return HttpResponse.json({
      items,
      total: items.length,
      limit: 50,
      offset: 0,
    });
  }),

  // POST /api/v1/payment-schedules — create (Idempotency-Key)
  http.post("/api/v1/payment-schedules", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const newId = `ps-new-0000-0000-0000-0000000000${Date.now() % 100}`;
    const rawLines = (body.lines as Record<string, unknown>[]) ?? [];
    const lines: MockLine[] = rawLines.map((l, i) => ({
      id: `psl-new-0000-0000-0000-0000000000${i + 1}`,
      tenant_id: TENANT_ID,
      payment_schedule_id: newId,
      sequence: (l.sequence as number) ?? i + 1,
      label: (l.label as string) ?? "",
      basis: (l.basis as string) ?? "percent",
      percent: (l.percent as string) ?? null,
      amount_cents: (l.amount_cents as number) ?? null,
      trigger_type: (l.trigger_type as string) ?? "manual",
      trigger_date: (l.trigger_date as string) ?? null,
      milestone_label: (l.milestone_label as string) ?? null,
      invoice_id: null,
      status: "pending",
      is_active: true,
      resolved_amount_cents: 0,
    }));
    const newSchedule = recomputeTotals({
      id: newId,
      tenant_id: TENANT_ID,
      quote_id: (body.quote_id as string) ?? null,
      job_id: (body.job_id as string) ?? null,
      customer_id: body.customer_id as string,
      site_id: body.site_id as string,
      contract_total_cents: body.contract_total_cents as number,
      status: "draft",
      basis_default: (body.basis_default as string) ?? "percent",
      is_active: true,
      lines,
      scheduled_total_cents: 0,
      residual_cents: 0,
    });
    SCHEDULES[newId] = newSchedule;
    return HttpResponse.json(newSchedule, { status: 201 });
  }),

  // GET /api/v1/payment-schedules/:id — detail
  http.get("/api/v1/payment-schedules/:id", ({ params }) => {
    const { id } = params as { id: string };
    const schedule = SCHEDULES[id];
    if (!schedule) {
      return HttpResponse.json(
        { detail: "Payment schedule not found" },
        { status: 404 },
      );
    }
    return HttpResponse.json(schedule);
  }),

  // PATCH /api/v1/payment-schedules/:id — update header (draft only)
  http.patch("/api/v1/payment-schedules/:id", async ({ params, request }) => {
    const { id } = params as { id: string };
    const schedule = SCHEDULES[id];
    if (!schedule) {
      return HttpResponse.json(
        { detail: "Payment schedule not found" },
        { status: 404 },
      );
    }
    if (schedule.status !== "draft") {
      return HttpResponse.json(
        {
          detail: "Schedule is no longer draft — structural edits are locked.",
        },
        { status: 409 },
      );
    }
    const body = (await request.json()) as Partial<MockSchedule>;
    const updated = recomputeTotals({ ...schedule, ...body });
    SCHEDULES[id] = updated;
    return HttpResponse.json(updated);
  }),

  // POST /api/v1/payment-schedules/:id/activate (422 on residual ≠ 0)
  http.post("/api/v1/payment-schedules/:id/activate", ({ params }) => {
    const { id } = params as { id: string };
    const schedule = SCHEDULES[id];
    if (!schedule) {
      return HttpResponse.json(
        { detail: "Payment schedule not found" },
        { status: 404 },
      );
    }
    if (schedule.residual_cents !== 0) {
      return HttpResponse.json(
        {
          detail: `Draws must sum to the contract total before activating. ${Math.abs(schedule.residual_cents) / 100} ${schedule.residual_cents > 0 ? "under" : "over"}-allocated.`,
          type: "https://errors.pilotfortrades.com/residual-mismatch",
        },
        { status: 422 },
      );
    }
    const updated: MockSchedule = { ...schedule, status: "active" };
    SCHEDULES[id] = updated;
    return HttpResponse.json(updated);
  }),

  // POST /api/v1/payment-schedules/:id/lines — add line (draft only)
  http.post(
    "/api/v1/payment-schedules/:id/lines",
    async ({ params, request }) => {
      const { id } = params as { id: string };
      const schedule = SCHEDULES[id];
      if (!schedule) {
        return HttpResponse.json(
          { detail: "Payment schedule not found" },
          { status: 404 },
        );
      }
      if (schedule.status !== "draft") {
        return HttpResponse.json(
          {
            detail:
              "Schedule is no longer draft — structural edits are locked.",
          },
          { status: 409 },
        );
      }
      const body = (await request.json()) as Record<string, unknown>;
      const newLineId = `psl-add-0000-0000-0000-0000000000${Date.now() % 100}`;
      const newLine: MockLine = {
        id: newLineId,
        tenant_id: TENANT_ID,
        payment_schedule_id: id,
        sequence: (body.sequence as number) ?? schedule.lines.length + 1,
        label: (body.label as string) ?? "",
        basis: (body.basis as string) ?? "percent",
        percent: (body.percent as string) ?? null,
        amount_cents: (body.amount_cents as number) ?? null,
        trigger_type: (body.trigger_type as string) ?? "manual",
        trigger_date: (body.trigger_date as string) ?? null,
        milestone_label: (body.milestone_label as string) ?? null,
        invoice_id: null,
        status: "pending",
        is_active: true,
        resolved_amount_cents: 0,
      };
      const updated = recomputeTotals({
        ...schedule,
        lines: [...schedule.lines, newLine],
      });
      SCHEDULES[id] = updated;
      return HttpResponse.json(newLine, { status: 201 });
    },
  ),

  // PATCH /api/v1/payment-schedules/:id/lines/:lineId — update line (draft only)
  http.patch(
    "/api/v1/payment-schedules/:id/lines/:lineId",
    async ({ params, request }) => {
      const { id, lineId } = params as { id: string; lineId: string };
      const schedule = SCHEDULES[id];
      if (!schedule) {
        return HttpResponse.json(
          { detail: "Payment schedule not found" },
          { status: 404 },
        );
      }
      if (schedule.status !== "draft") {
        return HttpResponse.json(
          {
            detail:
              "Schedule is no longer draft — structural edits are locked.",
          },
          { status: 409 },
        );
      }
      const body = (await request.json()) as Partial<MockLine>;
      const updatedLines = schedule.lines.map((l) => {
        if (l.id !== lineId) return l;
        return { ...l, ...body };
      });
      const updated = recomputeTotals({ ...schedule, lines: updatedLines });
      SCHEDULES[id] = updated;
      const updatedLine = updatedLines.find((l) => l.id === lineId);
      return HttpResponse.json(updatedLine);
    },
  ),

  // DELETE /api/v1/payment-schedules/:id/lines/:lineId — delete line (draft only)
  http.delete("/api/v1/payment-schedules/:id/lines/:lineId", ({ params }) => {
    const { id, lineId } = params as { id: string; lineId: string };
    const schedule = SCHEDULES[id];
    if (!schedule) {
      return HttpResponse.json(
        { detail: "Payment schedule not found" },
        { status: 404 },
      );
    }
    if (schedule.status !== "draft") {
      return HttpResponse.json(
        {
          detail: "Schedule is no longer draft — structural edits are locked.",
        },
        { status: 409 },
      );
    }
    const updatedLines = schedule.lines.filter((l) => l.id !== lineId);
    const updated = recomputeTotals({ ...schedule, lines: updatedLines });
    SCHEDULES[id] = updated;
    return new HttpResponse(null, { status: 204 });
  }),

  // POST /api/v1/payment-schedules/:id/lines/:lineId/generate-invoice (409 if invoiced)
  http.post(
    "/api/v1/payment-schedules/:id/lines/:lineId/generate-invoice",
    ({ params }) => {
      const { id, lineId } = params as { id: string; lineId: string };
      const schedule = SCHEDULES[id];
      if (!schedule) {
        return HttpResponse.json(
          { detail: "Payment schedule not found" },
          { status: 404 },
        );
      }
      const line = schedule.lines.find((l) => l.id === lineId);
      if (!line) {
        return HttpResponse.json({ detail: "Draw not found" }, { status: 404 });
      }
      if (line.invoice_id) {
        return HttpResponse.json(
          {
            detail:
              "This draw already has an invoice. Void the existing invoice before re-generating.",
            type: "https://errors.pilotfortrades.com/already-invoiced",
          },
          { status: 409 },
        );
      }
      // Generate a mock invoice
      const newInvoiceId = `inv-gen-0000-0000-0000-0000000000${Date.now() % 100}`;
      const updatedLines = schedule.lines.map((l) =>
        l.id === lineId
          ? { ...l, invoice_id: newInvoiceId, status: "invoiced" }
          : l,
      );
      SCHEDULES[id] = { ...schedule, lines: updatedLines };
      return HttpResponse.json(
        {
          id: newInvoiceId,
          tenant_id: TENANT_ID,
          invoice_number: `INV-${Date.now()}`,
          customer_id: schedule.customer_id,
          site_id: schedule.site_id,
          status_code: "issued",
          total_cents: line.resolved_amount_cents,
          balance_due_cents: line.resolved_amount_cents,
        },
        { status: 201 },
      );
    },
  ),
];
