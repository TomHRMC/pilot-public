/**
 * ChangeOrderSection unit tests (MOB-B2)
 *
 * Location: apps/mobile/__tests__/batch_mob_b2/ChangeOrderSection.test.tsx
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

import { ChangeOrderSection } from "../../features/jobs/components/detail/ChangeOrderSection";

const mockCreate = jest.fn().mockResolvedValue({});

jest.mock("../../features/offline-sync/hooks/useCreateChangeOrder", () => ({
  useCreateChangeOrder: () => ({
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

const server = setupServer(
  http.get("*/api/v1/jobs/:jobId/change-orders", () => {
    return HttpResponse.json([
      {
        id: "co-001",
        tenant_id: "tenant-001",
        job_id: JOB_ID,
        description: "Panel upgrade addition",
        subtotal_cents: 32000,
        tax_cents: 2880,
        total_cents: 34880,
        is_active: true,
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

describe("ChangeOrderSection", () => {
  it("renders change order list from API fixture", async () => {
    render(<ChangeOrderSection jobId={JOB_ID} testID="co-section" />, {
      wrapper,
    });

    await waitFor(() => {
      expect(screen.getByTestId("co-row-co-001")).toBeTruthy();
      expect(screen.getByText("Panel upgrade addition")).toBeTruthy();
      expect(screen.getByText("$348.80")).toBeTruthy();
    });
  });

  it("opens add CO modal on '+ Add' press", async () => {
    render(<ChangeOrderSection jobId={JOB_ID} testID="co-section" />, {
      wrapper,
    });

    act(() => {
      fireEvent.press(screen.getByTestId("add-change-order-button"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("co-title-input")).toBeTruthy();
      expect(screen.getByTestId("submit-co-button")).toBeTruthy();
    });
  });

  it("calls create() with title and totalAmountCents on submit", async () => {
    render(<ChangeOrderSection jobId={JOB_ID} testID="co-section" />, {
      wrapper,
    });

    act(() => {
      fireEvent.press(screen.getByTestId("add-change-order-button"));
    });

    await waitFor(() =>
      expect(screen.getByTestId("co-title-input")).toBeTruthy(),
    );

    fireEvent.changeText(
      screen.getByTestId("co-title-input"),
      "Conduit run addition",
    );
    fireEvent.changeText(screen.getByTestId("co-total-input"), "250.00");

    await act(async () => {
      fireEvent.press(screen.getByTestId("submit-co-button"));
    });

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({
          jobId: JOB_ID,
          title: "Conduit run addition",
          totalAmountCents: 25000,
        }),
      );
    });
  });
});
