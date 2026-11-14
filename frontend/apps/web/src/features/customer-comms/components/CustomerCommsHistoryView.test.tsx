/**
 * CustomerCommsHistoryView — unit tests (web)
 *
 * Location: apps/web/src/features/customer-comms/components/CustomerCommsHistoryView.test.tsx
 *
 * Tests per design doc G.1.
 * POST-BETA: rewritten to match the real CommunicationHistoryItem shape (not SmsThread).
 * Fix 2: updated to mock useCustomerSmsThreads; keys now prefixed hist-/thread-.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("../hooks/useCustomerCommsHistory", () => ({
  useCustomerCommsHistory: vi.fn(),
}));

vi.mock("../hooks/useCustomerCommsSse", () => ({
  useCustomerCommsSse: vi.fn(() => ({ isConnected: false })),
}));

vi.mock("../hooks/useCustomerSmsThreads", () => ({
  useCustomerSmsThreads: vi.fn(() => ({
    threads: [],
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

import { CustomerCommsHistoryView } from "./CustomerCommsHistoryView";
import { useCustomerCommsHistory } from "../hooks/useCustomerCommsHistory";
import { useCustomerSmsThreads } from "../hooks/useCustomerSmsThreads";
import type { CommunicationHistoryItem } from "../hooks/useCustomerCommsHistory";
import type { SmsThread } from "@pilot/ui";

const mockUseCustomerCommsHistory = vi.mocked(useCustomerCommsHistory);
const mockUseCustomerSmsThreads = vi.mocked(useCustomerSmsThreads);

function makeItem(
  id: string,
  channel: "sms" | "email",
  status: "sent" | "failed" | "pending" = "sent",
): CommunicationHistoryItem {
  return {
    communication_id: id,
    template_code: "job_dispatch",
    actual_channel: channel,
    channel_override_flag: false,
    customer_preferred_channel: channel,
    rendered_message: `Test message ${id}`,
    rendered_subject: channel === "email" ? `Subject ${id}` : null,
    status,
    sent_at: "2026-05-26T09:00:00Z",
    sender_user_id: "tech-001",
    job_id: "job-001",
  };
}

function makeThread(id: string, customerId: string): SmsThread {
  return {
    thread_id: id,
    tenant_id: "tenant-001",
    customer_id: customerId,
    customer_name: "John Smith",
    customer_phone: "+15555551234",
    customer_sms_opted_out: false,
    customer_opted_out_at: null,
    tech_id: "tech-001",
    tech_name: "Mike Johnson",
    tenant_phone_number_id: "phone-001",
    status: "active",
    first_message_at: "2026-05-26T08:00:00Z",
    last_message_at: "2026-05-26T08:05:00Z",
    message_count: 2,
    unread_count: 1,
    originating_job_id: null,
    originating_job_display: null,
    created_at: "2026-05-26T08:00:00Z",
    updated_at: "2026-05-26T08:05:00Z",
    messages: [
      {
        message_id: `msg-${id}-1`,
        thread_id: id,
        direction: "outbound",
        channel: "sms",
        body: `Thread message out ${id}`,
        segment_count: 1,
        status: "delivered",
        carrier_message_id: null,
        composition_method: "free_form_text",
        template_id: null,
        voice_audio_id: null,
        sent_at: "2026-05-26T08:00:00Z",
        delivered_at: "2026-05-26T08:00:02Z",
        received_at: null,
        audit_user_id: "tech-001",
      },
      {
        message_id: `msg-${id}-2`,
        thread_id: id,
        direction: "inbound",
        channel: "sms",
        body: `Thread reply in ${id}`,
        segment_count: 1,
        status: "received",
        carrier_message_id: null,
        composition_method: "free_form_text",
        template_id: null,
        voice_audio_id: null,
        sent_at: null,
        delivered_at: null,
        received_at: "2026-05-26T08:05:00Z",
        audit_user_id: "tech-001",
      },
    ],
  };
}

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe("CustomerCommsHistoryView", () => {
  it("renders SMS items from history with SMS badge", () => {
    mockUseCustomerCommsHistory.mockReturnValue({
      items: [makeItem("comm-001", "sms")],
      customerOptedOut: false,
      optedOutAt: null,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<CustomerCommsHistoryView customerId="customer-001" />, { wrapper });

    // key is now hist-comm-001
    expect(screen.getByTestId("comm-item-hist-comm-001")).toBeTruthy();
    expect(screen.getByText("SMS")).toBeTruthy();
    expect(screen.getByText("Test message comm-001")).toBeTruthy();
  });

  it("renders email items with Email badge", () => {
    mockUseCustomerCommsHistory.mockReturnValue({
      items: [makeItem("comm-002", "email")],
      customerOptedOut: false,
      optedOutAt: null,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<CustomerCommsHistoryView customerId="customer-001" />, { wrapper });

    expect(screen.getByText("Email")).toBeTruthy();
  });

  it("renders multiple items from history", () => {
    mockUseCustomerCommsHistory.mockReturnValue({
      items: [makeItem("comm-001", "sms"), makeItem("comm-002", "email")],
      customerOptedOut: false,
      optedOutAt: null,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<CustomerCommsHistoryView customerId="customer-001" />, { wrapper });

    expect(screen.getByTestId("comm-item-hist-comm-001")).toBeTruthy();
    expect(screen.getByTestId("comm-item-hist-comm-002")).toBeTruthy();
  });

  it("renders thread messages (inbound) from useCustomerSmsThreads", () => {
    mockUseCustomerCommsHistory.mockReturnValue({
      items: [],
      customerOptedOut: false,
      optedOutAt: null,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseCustomerSmsThreads.mockReturnValue({
      threads: [makeThread("thread-001", "customer-001")],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<CustomerCommsHistoryView customerId="customer-001" />, { wrapper });

    // outbound message from thread
    expect(
      screen.getByTestId("comm-item-thread-msg-thread-001-1"),
    ).toBeTruthy();
    expect(screen.getByText("Thread message out thread-001")).toBeTruthy();
    // inbound message from thread
    expect(
      screen.getByTestId("comm-item-thread-msg-thread-001-2"),
    ).toBeTruthy();
    expect(screen.getByText("Thread reply in thread-001")).toBeTruthy();
    // inbound badge
    expect(screen.getByText("inbound")).toBeTruthy();
  });

  it("empty items array renders empty state when both sources empty", () => {
    mockUseCustomerCommsHistory.mockReturnValue({
      items: [],
      customerOptedOut: false,
      optedOutAt: null,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseCustomerSmsThreads.mockReturnValue({
      threads: [],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<CustomerCommsHistoryView customerId="customer-001" />, { wrapper });

    expect(screen.getByTestId("comms-history-empty")).toBeTruthy();
  });

  it("shows loading spinner while history fetching", () => {
    mockUseCustomerCommsHistory.mockReturnValue({
      items: [],
      customerOptedOut: false,
      optedOutAt: null,
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseCustomerSmsThreads.mockReturnValue({
      threads: [],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    const { container } = render(
      <CustomerCommsHistoryView customerId="customer-001" />,
      { wrapper },
    );

    expect(container.querySelector(".animate-spin")).toBeTruthy();
  });

  it("shows loading spinner while threads fetching", () => {
    mockUseCustomerCommsHistory.mockReturnValue({
      items: [],
      customerOptedOut: false,
      optedOutAt: null,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseCustomerSmsThreads.mockReturnValue({
      threads: [],
      isLoading: true,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    const { container } = render(
      <CustomerCommsHistoryView customerId="customer-001" />,
      { wrapper },
    );

    expect(container.querySelector(".animate-spin")).toBeTruthy();
  });

  it("shows error state on history fetch failure", () => {
    mockUseCustomerCommsHistory.mockReturnValue({
      items: [],
      customerOptedOut: false,
      optedOutAt: null,
      isLoading: false,
      isError: true,
      error: new Error("Network error"),
      refetch: vi.fn(),
    });
    mockUseCustomerSmsThreads.mockReturnValue({
      threads: [],
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });

    render(<CustomerCommsHistoryView customerId="customer-001" />, { wrapper });

    expect(screen.getByTestId("comms-history-error")).toBeTruthy();
  });

  it("shows error state on threads fetch failure", () => {
    mockUseCustomerCommsHistory.mockReturnValue({
      items: [],
      customerOptedOut: false,
      optedOutAt: null,
      isLoading: false,
      isError: false,
      error: null,
      refetch: vi.fn(),
    });
    mockUseCustomerSmsThreads.mockReturnValue({
      threads: [],
      isLoading: false,
      isError: true,
      error: new Error("Threads fetch failed"),
      refetch: vi.fn(),
    });

    render(<CustomerCommsHistoryView customerId="customer-001" />, { wrapper });

    expect(screen.getByTestId("comms-history-error")).toBeTruthy();
  });
});
