/**
 * Customer detail integration tests (MOB-B3)
 *
 * Location: apps/mobile/__tests__/batch_mob_b3/customer-detail.integration.test.tsx
 *
 * Tests CustomerDetailScreen end-to-end with MSW-intercepted API calls.
 */

import React from "react";
import {
  render,
  screen,
  waitFor,
  fireEvent,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import { router } from "expo-router";
import {
  CUSTOMER_JOHN_SMITH,
  SITE_MAIN_HOME,
  SITE_RENTAL_PROPERTY,
} from "../../mocks/handlers/customersHandlers";
import { CustomerDetailScreen } from "../../features/customers/components/CustomerDetailScreen";

// jest.mock is hoisted — use jest.fn() inline so factory has valid references
jest.mock("expo-router", () => ({
  router: {
    push: jest.fn(),
    back: jest.fn(),
  },
  useRouter: () => require("expo-router").router,
}));

// ── Convenience references to mock fns ───────────────────────────────────────

const mockRouterPush = router.push as jest.Mock;
const mockRouterBack = router.back as jest.Mock;

// ── Test server ───────────────────────────────────────────────────────────────

const server = setupServer(
  http.get("*/api/v1/customers/:customerId", ({ params }) => {
    const { customerId } = params as { customerId: string };
    if (customerId === CUSTOMER_JOHN_SMITH.id) {
      return HttpResponse.json(CUSTOMER_JOHN_SMITH);
    }
    return HttpResponse.json({ detail: "Not found" }, { status: 404 });
  }),
  http.get("*/api/v1/sites/", ({ request }) => {
    const url = new URL(request.url);
    const customerId = url.searchParams.get("customer_id");
    if (customerId === CUSTOMER_JOHN_SMITH.id) {
      return HttpResponse.json([SITE_MAIN_HOME, SITE_RENTAL_PROPERTY]);
    }
    return HttpResponse.json([]);
  }),
);

let qc: QueryClient;

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  qc?.clear();
  mockRouterPush.mockClear();
  mockRouterBack.mockClear();
});
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("CustomerDetailScreen integration", () => {
  it("renders customer display_name in header from MSW fixture", async () => {
    render(<CustomerDetailScreen customerId={CUSTOMER_JOHN_SMITH.id} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(screen.getByTestId("customer-detail-name")).toBeTruthy();
    });

    expect(screen.getByText(CUSTOMER_JOHN_SMITH.display_name)).toBeTruthy();
  });

  it("renders customer email when present", async () => {
    render(<CustomerDetailScreen customerId={CUSTOMER_JOHN_SMITH.id} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(screen.getByTestId("customer-detail-email")).toBeTruthy();
    });

    expect(screen.getByText(CUSTOMER_JOHN_SMITH.email!)).toBeTruthy();
  });

  it("renders 2 site rows from MSW fixture", async () => {
    render(<CustomerDetailScreen customerId={CUSTOMER_JOHN_SMITH.id} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(screen.getByTestId(`site-row-${SITE_MAIN_HOME.id}`)).toBeTruthy();
    });

    expect(
      screen.getByTestId(`site-row-${SITE_RENTAL_PROPERTY.id}`),
    ).toBeTruthy();
    expect(screen.getByText("Main Home")).toBeTruthy();
    expect(screen.getByText("Rental Property")).toBeTruthy();
  });

  it("renders site address from fixture", async () => {
    render(<CustomerDetailScreen customerId={CUSTOMER_JOHN_SMITH.id} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(screen.getByText("Main Home")).toBeTruthy();
    });

    // Address from SITE_MAIN_HOME fixture: "123 Main St, Springfield, IL 62701"
    expect(screen.getByText("123 Main St, Springfield, IL 62701")).toBeTruthy();
  });

  it("pressing 'Message Customer' calls router.push with customers/${id}/comms", async () => {
    render(<CustomerDetailScreen customerId={CUSTOMER_JOHN_SMITH.id} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(screen.getByTestId("customer-detail-message-btn")).toBeTruthy();
    });

    fireEvent.press(screen.getByTestId("customer-detail-message-btn"));

    expect(mockRouterPush).toHaveBeenCalledWith(
      `/(tabs)/customers/${CUSTOMER_JOHN_SMITH.id}/comms`,
    );
  });

  it("pressing Back button calls router.back()", async () => {
    render(<CustomerDetailScreen customerId={CUSTOMER_JOHN_SMITH.id} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(screen.getByTestId("customer-detail-back-btn")).toBeTruthy();
    });

    fireEvent.press(screen.getByTestId("customer-detail-back-btn"));
    expect(mockRouterBack).toHaveBeenCalled();
  });

  it("renders error state when MSW returns 500 for customer", async () => {
    server.use(
      http.get("*/api/v1/customers/:customerId", () => {
        return HttpResponse.json({ detail: "server error" }, { status: 500 });
      }),
    );

    render(<CustomerDetailScreen customerId={CUSTOMER_JOHN_SMITH.id} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(screen.getByTestId("customer-detail-error")).toBeTruthy();
    });

    expect(screen.getByText("Failed to load customer")).toBeTruthy();
    expect(screen.getByTestId("customer-detail-retry-btn")).toBeTruthy();
  });

  it("renders 'No sites on record' when customer has no sites", async () => {
    server.use(
      http.get("*/api/v1/sites/", () => {
        return HttpResponse.json([]);
      }),
    );

    render(<CustomerDetailScreen customerId={CUSTOMER_JOHN_SMITH.id} />, {
      wrapper,
    });

    await waitFor(() => {
      expect(screen.getByText(CUSTOMER_JOHN_SMITH.display_name)).toBeTruthy();
    });

    expect(screen.getByText("No sites on record")).toBeTruthy();
  });

  it("renders loading indicator while fetching", async () => {
    server.use(
      http.get("*/api/v1/customers/:customerId", async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
        return HttpResponse.json(CUSTOMER_JOHN_SMITH);
      }),
    );

    render(<CustomerDetailScreen customerId={CUSTOMER_JOHN_SMITH.id} />, {
      wrapper,
    });

    expect(screen.getByTestId("customer-detail-loading")).toBeTruthy();

    await waitFor(() => {
      expect(screen.queryByTestId("customer-detail-loading")).toBeNull();
    });
  });
});
