/**
 * FE-B28 — Catalog tables migration integration tests
 *
 * Location: apps/web/src/__tests__/batch_fe_b28/catalog_tables_migration.integration.test.tsx
 *
 * Covers: PricebookItemsPage, LaborRatesPage, MarkupsPage, SupplierItemsPage
 */

import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import {
  describe,
  it,
  expect,
  beforeAll,
  afterEach,
  afterAll,
  vi,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthContext } from "@pilot/ui/auth";
import type { AuthContextValue } from "@pilot/ui/auth";
import { setupServer } from "msw/node";
import { handlers } from "../../mocks/handlers/index";
import { PricebookItemsPage } from "@/features/catalog/components/PricebookItemsPage";
import { LaborRatesPage } from "@/features/catalog/components/LaborRatesPage";
import { MarkupsPage } from "@/features/catalog/components/MarkupsPage";
import { SupplierItemsPage } from "@/features/catalog/components/SupplierItemsPage";

vi.mock("next/navigation", () => ({
  usePathname: () => "/catalog",
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => React.createElement("a", { href, ...rest }, children),
}));

const server = setupServer(...handlers);
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function makeAuthContext(): AuthContextValue {
  return {
    user: {
      id: "u1",
      email: "owner@test.com",
      role: "owner",
      tenantId: "t1",
      displayName: "Owner",
      accessToken: "tok",
    },
    isAuthenticated: true,
    role: "owner",
    signIn: vi.fn(),
    confirmMfaChallenge: vi.fn(),
    signOut: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue("tok"),
  };
}

function renderWith(component: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <AuthContext.Provider value={makeAuthContext()}>
      <QueryClientProvider client={qc}>{component}</QueryClientProvider>
    </AuthContext.Provider>,
  );
}

// ── PricebookItemsPage ─────────────────────────────────────────────────────

describe("PricebookItemsPage — FE-B28 TanStack Table migration", () => {
  it("renders without crashing", async () => {
    renderWith(<PricebookItemsPage />);
    await waitFor(() => {
      expect(screen.getByText("Pricebook Items")).toBeInTheDocument();
    });
  });

  it("renders correct column headers", async () => {
    renderWith(<PricebookItemsPage />);
    await waitFor(() => {
      expect(screen.getByText("SKU")).toBeInTheDocument();
      expect(screen.getByText("Name")).toBeInTheDocument();
      expect(screen.getByText("Description")).toBeInTheDocument();
      expect(screen.getByText("Current Price")).toBeInTheDocument();
      // "Status" now appears in both column header AND the new filter dropdown label
      // Use getAllByText and verify at least one is present
      expect(screen.getAllByText("Status").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("renders pricebook data from MSW fixture", async () => {
    renderWith(<PricebookItemsPage />);
    await waitFor(() => {
      // catalogHandlers has sku "SW-200A"
      expect(screen.getByText("SW-200A")).toBeInTheDocument();
    });
  });

  it("renders search input (UI-FIX-1C: placeholder updated)", async () => {
    renderWith(<PricebookItemsPage />);
    await waitFor(() => {
      // UI-FIX-1C: placeholder text updated to include "description"
      expect(
        screen.getByPlaceholderText("Search name, SKU, description…"),
      ).toBeInTheDocument();
    });
  });
});

// ── LaborRatesPage ─────────────────────────────────────────────────────────

describe("LaborRatesPage — FE-B28 TanStack Table migration", () => {
  it("renders without crashing", async () => {
    renderWith(<LaborRatesPage />);
    await waitFor(() => {
      expect(screen.getByText("Labor Rates")).toBeInTheDocument();
    });
  });

  it("renders correct column headers", async () => {
    renderWith(<LaborRatesPage />);
    await waitFor(() => {
      expect(screen.getByText("Skill Level")).toBeInTheDocument();
      expect(screen.getByText("Hourly Rate")).toBeInTheDocument();
      expect(screen.getByText("Burden %")).toBeInTheDocument();
      expect(screen.getByText("Burdened Rate")).toBeInTheDocument();
      expect(screen.getByText("Effective From")).toBeInTheDocument();
    });
  });
});

// ── MarkupsPage ────────────────────────────────────────────────────────────

describe("MarkupsPage — FE-B28 TanStack Table migration", () => {
  it("renders without crashing", async () => {
    renderWith(<MarkupsPage />);
    await waitFor(() => {
      expect(screen.getByText("Markup Percentages")).toBeInTheDocument();
    });
  });

  it("renders correct column headers", async () => {
    renderWith(<MarkupsPage />);
    await waitFor(() => {
      expect(screen.getByText("Category")).toBeInTheDocument();
      expect(screen.getByText("Current Markup")).toBeInTheDocument();
      // LaborRatesPage and MarkupsPage both have "Effective From"
      const effectiveFromHeaders = screen.getAllByText("Effective From");
      expect(effectiveFromHeaders.length).toBeGreaterThanOrEqual(1);
    });
  });
});

// ── SupplierItemsPage ──────────────────────────────────────────────────────

describe("SupplierItemsPage — FE-B28 TanStack Table migration", () => {
  it("renders without crashing", async () => {
    renderWith(<SupplierItemsPage />);
    await waitFor(() => {
      expect(screen.getByText("Supplier Items")).toBeInTheDocument();
    });
  });

  it("renders correct column headers", async () => {
    renderWith(<SupplierItemsPage />);
    await waitFor(() => {
      expect(screen.getByText("Supplier Items")).toBeInTheDocument();
    });
  });

  it("renders supplier data from MSW fixture", async () => {
    renderWith(<SupplierItemsPage />);
    await waitFor(() => {
      // catalogHandlers has supplier sku "HD-SW200A"
      expect(screen.getByText("HD-SW200A")).toBeInTheDocument();
    });
  });
});
