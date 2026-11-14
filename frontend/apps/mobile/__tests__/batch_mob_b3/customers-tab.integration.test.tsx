/**
 * Customers tab integration tests (MOB-B3)
 *
 * Location: apps/mobile/__tests__/batch_mob_b3/customers-tab.integration.test.tsx
 *
 * Tests CustomersTabScreen end-to-end with MSW-intercepted API calls.
 */

import React from "react";
import {
  render,
  screen,
  waitFor,
  fireEvent,
  act,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import { router } from "expo-router";
import {
  ALL_CUSTOMER_FIXTURES,
  CUSTOMER_JOHN_SMITH,
  CUSTOMER_JANE_DOE,
  CUSTOMER_ACME_CORP,
} from "../../mocks/handlers/customersHandlers";
import { CustomersTabScreen } from "../../features/customers/components/CustomersTabScreen";

// jest.mock is hoisted — use jest.fn() inline to avoid undefined reference
jest.mock("expo-router", () => ({
  router: { push: jest.fn(), back: jest.fn() },
  useRouter: () => require("expo-router").router,
}));

const mockRouterPush = router.push as jest.Mock;

// ── Test server ───────────────────────────────────────────────────────────────

const capturedRequests: URL[] = [];

// Backend returns PaginatedCustomerResponse { items, total, limit, offset }
const server = setupServer(
  http.get("*/api/v1/customers/", ({ request }) => {
    capturedRequests.push(new URL(request.url));
    const url = new URL(request.url);
    const search = url.searchParams.get("search")?.toLowerCase() ?? "";

    const results = search
      ? ALL_CUSTOMER_FIXTURES.filter(
          (c) =>
            c.display_name.toLowerCase().includes(search) ||
            (c.email ?? "").toLowerCase().includes(search),
        )
      : ALL_CUSTOMER_FIXTURES;

    return HttpResponse.json({
      items: results,
      total: results.length,
      limit: 50,
      offset: 0,
    });
  }),
);

let qc: QueryClient;

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  qc?.clear();
  mockRouterPush.mockClear();
  capturedRequests.length = 0;
});
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("CustomersTabScreen integration", () => {
  it("renders 3 CustomerListItem cards when MSW returns 3 customers", async () => {
    render(<CustomersTabScreen />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(CUSTOMER_JOHN_SMITH.display_name)).toBeTruthy();
    });

    expect(screen.getByText(CUSTOMER_JANE_DOE.display_name)).toBeTruthy();
    expect(screen.getByText(CUSTOMER_ACME_CORP.display_name)).toBeTruthy();
    expect(
      screen.getByTestId(`customer-row-${CUSTOMER_JOHN_SMITH.id}`),
    ).toBeTruthy();
  });

  it("renders empty state copy when MSW returns []", async () => {
    server.use(
      http.get("*/api/v1/customers/", () => {
        return HttpResponse.json({ items: [], total: 0, limit: 50, offset: 0 });
      }),
    );

    render(<CustomersTabScreen />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("customers-empty")).toBeTruthy();
    });

    expect(screen.getByText("No customers found")).toBeTruthy();
    expect(screen.queryByTestId("customers-list")).toBeTruthy();
  });

  it("renders ActivityIndicator while loading (before MSW responds)", async () => {
    // Delay the server response to observe loading state
    server.use(
      http.get("*/api/v1/customers/", async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
        return HttpResponse.json({
          items: ALL_CUSTOMER_FIXTURES,
          total: ALL_CUSTOMER_FIXTURES.length,
          limit: 50,
          offset: 0,
        });
      }),
    );

    render(<CustomersTabScreen />, { wrapper });

    expect(screen.getByTestId("customers-loading")).toBeTruthy();

    await waitFor(() => {
      expect(screen.queryByTestId("customers-loading")).toBeNull();
    });
  });

  it("renders error state + 'Try again' when MSW returns 500", async () => {
    server.use(
      http.get("*/api/v1/customers/", () => {
        return HttpResponse.json({ detail: "server error" }, { status: 500 });
      }),
    );

    render(<CustomersTabScreen />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("customers-error")).toBeTruthy();
    });

    expect(screen.getByText("Failed to load customers")).toBeTruthy();
    expect(screen.getByText("Try again")).toBeTruthy();
  });

  it("calls API with ?search= after 300ms debounce when user types in search bar", async () => {
    render(<CustomersTabScreen />, { wrapper });

    // Wait for initial load
    await waitFor(() => {
      expect(screen.getByText(CUSTOMER_JOHN_SMITH.display_name)).toBeTruthy();
    });

    // Clear initial requests
    capturedRequests.length = 0;

    const searchInput = screen.getByTestId("customers-search-input");

    // Type into search bar
    await act(async () => {
      fireEvent.changeText(searchInput, "acme");
      // Advance past debounce
      await new Promise((resolve) => setTimeout(resolve, 350));
    });

    await waitFor(() => {
      const searchReqs = capturedRequests.filter((url) =>
        url.searchParams.has("search"),
      );
      expect(searchReqs.length).toBeGreaterThan(0);
      expect(searchReqs[0].searchParams.get("search")).toBe("acme");
    });
  });

  it("shows search-specific empty copy when MSW returns [] for search", async () => {
    server.use(
      http.get("*/api/v1/customers/", ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.has("search")) {
          return HttpResponse.json({
            items: [],
            total: 0,
            limit: 50,
            offset: 0,
          });
        }
        return HttpResponse.json({
          items: ALL_CUSTOMER_FIXTURES,
          total: ALL_CUSTOMER_FIXTURES.length,
          limit: 50,
          offset: 0,
        });
      }),
    );

    render(<CustomersTabScreen />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(CUSTOMER_JOHN_SMITH.display_name)).toBeTruthy();
    });

    const searchInput = screen.getByTestId("customers-search-input");

    await act(async () => {
      fireEvent.changeText(searchInput, "zzz");
      await new Promise((resolve) => setTimeout(resolve, 350));
    });

    await waitFor(() => {
      expect(screen.getByTestId("customers-search-empty")).toBeTruthy();
    });
  });

  it("pressing customer card calls router.push with customers/${customerId}", async () => {
    render(<CustomersTabScreen />, { wrapper });

    await waitFor(() => {
      expect(
        screen.getByTestId(`customer-row-${CUSTOMER_JOHN_SMITH.id}`),
      ).toBeTruthy();
    });

    fireEvent.press(
      screen.getByTestId(`customer-row-${CUSTOMER_JOHN_SMITH.id}`),
    );

    expect(mockRouterPush).toHaveBeenCalledWith(
      `/(tabs)/customers/${CUSTOMER_JOHN_SMITH.id}`,
    );
  });

  it("renders the customers FlatList", async () => {
    render(<CustomersTabScreen />, { wrapper });

    await waitFor(() => {
      expect(screen.getByTestId("customers-list")).toBeTruthy();
    });
  });

  it("renders search bar", async () => {
    render(<CustomersTabScreen />, { wrapper });

    expect(screen.getByTestId("customers-search-input")).toBeTruthy();
  });
});
