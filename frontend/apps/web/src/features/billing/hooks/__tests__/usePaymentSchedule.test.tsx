/**
 * Payment Schedule hooks unit tests
 *
 * Location: apps/web/src/features/billing/hooks/__tests__/usePaymentSchedule.test.tsx
 *
 * BILLING-B1 Part B — covers:
 *   - usePaymentSchedule: query shape + query-key factory
 *   - useCreatePaymentSchedule: Idempotency-Key header
 *   - useGenerateDrawInvoice: Idempotency-Key header + 409 handling
 *
 * Rule 14: fresh QueryClient per test with retry: false.
 * Rule 15: MSW at the HTTP level — never mock apiClient directly.
 */

import {
  describe,
  it,
  expect,
  beforeAll,
  afterEach,
  afterAll,
  vi,
} from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import type { ReactNode } from "react";
import { usePaymentSchedule, paymentScheduleKeys } from "../usePaymentSchedule";
import { useCreatePaymentSchedule } from "../useCreatePaymentSchedule";
import { useGenerateDrawInvoice } from "../useGenerateDrawInvoice";

// ── MSW server ────────────────────────────────────────────────────────────────

const DRAFT_ID = "ps-draft-000-0000-0000-0000-000000000001";

const server = setupServer(
  // GET detail
  http.get(`/api/v1/payment-schedules/${DRAFT_ID}`, () => {
    return HttpResponse.json({
      id: DRAFT_ID,
      tenant_id: "t-001",
      quote_id: "q-001",
      job_id: null,
      customer_id: "c-001",
      site_id: "s-001",
      contract_total_cents: 1_000_000,
      status: "draft",
      basis_default: "percent",
      is_active: true,
      lines: [],
      scheduled_total_cents: 0,
      residual_cents: 1_000_000,
    });
  }),

  // GET detail — 404
  http.get("/api/v1/payment-schedules/not-found", () => {
    return HttpResponse.json({ detail: "Not found" }, { status: 404 });
  }),

  // POST create — capture Idempotency-Key
  http.post("/api/v1/payment-schedules", async ({ request }) => {
    const idempotencyKey = request.headers.get("Idempotency-Key");
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: "ps-new-001",
        tenant_id: "t-001",
        quote_id: body.quote_id ?? null,
        job_id: body.job_id ?? null,
        customer_id: body.customer_id,
        site_id: body.site_id,
        contract_total_cents: body.contract_total_cents,
        status: "draft",
        basis_default: body.basis_default ?? "percent",
        is_active: true,
        lines: [],
        scheduled_total_cents: 0,
        residual_cents: body.contract_total_cents as number,
        _idempotencyKey: idempotencyKey,
      },
      { status: 201 },
    );
  }),

  // POST generate-invoice — capture Idempotency-Key
  http.post(
    "/api/v1/payment-schedules/:id/lines/:lineId/generate-invoice",
    async ({ request, params }) => {
      const idempotencyKey = request.headers.get("Idempotency-Key");
      const { lineId } = params as { lineId: string };
      // If lineId is "already-invoiced", return 409
      if (lineId === "already-invoiced") {
        return HttpResponse.json(
          { detail: "This draw already has an invoice." },
          { status: 409 },
        );
      }
      return HttpResponse.json(
        {
          id: "inv-gen-001",
          tenant_id: "t-001",
          invoice_number: "INV-001",
          customer_id: "c-001",
          site_id: "s-001",
          status_code: "issued",
          total_cents: 300_000,
          balance_due_cents: 300_000,
          _idempotencyKey: idempotencyKey,
        },
        { status: 201 },
      );
    },
  ),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Wrapper ───────────────────────────────────────────────────────────────────

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("paymentScheduleKeys", () => {
  it("detail key includes the id", () => {
    expect(paymentScheduleKeys.detail("abc")).toEqual([
      "payment-schedules",
      "detail",
      "abc",
    ]);
  });

  it("list key includes the params", () => {
    expect(
      paymentScheduleKeys.list({ quote_id: "q1", job_id: undefined }),
    ).toEqual([
      "payment-schedules",
      "list",
      { quote_id: "q1", job_id: undefined },
    ]);
  });
});

describe("usePaymentSchedule", () => {
  it("returns the schedule data in the expected shape", async () => {
    const { result } = renderHook(() => usePaymentSchedule(DRAFT_ID), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe(DRAFT_ID);
    expect(result.current.data?.status).toBe("draft");
    expect(result.current.data?.contract_total_cents).toBe(1_000_000);
    expect(result.current.data?.residual_cents).toBe(1_000_000);
  });

  it("surfaces error state on 404", async () => {
    const { result } = renderHook(() => usePaymentSchedule("not-found"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});

describe("useCreatePaymentSchedule", () => {
  it("sends an Idempotency-Key header on POST", async () => {
    const { result } = renderHook(() => useCreatePaymentSchedule(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({
        customer_id: "c-001",
        site_id: "s-001",
        contract_total_cents: 500_000,
        basis_default: "percent",
        lines: [],
      });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe("ps-new-001");
    // The mock echoes back the Idempotency-Key it received
    expect(
      (result.current.data as unknown as { _idempotencyKey: string })
        ._idempotencyKey,
    ).toBeTruthy();
  });
});

describe("useGenerateDrawInvoice", () => {
  it("sends an Idempotency-Key header and returns the invoice", async () => {
    const onSuccess = vi.fn();
    const { result } = renderHook(() => useGenerateDrawInvoice({ onSuccess }), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      result.current.mutate({ scheduleId: DRAFT_ID, lineId: "psl-001" });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.id).toBe("inv-gen-001");
    expect(
      (result.current.data as unknown as { _idempotencyKey: string })
        ._idempotencyKey,
    ).toMatch(/^draw-gen-/);
    expect(onSuccess).toHaveBeenCalledWith(
      expect.objectContaining({ id: "inv-gen-001" }),
    );
  });

  it("calls onAlreadyInvoiced on 409", async () => {
    const onAlreadyInvoiced = vi.fn();
    const { result } = renderHook(
      () => useGenerateDrawInvoice({ onAlreadyInvoiced }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      result.current.mutate({
        scheduleId: DRAFT_ID,
        lineId: "already-invoiced",
      });
    });

    await waitFor(() => expect(onAlreadyInvoiced).toHaveBeenCalled());
    expect(onAlreadyInvoiced).toHaveBeenCalledWith(
      expect.stringContaining("already has an invoice"),
    );
  });
});
