/**
 * useQuotes unit tests — UI-FIX-1C update
 *
 * Location: apps/web/src/features/quotes/hooks/__tests__/useQuotes.test.ts
 *
 * UI-FIX-1C: QUOTES_QUERY_KEY is now object-based (includes all filter params).
 */

import { QUOTES_QUERY_KEY } from "../useQuotes";

describe("useQuotes — query key", () => {
  it("constructs correct query key with default params (no filters)", () => {
    const key = QUOTES_QUERY_KEY({ offset: 0, limit: 25 });
    expect(key[0]).toBe("quotes");
    expect(key[1]).toMatchObject({ offset: 0, limit: 25 });
  });

  it("query key differs when offset changes", () => {
    const k1 = QUOTES_QUERY_KEY({ offset: 0, limit: 25 });
    const k2 = QUOTES_QUERY_KEY({ offset: 25, limit: 25 });
    expect(k1).not.toEqual(k2);
  });

  it("query key differs when limit changes", () => {
    const k1 = QUOTES_QUERY_KEY({ offset: 0, limit: 25 });
    const k2 = QUOTES_QUERY_KEY({ offset: 0, limit: 50 });
    expect(k1).not.toEqual(k2);
  });

  it("query key includes status when provided", () => {
    const key = QUOTES_QUERY_KEY({ offset: 0, limit: 25, status: "draft" });
    expect(key[1]).toMatchObject({ status: "draft" });
  });

  it("query key differs when status changes", () => {
    const k1 = QUOTES_QUERY_KEY({ offset: 0, limit: 25, status: "draft" });
    const k2 = QUOTES_QUERY_KEY({ offset: 0, limit: 25, status: "sent" });
    expect(k1).not.toEqual(k2);
  });

  it("query key includes customer_search when provided", () => {
    const key = QUOTES_QUERY_KEY({
      offset: 0,
      limit: 25,
      customer_search: "Smith",
    });
    expect(key[1]).toMatchObject({ customer_search: "Smith" });
  });

  it("query key includes title_search when provided", () => {
    const key = QUOTES_QUERY_KEY({
      offset: 0,
      limit: 25,
      title_search: "Panel",
    });
    expect(key[1]).toMatchObject({ title_search: "Panel" });
  });

  it("query key is a tuple starting with 'quotes'", () => {
    const key = QUOTES_QUERY_KEY({ offset: 0, limit: 25 });
    expect(key[0]).toBe("quotes");
  });

  // UI-FIX-2D: customer_id param
  it("query key includes customer_id when provided", () => {
    const key = QUOTES_QUERY_KEY({
      offset: 0,
      limit: 25,
      customer_id: "cust-1",
    });
    expect(key[1]).toMatchObject({ customer_id: "cust-1" });
  });

  it("query key differs when customer_id changes", () => {
    const k1 = QUOTES_QUERY_KEY({
      offset: 0,
      limit: 25,
      customer_id: "cust-1",
    });
    const k2 = QUOTES_QUERY_KEY({
      offset: 0,
      limit: 25,
      customer_id: "cust-2",
    });
    expect(k1).not.toEqual(k2);
  });

  it("query key with customer_id differs from key without customer_id", () => {
    const k1 = QUOTES_QUERY_KEY({ offset: 0, limit: 25 });
    const k2 = QUOTES_QUERY_KEY({
      offset: 0,
      limit: 25,
      customer_id: "cust-1",
    });
    expect(k1).not.toEqual(k2);
  });
});
