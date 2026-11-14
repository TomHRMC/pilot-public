/**
 * FE-B20 Integration — Catalog Markups
 *
 * Location: apps/web/src/__tests__/batch_fe_b20/catalogMarkups.integration.test.tsx
 *
 * Tests the /catalog/markups page (MarkupsPage) with MSW handlers.
 * Rule 15: never assert on toHaveLength(N), assert by content; no fixture mutation.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { setupServer } from "msw/node";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { http, HttpResponse } from "msw";
import { catalogHandlers } from "@/mocks/handlers/catalogHandlers";
import { MarkupsPage } from "@/features/catalog/components/MarkupsPage";

// Per-test MSW server — isolated from global handler set
const server = setupServer(...catalogHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

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

function Wrapper({
  role = "owner",
  children,
}: {
  role?: "owner" | "office_staff" | "technician" | "accountant";
  children: React.ReactNode;
}) {
  return (
    <AuthContext.Provider value={makeContext(role)}>
      <QueryClientProvider client={makeQueryClient()}>
        {children}
      </QueryClientProvider>
    </AuthContext.Provider>
  );
}

describe("Catalog — MarkupsPage integration", () => {
  it("renders markup table from MSW data", async () => {
    render(<MarkupsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("materials")).toBeInTheDocument();
    });
    expect(screen.getByText("equipment")).toBeInTheDocument();
    expect(screen.getByText("permits")).toBeInTheDocument();
  });

  it("Set Markup button is visible for owner", async () => {
    render(<MarkupsPage />, {
      wrapper: ({ children }) => <Wrapper role="owner">{children}</Wrapper>,
    });

    await waitFor(() => {
      expect(screen.getByText("materials")).toBeInTheDocument();
    });
    expect(
      screen.getByRole("button", { name: /set markup/i }),
    ).toBeInTheDocument();
  });

  it("clicking Set Markup opens SetMarkupModal", async () => {
    render(<MarkupsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("materials")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /set markup/i }));

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: /set markup/i }),
      ).toBeInTheDocument();
    });
  });

  it("submitting Set Markup form fires POST to /api/v1/settings/markups", async () => {
    let postCalled = false;
    let capturedBody: Record<string, unknown> | null = null;

    server.use(
      http.get("*/api/v1/job-expense-categories", () =>
        HttpResponse.json({
          categories: [
            { code: "materials", label: "Materials" },
            { code: "equipment", label: "Equipment" },
            { code: "permits", label: "Permits" },
          ],
        }),
      ),
      http.post("*/api/v1/settings/markups", async ({ request }) => {
        postCalled = true;
        capturedBody = (await request.json()) as Record<string, unknown>;
        return HttpResponse.json(
          {
            id: 99,
            tenant_id: "tenant-test-1",
            job_expense_category_code: "materials",
            markup_pct: 25,
            markup_amt_cents: null,
            valid_period_lower: new Date().toISOString(),
            valid_period_upper: null,
            recorded_at: new Date().toISOString(),
            created_by: null,
          },
          { status: 201 },
        );
      }),
    );

    render(<MarkupsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.getByText("materials")).toBeInTheDocument();
    });

    // Open modal
    fireEvent.click(screen.getByRole("button", { name: /set markup/i }));

    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    // Set markup % to 25
    fireEvent.change(screen.getByLabelText(/markup %/i), {
      target: { value: "25" },
    });

    // Submit
    fireEvent.click(screen.getAllByRole("button", { name: /set markup/i })[1]);

    await waitFor(() => {
      expect(postCalled).toBe(true);
    });

    expect(capturedBody).toMatchObject({
      job_expense_category_code: "materials",
      markup_pct: 25,
    });
  });

  it("shows error state when API fails", async () => {
    server.use(
      http.get("*/api/v1/settings/markups", () =>
        HttpResponse.json({ detail: "Server error" }, { status: 500 }),
      ),
    );

    render(<MarkupsPage />, { wrapper: Wrapper });

    await waitFor(() => {
      expect(screen.queryByText("materials")).toBeNull();
    });
  });
});
