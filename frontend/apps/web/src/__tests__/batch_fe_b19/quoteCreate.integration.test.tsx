/**
 * quoteCreate integration test — FE-B19
 *
 * Location: apps/web/src/__tests__/batch_fe_b19/quoteCreate.integration.test.tsx
 *
 * Platform: Web (Vitest + @testing-library/react + MSW node)
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
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import {
  quoteBuilderHandlers,
  MOCK_QUOTE_RESPONSE,
} from "@/mocks/handlers/quoteBuilderHandlers";
import { customerHandlers } from "@/mocks/handlers/customerHandlers";
import { quotesListHandlers } from "@/mocks/handlers/quotesListHandlers";
import { QuoteCreatePage } from "@/features/quotes/components/QuoteCreatePage";
import { QuotesPage } from "@/features/quotes/components/QuotesPage";

// Per-test MSW server — isolated from global handler set
const server = setupServer(
  ...quoteBuilderHandlers,
  ...customerHandlers,
  ...quotesListHandlers,
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// --- Auth context helper ---
function makeContext(
  role: "owner" | "office_staff" | "technician" | "accountant",
): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "owner@pilot.example.com",
      role,
      tenantId: "t1",
      displayName: "Test Owner",
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

// --- Mock Next.js navigation ---
const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  usePathname: () => "/quotes/new",
  useRouter: () => ({ push: mockPush }),
}));

vi.stubGlobal("crypto", { randomUUID: () => "test-idem-key-b19" });

afterEach(() => {
  mockPush.mockClear();
});

describe("FE-B19 — Quote Create Integration", () => {
  it("renders /quotes/new without crashing", () => {
    render(
      <Wrapper role="owner">
        <QuoteCreatePage />
      </Wrapper>,
    );
    // Use heading role to avoid matching breadcrumb "New Quote" text as well
    expect(
      screen.getByRole("heading", { name: /new quote/i }),
    ).toBeInTheDocument();
  });

  it("shows Customer and Site labels", () => {
    render(
      <Wrapper role="owner">
        <QuoteCreatePage />
      </Wrapper>,
    );
    expect(screen.getByLabelText(/Customer/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Site/i)).toBeInTheDocument();
  });

  it("New Quote button is visible for owner role in QuotesPage", async () => {
    render(
      <Wrapper role="owner">
        <QuotesPage />
      </Wrapper>,
    );
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /\+ new quote/i }),
      ).toBeInTheDocument();
    });
  });

  it("New Quote button is hidden for tech role in QuotesPage", async () => {
    render(
      <Wrapper role="technician">
        <QuotesPage />
      </Wrapper>,
    );
    // Tech has no quotes.view — QuotesPage returns null for tech
    await waitFor(() => {
      expect(
        screen.queryByRole("button", { name: /\+ new quote/i }),
      ).toBeNull();
    });
  });

  it("customer picker loads customers from MSW", async () => {
    render(
      <Wrapper role="owner">
        <QuoteCreatePage />
      </Wrapper>,
    );
    const searchInput = screen.getByPlaceholderText(/search customer/i);
    fireEvent.change(searchInput, { target: { value: "Smith" } });
    await waitFor(() => {
      expect(screen.getByText(/Smith Electrical/i)).toBeInTheDocument();
    });
  });

  it("adding a line item row shows description input in table", async () => {
    render(
      <Wrapper role="owner">
        <QuoteCreatePage />
      </Wrapper>,
    );
    // PLP-FIX-2: Add Line Item is disabled until line types load from the API
    const addBtn = await screen.findByText(/\+ Add Line Item/i);
    fireEvent.click(addBtn);
    expect(
      screen.getByRole("textbox", { name: /description/i }),
    ).toBeInTheDocument();
  });

  it("Save Draft is disabled when customer not selected", () => {
    render(
      <Wrapper role="owner">
        <QuoteCreatePage />
      </Wrapper>,
    );
    expect(screen.getByRole("button", { name: /save draft/i })).toBeDisabled();
  });

  it("Save Draft mutation fires POST /api/v1/quotes/ with correct payload", async () => {
    let capturedBody: unknown = null;
    server.use(
      http.post("/api/v1/quotes/", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json(
          { ...MOCK_QUOTE_RESPONSE, id: "q-saved-draft-001" },
          { status: 201 },
        );
      }),
    );

    render(
      <Wrapper role="owner">
        <QuoteCreatePage />
      </Wrapper>,
    );

    // Type in customer search
    const searchInput = screen.getByPlaceholderText(/search customer/i);
    fireEvent.change(searchInput, { target: { value: "Smith" } });
    await waitFor(() => screen.getByText(/Smith Electrical/i));
    fireEvent.click(screen.getByText(/Smith Electrical/i));

    // Wait for sites to load — check for at least 2 options (placeholder + 1 site)
    const siteSelect = await waitFor<HTMLSelectElement>(() => {
      const el = screen.getByLabelText(/site/i) as HTMLSelectElement;
      if (el.options.length < 2) throw new Error("Sites not loaded yet");
      return el;
    });

    // Pick the first real site option
    fireEvent.change(siteSelect, {
      target: { value: siteSelect.options[1]!.value },
    });

    // Click Save Draft
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /save draft/i }),
      ).not.toBeDisabled();
    });
    fireEvent.click(screen.getByRole("button", { name: /save draft/i }));

    await waitFor(() => expect(capturedBody).not.toBeNull());
    expect((capturedBody as Record<string, unknown>).currency).toBe("USD");
    // Should navigate to the new quote
    await waitFor(() =>
      expect(mockPush).toHaveBeenCalledWith("/quotes/q-saved-draft-001"),
    );
  });
});
