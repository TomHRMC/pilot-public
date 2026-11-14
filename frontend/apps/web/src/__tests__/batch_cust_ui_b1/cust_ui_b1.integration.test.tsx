/**
 * CUST-UI-B1 — Customer Type Confirmation + Site Type on Sites
 *
 * Location: apps/web/src/__tests__/batch_cust_ui_b1/cust_ui_b1.integration.test.tsx
 *
 * Test coverage:
 *  1. SiteForm dropdown — renders all 3 options
 *  2. SiteForm dropdown — company customer defaults to Commercial
 *  3. SiteForm dropdown — person customer defaults to Residential
 *  4. SiteForm dropdown — selecting a value + submit includes site_type in payload
 *  5. SiteForm edit — pre-fills site_type from initialValues
 *  6. SiteListPanel card — shows site_type chip for commercial site
 *  7. SiteListPanel card — omits chip when site_type is null
 *  8. SiteListPanel default wiring — company customer sees Commercial pre-selected
 *  9. CustomerOverviewTab — renders Type chip (company)
 * 10. CustomerOverviewTab — renders Type chip (person)
 */

import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

// CustomerOverviewTab uses useRouter for post-delete navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn(), replace: vi.fn() }),
  usePathname: () => "/customers/test",
  useSearchParams: () => new URLSearchParams(),
}));

import { SiteForm } from "../../features/customers/components/SiteForm";
import { SiteListPanel } from "../../features/customers/components/SiteListPanel";
import { CustomerOverviewTab } from "../../features/customers/components/CustomerOverviewTab";
import {
  MOCK_CUSTOMERS,
  MOCK_SITES,
} from "../../mocks/handlers/customerHandlers";

// ── MSW server ─────────────────────────────────────────────────────────────────

const COMPANY_CUSTOMER_ID = "c-00000001-0000-0000-0000-000000000001";
const PERSON_CUSTOMER_ID = "c-00000004-0000-0000-0000-000000000004";

const server = setupServer(
  // GET /api/v1/customers/:id
  http.get("/api/v1/customers/:customerId", ({ params }) => {
    const { customerId } = params as { customerId: string };
    const customer = MOCK_CUSTOMERS.find((c) => c.id === customerId);
    if (!customer) {
      return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    }
    return HttpResponse.json(customer);
  }),

  // GET /api/v1/sites/
  http.get("/api/v1/sites/", ({ request }) => {
    const url = new URL(request.url);
    const customerId = url.searchParams.get("customer_id");
    const filtered = customerId
      ? MOCK_SITES.filter((s) => s.customer_id === customerId)
      : MOCK_SITES;
    return HttpResponse.json(filtered);
  }),

  // POST /api/v1/sites/
  http.post("/api/v1/sites/", async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    return HttpResponse.json(
      {
        id: "site-new-test",
        tenant_id: "t-001",
        customer_id: body.customer_id ?? "",
        name: body.name ?? null,
        notes: body.notes ?? null,
        jurisdiction_code: body.jurisdiction_code ?? null,
        is_active: true,
        site_type: body.site_type ?? null,
        address: null,
      },
      { status: 201 },
    );
  }),

  // PATCH /api/v1/sites/:siteId
  http.patch("/api/v1/sites/:siteId", async ({ params, request }) => {
    const { siteId } = params as { siteId: string };
    const body = (await request.json()) as Record<string, unknown>;
    const existing = MOCK_SITES.find((s) => s.id === siteId);
    if (!existing) {
      return HttpResponse.json({ detail: "Not found" }, { status: 404 });
    }
    return HttpResponse.json({ ...existing, ...body });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Helpers ────────────────────────────────────────────────────────────────────

function makeContext(
  role: "owner" | "office_staff" | "technician" | "accountant" = "owner",
): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "a@b.com",
      role,
      tenantId: "t1",
      displayName: "Test",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role,
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <AuthContext.Provider value={makeContext("owner")}>
      <QueryClientProvider client={makeQueryClient()}>
        {children}
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

// ── Test 1–5: SiteForm unit tests (no network needed) ─────────────────────────

describe("CUST-UI-B1 — SiteForm site_type dropdown", () => {
  const noop = vi.fn();

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("1. renders Commercial, Residential, and Industrial options", () => {
    render(
      <SiteForm
        customerId="c-001"
        onSubmit={noop}
        onCancel={noop}
        isSubmitting={false}
      />,
    );
    const select = screen.getByTestId("site-type-select") as HTMLSelectElement;
    const options = Array.from(select.options).map((o) => o.value);
    expect(options).toContain("commercial");
    expect(options).toContain("residential");
    expect(options).toContain("industrial");
  });

  it("2. defaults to Commercial for company customer", () => {
    render(
      <SiteForm
        customerId="c-001"
        customerType="company"
        onSubmit={noop}
        onCancel={noop}
        isSubmitting={false}
      />,
    );
    const select = screen.getByTestId("site-type-select") as HTMLSelectElement;
    expect(select.value).toBe("commercial");
  });

  it("3. defaults to Residential for person customer", () => {
    render(
      <SiteForm
        customerId="c-001"
        customerType="person"
        onSubmit={noop}
        onCancel={noop}
        isSubmitting={false}
      />,
    );
    const select = screen.getByTestId("site-type-select") as HTMLSelectElement;
    expect(select.value).toBe("residential");
  });

  it("4. selecting Industrial + submit includes site_type='industrial' in payload", async () => {
    const onSubmit = vi.fn();
    render(
      <SiteForm
        customerId="c-001"
        customerType="company"
        onSubmit={onSubmit}
        onCancel={noop}
        isSubmitting={false}
      />,
    );

    // Fill required name field
    const nameInput = screen.getByRole("textbox", { name: /site name/i });
    fireEvent.change(nameInput, { target: { value: "Test Site" } });

    // Change site_type to industrial
    const select = screen.getByTestId("site-type-select");
    fireEvent.change(select, { target: { value: "industrial" } });

    // Submit
    fireEvent.click(screen.getByTestId("site-form-submit"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledOnce();
      const payload = onSubmit.mock.calls[0][0] as Record<string, unknown>;
      expect(payload.site_type).toBe("industrial");
    });
  });

  it("5. pre-fills site_type='residential' from initialValues (edit mode — overrides company default)", () => {
    render(
      <SiteForm
        customerId="c-001"
        customerType="company"
        initialValues={{ name: "HQ", site_type: "residential" }}
        onSubmit={noop}
        onCancel={noop}
        isSubmitting={false}
      />,
    );
    const select = screen.getByTestId("site-type-select") as HTMLSelectElement;
    // initialValues.site_type takes precedence over customerType default
    expect(select.value).toBe("residential");
  });
});

// ── Test 6–8: SiteListPanel integration ────────────────────────────────────────

describe("CUST-UI-B1 — SiteListPanel site_type chip (integration)", () => {
  it("6. shows site_type chip for commercial site (fixture site-001)", async () => {
    render(
      <Wrapper>
        <SiteListPanel customerId={COMPANY_CUSTOMER_ID} />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(
        screen.getByTestId(
          "site-type-chip-site-00000001-0000-0000-0000-000000000001",
        ),
      ).toBeTruthy();
    });

    const chip = screen.getByTestId(
      "site-type-chip-site-00000001-0000-0000-0000-000000000001",
    );
    expect(chip.textContent).toBe("commercial");
  });

  it("7. omits site_type chip when site_type is null", async () => {
    server.use(
      http.get("/api/v1/sites/", () => {
        return HttpResponse.json([
          {
            id: "site-null-type",
            tenant_id: "t-001",
            customer_id: COMPANY_CUSTOMER_ID,
            name: "No Type Site",
            notes: null,
            jurisdiction_code: null,
            is_active: true,
            site_type: null,
            address: null,
          },
        ]);
      }),
    );

    render(
      <Wrapper>
        <SiteListPanel customerId={COMPANY_CUSTOMER_ID} />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText("No Type Site")).toBeTruthy();
    });

    expect(screen.queryByTestId("site-type-chip-site-null-type")).toBeNull();
  });

  it("8. Add Site for company customer defaults to Commercial (integration — customer fetched via useCustomer)", async () => {
    render(
      <Wrapper>
        <SiteListPanel customerId={COMPANY_CUSTOMER_ID} />
      </Wrapper>,
    );

    // Wait for the Add Site button (owner role)
    await waitFor(() => {
      expect(screen.getByTestId("add-site-btn")).toBeTruthy();
    });

    fireEvent.click(screen.getByTestId("add-site-btn"));

    // Modal opens — check the site_type select defaults to commercial
    await waitFor(() => {
      const select = screen.getByTestId(
        "site-type-select",
      ) as HTMLSelectElement;
      expect(select.value).toBe("commercial");
    });
  });
});

// ── Test 9–10: CustomerOverviewTab Type chip ───────────────────────────────────

describe("CUST-UI-B1 — CustomerOverviewTab Type chip (verification)", () => {
  it("9. renders Type chip 'company' for a company customer", async () => {
    render(
      <Wrapper>
        <CustomerOverviewTab customerId={COMPANY_CUSTOMER_ID} />
      </Wrapper>,
    );

    await waitFor(() => {
      // The chip is inside a <span> with className containing "capitalize"
      // it renders the type value directly
      expect(screen.getByText("company")).toBeTruthy();
    });
  });

  it("10. renders Type chip 'person' for a person customer", async () => {
    render(
      <Wrapper>
        <CustomerOverviewTab customerId={PERSON_CUSTOMER_ID} />
      </Wrapper>,
    );

    await waitFor(() => {
      expect(screen.getByText("person")).toBeTruthy();
    });
  });
});
