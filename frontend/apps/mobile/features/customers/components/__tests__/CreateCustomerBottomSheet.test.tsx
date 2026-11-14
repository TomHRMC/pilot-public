/**
 * CreateCustomerBottomSheet unit tests — MOB-B7
 *
 * Location: apps/mobile/features/customers/components/__tests__/CreateCustomerBottomSheet.test.tsx
 *
 * Tests:
 *   - Renders form fields (display name, phone, email, type selector)
 *   - Submit with valid data calls useCreateCustomer
 *   - Submit with empty display_name shows validation error
 *   - Cancel button calls onClose
 */

import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CreateCustomerBottomSheet } from "../CreateCustomerBottomSheet";

// ── Mock WatermelonDB ─────────────────────────────────────────────────────────
jest.mock("../../../../database", () => ({
  database: {
    write: jest
      .fn()
      .mockImplementation(async (fn: () => Promise<unknown>) => fn()),
    get: jest.fn().mockReturnValue({ create: jest.fn() }),
  },
}));

// ── Mock useCreateCustomer ────────────────────────────────────────────────────
const mockMutate = jest.fn();

jest.mock("../../hooks/useCreateCustomer", () => ({
  useCreateCustomer: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

// ── Mock expo-router ──────────────────────────────────────────────────────────
jest.mock("expo-router", () => ({
  useRouter: () => ({ push: jest.fn(), back: jest.fn(), replace: jest.fn() }),
  router: { push: jest.fn(), back: jest.fn() },
  Link: ({ children }: { children: React.ReactNode }) => children,
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

const mockOnClose = jest.fn();

function renderSheet(visible = true) {
  return render(
    <CreateCustomerBottomSheet visible={visible} onClose={mockOnClose} />,
    { wrapper },
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("CreateCustomerBottomSheet — MOB-B7", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders form fields when visible", () => {
    renderSheet(true);

    expect(screen.getByTestId("customer-display-name")).toBeTruthy();
    expect(screen.getByTestId("customer-mobile-phone")).toBeTruthy();
    expect(screen.getByTestId("customer-email")).toBeTruthy();
    expect(screen.getByTestId("customer-type-selector")).toBeTruthy();
    expect(screen.getByTestId("type-person")).toBeTruthy();
    expect(screen.getByTestId("type-company")).toBeTruthy();
    expect(screen.getByTestId("create-customer-submit")).toBeTruthy();
  });

  it("shows validation error when display_name is empty on submit", () => {
    renderSheet(true);

    fireEvent.press(screen.getByTestId("create-customer-submit"));

    expect(screen.getByTestId("display-name-error")).toBeTruthy();
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("calls useCreateCustomer mutate with valid data on submit", async () => {
    mockMutate.mockImplementation(
      (_data: unknown, opts: { onSuccess: () => void }) => {
        opts?.onSuccess?.();
      },
    );

    renderSheet(true);

    fireEvent.changeText(
      screen.getByTestId("customer-display-name"),
      "John Smith",
    );
    fireEvent.changeText(
      screen.getByTestId("customer-mobile-phone"),
      "555-867-5309",
    );
    fireEvent.changeText(
      screen.getByTestId("customer-email"),
      "john@example.com",
    );
    fireEvent.press(screen.getByTestId("create-customer-submit"));

    await waitFor(() => {
      expect(mockMutate).toHaveBeenCalledWith(
        expect.objectContaining({
          display_name: "John Smith",
          mobile_phone: "555-867-5309",
          email: "john@example.com",
          type: "person",
        }),
        expect.any(Object),
      );
    });
  });

  it("calls onClose when cancel is pressed", () => {
    renderSheet(true);

    fireEvent.press(screen.getByTestId("create-customer-cancel"));

    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });
});
