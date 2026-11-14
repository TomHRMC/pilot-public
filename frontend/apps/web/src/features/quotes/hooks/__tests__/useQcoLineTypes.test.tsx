/**
 * useQcoLineTypes unit tests — PLP-FIX-2
 *
 * Location: apps/web/src/features/quotes/hooks/__tests__/useQcoLineTypes.test.ts
 *
 * Tests:
 * 1. useQcoLineTypes returns API-shaped data with correct query key
 * 2. resolveDefaultLineTypeId picks 'misc' first
 * 3. resolveDefaultLineTypeId falls back to is_default when no 'misc'
 * 4. resolveDefaultLineTypeId falls back to first row when no 'misc' and no is_default
 * 5. resolveDefaultLineTypeId returns null for empty array
 */

import { describe, it, expect, beforeAll, afterEach, afterAll } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import {
  useQcoLineTypes,
  resolveDefaultLineTypeId,
  QCO_LINE_TYPES_QUERY_KEY,
} from "../useQcoLineTypes";

// ── MSW ───────────────────────────────────────────────────────────────────────

const MOCK_TYPES = [
  {
    id: "id-discount",
    code: "discount",
    name: "Discount",
    is_default: false,
    is_active: true,
    is_tenant_override: false,
  },
  {
    id: "id-labor",
    code: "labor",
    name: "Labor",
    is_default: true,
    is_active: true,
    is_tenant_override: false,
  },
  {
    id: "id-material",
    code: "material",
    name: "Material",
    is_default: false,
    is_active: true,
    is_tenant_override: false,
  },
  {
    id: "id-misc",
    code: "misc",
    name: "Misc",
    is_default: false,
    is_active: true,
    is_tenant_override: false,
  },
  {
    id: "id-note",
    code: "note",
    name: "Note",
    is_default: false,
    is_active: true,
    is_tenant_override: false,
  },
];

const server = setupServer(
  http.get("/api/v1/qco-line-types", () => HttpResponse.json(MOCK_TYPES)),
);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ──────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return TestWrapper;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("useQcoLineTypes", () => {
  it("1. returns API-shaped data with correct query key", async () => {
    const { result } = renderHook(() => useQcoLineTypes(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual(MOCK_TYPES);
    // Query key is the colocated constant
    expect(QCO_LINE_TYPES_QUERY_KEY).toEqual(["qco-line-types"]);
  });
});

describe("resolveDefaultLineTypeId", () => {
  it("2. picks 'misc' first when present", () => {
    const types = [
      {
        id: "id-labor",
        code: "labor",
        name: "Labor",
        is_default: true,
        is_active: true,
        is_tenant_override: false,
      },
      {
        id: "id-misc",
        code: "misc",
        name: "Misc",
        is_default: false,
        is_active: true,
        is_tenant_override: false,
      },
    ];
    expect(resolveDefaultLineTypeId(types)).toBe("id-misc");
  });

  it("3. falls back to is_default when no 'misc'", () => {
    const types = [
      {
        id: "id-labor",
        code: "labor",
        name: "Labor",
        is_default: true,
        is_active: true,
        is_tenant_override: false,
      },
      {
        id: "id-material",
        code: "material",
        name: "Material",
        is_default: false,
        is_active: true,
        is_tenant_override: false,
      },
    ];
    expect(resolveDefaultLineTypeId(types)).toBe("id-labor");
  });

  it("4. falls back to first row when no 'misc' and no is_default", () => {
    const types = [
      {
        id: "id-discount",
        code: "discount",
        name: "Discount",
        is_default: false,
        is_active: true,
        is_tenant_override: false,
      },
      {
        id: "id-material",
        code: "material",
        name: "Material",
        is_default: false,
        is_active: true,
        is_tenant_override: false,
      },
    ];
    expect(resolveDefaultLineTypeId(types)).toBe("id-discount");
  });

  it("5. returns null for empty array", () => {
    expect(resolveDefaultLineTypeId([])).toBeNull();
  });
});
