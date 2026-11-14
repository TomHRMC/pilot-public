/**
 * useCustomers unit tests — UI-FIX-1C update
 *
 * Location: apps/web/src/features/customers/hooks/__tests__/useCustomers.test.ts
 *
 * UI-FIX-1C: CUSTOMERS_QUERY_KEY now includes offset, limit, search, status (5 elements).
 */

import { CUSTOMERS_QUERY_KEY } from "../useCustomers";

describe("useCustomers — query key", () => {
  it("constructs correct query key with default params (no search, no status)", () => {
    const key = CUSTOMERS_QUERY_KEY(0, 25);
    expect(key).toEqual(["customers", 0, 25, "", ""]);
  });

  it("constructs correct query key with search param", () => {
    const key = CUSTOMERS_QUERY_KEY(0, 25, "alice");
    expect(key).toEqual(["customers", 0, 25, "alice", ""]);
  });

  it("constructs correct query key with search + status", () => {
    const key = CUSTOMERS_QUERY_KEY(0, 25, "alice", "active");
    expect(key).toEqual(["customers", 0, 25, "alice", "active"]);
  });

  it("query key differs by offset", () => {
    const k1 = CUSTOMERS_QUERY_KEY(0, 25);
    const k2 = CUSTOMERS_QUERY_KEY(25, 25);
    expect(k1).not.toEqual(k2);
  });

  it("query key differs by limit", () => {
    const k1 = CUSTOMERS_QUERY_KEY(0, 25);
    const k2 = CUSTOMERS_QUERY_KEY(0, 50);
    expect(k1).not.toEqual(k2);
  });

  it("query key differs by search", () => {
    const k1 = CUSTOMERS_QUERY_KEY(0, 25, "alice");
    const k2 = CUSTOMERS_QUERY_KEY(0, 25, "bob");
    expect(k1).not.toEqual(k2);
  });

  it("query key differs by status", () => {
    const k1 = CUSTOMERS_QUERY_KEY(0, 25, undefined, "active");
    const k2 = CUSTOMERS_QUERY_KEY(0, 25, undefined, "inactive");
    expect(k1).not.toEqual(k2);
  });

  it("query key is a tuple starting with 'customers'", () => {
    const key = CUSTOMERS_QUERY_KEY(0, 25);
    expect(key[0]).toBe("customers");
    expect(key[1]).toBe(0);
    expect(key[2]).toBe(25);
  });
});
