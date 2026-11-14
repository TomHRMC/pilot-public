/**
 * useInvoices unit tests — BETA-B3
 *
 * Location: apps/web/src/features/invoices/hooks/__tests__/useInvoices.test.ts
 */

import { INVOICES_QUERY_KEY } from "../useInvoices";

describe("useInvoices — query key", () => {
  it("constructs correct query key with no options", () => {
    const key = INVOICES_QUERY_KEY({});
    expect(key).toEqual(["invoices", {}]);
  });

  it("query key includes status param when provided", () => {
    const key = INVOICES_QUERY_KEY({ status: "sent", limit: 50, offset: 0 });
    expect(key).toEqual(["invoices", { status: "sent", limit: 50, offset: 0 }]);
  });

  it("query key differs when status changes", () => {
    const k1 = INVOICES_QUERY_KEY({ status: "draft" });
    const k2 = INVOICES_QUERY_KEY({ status: "paid" });
    expect(k1).not.toEqual(k2);
  });

  it("query key differs when offset changes (pagination)", () => {
    const k1 = INVOICES_QUERY_KEY({ offset: 0 });
    const k2 = INVOICES_QUERY_KEY({ offset: 50 });
    expect(k1).not.toEqual(k2);
  });

  it("query key without status differs from query key with status", () => {
    const k1 = INVOICES_QUERY_KEY({});
    const k2 = INVOICES_QUERY_KEY({ status: "sent" });
    expect(k1).not.toEqual(k2);
  });

  // UI-FIX-2D: customer_id param
  it("query key includes customer_id when provided", () => {
    const key = INVOICES_QUERY_KEY({ customer_id: "cust-1" });
    expect(key[1]).toMatchObject({ customer_id: "cust-1" });
  });

  it("query key differs when customer_id changes", () => {
    const k1 = INVOICES_QUERY_KEY({ customer_id: "cust-1" });
    const k2 = INVOICES_QUERY_KEY({ customer_id: "cust-2" });
    expect(k1).not.toEqual(k2);
  });

  it("query key with customer_id differs from key without customer_id", () => {
    const k1 = INVOICES_QUERY_KEY({});
    const k2 = INVOICES_QUERY_KEY({ customer_id: "cust-1" });
    expect(k1).not.toEqual(k2);
  });
});
