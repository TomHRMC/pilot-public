/**
 * ReplyComposer — unit tests
 *
 * Location: apps/mobile/features/customer-comms/components/ReplyComposer.test.tsx
 *
 * CRITICAL TCPA compliance tests are included here.
 * Tests per design doc G.1.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// Mock all dependencies
jest.mock("@pilot/ui", () => ({
  usePreviewBeforeSend: jest.fn(() => ({
    preview: jest.fn(),
    send: jest.fn(),
    isSending: false,
    isModalOpen: false,
    closeModal: jest.fn(),
    previewData: null,
  })),
  SmsQuotaIndicator: ({ quota, testID }: { quota: unknown; testID?: string }) =>
    null,
  useSegmentCount: jest.fn(() => ({
    segmentCount: 1,
    encoding: "gsm7" as const,
    charCount: 10,
    charsPerSegment: 160,
    charsRemaining: 150,
  })),
  NotificationBanner: ({
    notification,
  }: {
    notification: { title: string };
  }) => <>{notification.title}</>,
  MessagePreviewModal: () => null,
}));

jest.mock("../hooks/useReplyToThread", () => ({
  useReplyToThread: () => ({ mutate: jest.fn(), isPending: false }),
}));

jest.mock("../hooks/useSmsQuota", () => ({
  useSmsQuota: jest.fn(() => ({
    quota: {
      period_id: "p1",
      used_segments: 50,
      included_segments: 500,
      remaining_segments: 450,
      overage_segments: 0,
      cap_policy: "soft",
      period_start: "2026-05-01",
      period_end: "2026-05-31",
      blocked_reason: null,
      projected_month_end_segments: 80,
    },
    isSendBlocked: false,
    quotaState: { state: "normal", remaining: 450, included: 500 },
  })),
}));

const mockStartDictating = jest.fn();
jest.mock("../hooks/useVoiceDictation", () => ({
  useVoiceDictation: () => ({
    state: { phase: "idle" },
    startDictating: mockStartDictating,
    stopDictating: jest.fn(),
    reset: jest.fn(),
  }),
}));

// Lazy import to allow mock to be set up first
let ReplyComposer: typeof import("./ReplyComposer").ReplyComposer;
let useSmsQuota: typeof import("../hooks/useSmsQuota").useSmsQuota;

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

beforeEach(() => {
  const module = require("./ReplyComposer");
  ReplyComposer = module.ReplyComposer;
  const quotaModule = require("../hooks/useSmsQuota");
  useSmsQuota = quotaModule.useSmsQuota;
});

describe("ReplyComposer", () => {
  it("send button enabled when text non-empty and not blocked", () => {
    const { ReplyComposer: Composer } = require("./ReplyComposer");
    render(
      <Composer
        threadId="thread-001"
        customerId="customer-001"
        testID="composer"
      />,
      { wrapper: createWrapper() },
    );
    const input = screen.getByTestId("composer-text-input");
    fireEvent.changeText(input, "Hello there");
    const sendBtn = screen.getByTestId("send-button");
    expect(sendBtn.props.accessibilityState?.disabled).toBeFalsy();
  });

  it("send button disabled when text empty", () => {
    const { ReplyComposer: Composer } = require("./ReplyComposer");
    render(
      <Composer
        threadId="thread-001"
        customerId="customer-001"
        testID="composer"
      />,
      { wrapper: createWrapper() },
    );
    const sendBtn = screen.getByTestId("send-button");
    expect(sendBtn.props.accessibilityState?.disabled).toBe(true);
  });

  it("TCPA: send button disabled when isOptedOut=true — RULE 7 critical", () => {
    const { ReplyComposer: Composer } = require("./ReplyComposer");
    render(
      <Composer
        threadId="thread-003"
        customerId="customer-003"
        isOptedOut={true}
        testID="composer"
      />,
      { wrapper: createWrapper() },
    );
    const input = screen.getByTestId("composer-text-input");
    fireEvent.changeText(input, "Hello there");
    const sendBtn = screen.getByTestId("send-button");
    expect(sendBtn.props.accessibilityState?.disabled).toBe(true);
  });

  it("TCPA: opted-out banner shown when isOptedOut=true — RULE 7 critical", () => {
    const { ReplyComposer: Composer } = require("./ReplyComposer");
    render(
      <Composer
        threadId="thread-003"
        customerId="customer-003"
        isOptedOut={true}
        testID="composer"
      />,
      { wrapper: createWrapper() },
    );
    expect(screen.getByTestId("opted-out-banner")).toBeTruthy();
  });

  it("TCPA: NO force-send button exists when opted out — RULE 7 critical", () => {
    const { ReplyComposer: Composer } = require("./ReplyComposer");
    render(
      <Composer
        threadId="thread-003"
        customerId="customer-003"
        isOptedOut={true}
        testID="composer"
      />,
      { wrapper: createWrapper() },
    );
    // There should be EXACTLY ONE button that is the send button, and it must be disabled
    const sendBtn = screen.getByTestId("send-button");
    expect(sendBtn.props.accessibilityState?.disabled).toBe(true);
    // No "force send" or "override" buttons
    expect(screen.queryByText(/force send|override|send anyway/i)).toBeNull();
  });

  it("mic button transitions to recording state on press", () => {
    render(
      <ReplyComposer
        threadId="thread-001"
        customerId="customer-001"
        testID="composer"
      />,
      { wrapper: createWrapper() },
    );
    const micBtn = screen.getByTestId("mic-button");
    fireEvent.press(micBtn);
    expect(mockStartDictating).toHaveBeenCalled();
  });
});
