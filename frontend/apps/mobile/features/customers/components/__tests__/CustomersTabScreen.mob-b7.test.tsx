/**
 * CustomersTabScreen "+" button tests — MOB-B7
 *
 * Location: apps/mobile/features/customers/components/__tests__/CustomersTabScreen.mob-b7.test.tsx
 *
 * Tests:
 *   - "+" button visible in header
 *   - Tapping "+" opens CreateCustomerBottomSheet
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CustomersTabScreen } from "../CustomersTabScreen";

// ── Mock WatermelonDB ─────────────────────────────────────────────────────────
jest.mock("../../../../database", () => ({
  database: {
    write: jest
      .fn()
      .mockImplementation(async (fn: () => Promise<unknown>) => fn()),
    get: jest.fn().mockReturnValue({ create: jest.fn() }),
  },
}));

// ── Mock expo-router ──────────────────────────────────────────────────────────
const mockPush = jest.fn();
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: mockPush, back: jest.fn(), replace: jest.fn() }),
  router: { push: mockPush, back: jest.fn() },
  Link: ({ children }: { children: React.ReactNode }) => children,
}));

// ── Mock useCustomers ─────────────────────────────────────────────────────────
jest.mock("../../hooks/useCustomers", () => ({
  useCustomers: () => ({
    customers: [
      {
        id: "cust-001",
        display_name: "John Smith",
        type: "residential",
        email: null,
        first_name: "John",
        last_name: "Smith",
        company_name: null,
        tenant_id: "t-001",
      },
    ],
    isLoading: false,
    isError: false,
    refetch: jest.fn(),
    isFetching: false,
  }),
}));

// ── Mock useCreateCustomer ────────────────────────────────────────────────────
jest.mock("../../hooks/useCreateCustomer", () => ({
  useCreateCustomer: () => ({
    mutate: jest.fn(),
    isPending: false,
  }),
}));

// ── Mock CreateCustomerBottomSheet (avoid deep render complexity) ─────────────
jest.mock("../CreateCustomerBottomSheet", () => ({
  CreateCustomerBottomSheet: ({ visible }: { visible: boolean }) => {
    const React = require("react");
    const { View } = require("react-native");
    return visible
      ? React.createElement(View, { testID: "create-customer-bottom-sheet" })
      : null;
  },
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("CustomersTabScreen — MOB-B7 Add Customer", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders the '+' add customer button in the header", () => {
    render(<CustomersTabScreen />, { wrapper });

    expect(screen.getByTestId("add-customer-button")).toBeTruthy();
  });

  it("opens CreateCustomerBottomSheet when '+' is pressed", () => {
    render(<CustomersTabScreen />, { wrapper });

    // Bottom sheet not visible initially
    expect(screen.queryByTestId("create-customer-bottom-sheet")).toBeNull();

    // Tap the "+" button
    fireEvent.press(screen.getByTestId("add-customer-button"));

    // Bottom sheet now visible
    expect(screen.getByTestId("create-customer-bottom-sheet")).toBeTruthy();
  });
});
