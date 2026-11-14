/**
 * RecordPaymentModal unit tests — FE-B22
 *
 * Location: apps/web/src/features/invoices/components/__tests__/RecordPaymentModal.test.tsx
 */

import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { NotificationQueueProvider } from "@pilot/ui/notification-banner";
import { RecordPaymentModal } from "../RecordPaymentModal";

vi.mock("../../hooks/useRecordPayment", () => ({
  useRecordPayment: vi.fn(),
  MANUAL_PAYMENT_METHOD_ID: "00000000-0000-0000-0000-000000000001",
  PAYMENT_STATUS_SUCCEEDED_ID: "fa70374c-513a-4cc3-baca-22a54a594a4d",
}));

import { useRecordPayment } from "../../hooks/useRecordPayment";

function createWrapper() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={qc}>
        <NotificationQueueProvider>{children}</NotificationQueueProvider>
      </QueryClientProvider>
    );
  }
  return Wrapper;
}

const BASE_PROPS = {
  open: true,
  invoiceId: "inv-00000001-0000-0000-0000-000000000001",
  balanceDueCents: 57914,
  onClose: vi.fn(),
};

describe("RecordPaymentModal", () => {
  let mockMutate: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    mockMutate = vi.fn();
    (useRecordPayment as ReturnType<typeof vi.fn>).mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    });
  });

  it("renders nothing when open=false", () => {
    const { container } = render(
      <RecordPaymentModal {...BASE_PROPS} open={false} />,
      { wrapper: createWrapper() },
    );
    expect(container.firstChild).toBeNull();
  });

  it("pre-fills amount field with balance due ($579.14)", () => {
    render(<RecordPaymentModal {...BASE_PROPS} />, {
      wrapper: createWrapper(),
    });
    const amountInput = screen.getByLabelText(/amount/i) as HTMLInputElement;
    expect(amountInput.value).toBe("579.14");
  });

  it("Cancel calls onClose without firing mutation", () => {
    render(<RecordPaymentModal {...BASE_PROPS} />, {
      wrapper: createWrapper(),
    });
    fireEvent.click(screen.getByText("Cancel"));
    expect(BASE_PROPS.onClose).toHaveBeenCalledTimes(1);
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("submitting fires useRecordPayment with correct amount_cents", () => {
    render(<RecordPaymentModal {...BASE_PROPS} />, {
      wrapper: createWrapper(),
    });
    // Use getByRole to select the submit button specifically (not the modal title)
    const submitBtn = screen.getByRole("button", { name: /^record payment$/i });
    fireEvent.click(submitBtn);
    expect(mockMutate).toHaveBeenCalledWith(
      expect.objectContaining({ amount_cents: 57914 }),
    );
  });

  it("shows 'Recording…' when isPending=true", () => {
    (useRecordPayment as ReturnType<typeof vi.fn>).mockReturnValue({
      mutate: mockMutate,
      isPending: true,
    });
    render(<RecordPaymentModal {...BASE_PROPS} />, {
      wrapper: createWrapper(),
    });
    expect(screen.getByText("Recording…")).toBeTruthy();
  });
});
