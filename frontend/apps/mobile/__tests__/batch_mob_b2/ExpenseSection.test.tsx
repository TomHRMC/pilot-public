/**
 * ExpenseSection unit tests (MOB-B2)
 *
 * Location: apps/mobile/__tests__/batch_mob_b2/ExpenseSection.test.tsx
 */

import React from "react";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";

import { ExpenseSection } from "../../features/jobs/components/detail/ExpenseSection";

const mockCreate = jest.fn().mockResolvedValue({});

jest.mock("../../features/offline-sync/hooks/useCreateExpense", () => ({
  useCreateExpense: () => ({
    create: mockCreate,
    isPending: false,
    error: null,
  }),
}));

jest.mock("../../database", () => ({
  database: {
    write: jest
      .fn()
      .mockImplementation(async (fn: () => Promise<unknown>) => fn()),
    get: jest.fn().mockReturnValue({ create: jest.fn() }),
  },
}));

const JOB_ID = "job-today-001";
const USER_ID = "tech-user-001";
const TODAY = new Date().toISOString().slice(0, 10);

const server = setupServer(
  // MOB-B6: ExpenseSection now fetches categories from API — add handler here
  http.get("*/api/v1/job-expense-categories", () => {
    return HttpResponse.json({
      categories: [
        { code: "materials", name: "Materials", is_default: true },
        { code: "tools", name: "Tools & Equipment", is_default: false },
        { code: "subcontractor", name: "Subcontractor", is_default: false },
        { code: "fuel", name: "Fuel & Travel", is_default: false },
        { code: "other", name: "Other", is_default: false },
      ],
    });
  }),
  http.get("*/api/v1/jobs/:jobId/expenses", () => {
    return HttpResponse.json([
      {
        id: "expense-001",
        tenant_id: "tenant-001",
        job_id: JOB_ID,
        job_expense_category_code: "materials",
        description: "12 AWG wire",
        vendor_name: null,
        incurred_at: TODAY,
        cost_cents: 4500,
      },
      {
        id: "expense-002",
        tenant_id: "tenant-001",
        job_id: JOB_ID,
        job_expense_category_code: "tools",
        description: "Drill bit set",
        vendor_name: null,
        incurred_at: TODAY,
        cost_cents: 2800,
      },
    ]);
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  jest.clearAllMocks();
});
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return React.createElement(QueryClientProvider, { client: qc }, children);
}

describe("ExpenseSection", () => {
  it("renders 2 expense rows from API fixture", async () => {
    render(
      <ExpenseSection
        jobId={JOB_ID}
        userId={USER_ID}
        testID="expense-section"
      />,
      { wrapper },
    );

    await waitFor(() => {
      expect(screen.getByTestId("expense-row-expense-001")).toBeTruthy();
      expect(screen.getByTestId("expense-row-expense-002")).toBeTruthy();
    });
  });

  it("opens add expense modal when '+ Add' is pressed", async () => {
    render(
      <ExpenseSection
        jobId={JOB_ID}
        userId={USER_ID}
        testID="expense-section"
      />,
      { wrapper },
    );

    act(() => {
      fireEvent.press(screen.getByTestId("add-expense-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("expense-amount-input")).toBeTruthy();
      expect(screen.getByTestId("expense-submit-button")).toBeTruthy();
    });
  });

  it("calls create() with correct args on form submit", async () => {
    render(
      <ExpenseSection
        jobId={JOB_ID}
        userId={USER_ID}
        testID="expense-section"
      />,
      { wrapper },
    );

    act(() => {
      fireEvent.press(screen.getByTestId("add-expense-button"));
    });

    await waitFor(() =>
      expect(screen.getByTestId("expense-amount-input")).toBeTruthy(),
    );

    fireEvent.changeText(screen.getByTestId("expense-amount-input"), "45.00");
    fireEvent.changeText(
      screen.getByTestId("expense-description-input"),
      "12 AWG wire",
    );

    await act(async () => {
      fireEvent.press(screen.getByTestId("expense-submit-button"));
    });

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          jobId: JOB_ID,
          userId: USER_ID,
          jobExpenseCategoryCode: "materials",
          costCents: 4500,
          isBillable: true,
          incurredAt: expect.any(Date),
        }),
      );
    });
  });
});
