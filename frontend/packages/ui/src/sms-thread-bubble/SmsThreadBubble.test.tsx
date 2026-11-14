/**
 * SmsThreadBubble — unit tests (web variant)
 *
 * Location: packages/ui/src/sms-thread-bubble/SmsThreadBubble.test.tsx
 *
 * Tests per design doc G.1.
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SmsThreadBubble } from "./SmsThreadBubble";
import type { SmsMessage } from "./types";

// Mock PendingBadge to simplify assertions
vi.mock("../pending-badge/PendingBadge", () => ({
  PendingBadge: ({ variant, testID }: { variant: string; testID?: string }) => (
    <span data-testid={testID} data-variant={variant}>
      badge
    </span>
  ),
}));

const baseMessage: SmsMessage = {
  message_id: "msg-001",
  thread_id: "thread-001",
  direction: "outbound",
  channel: "sms",
  body: "Hello, this is a test message",
  segment_count: 1,
  status: "delivered",
  carrier_message_id: "carrier-001",
  composition_method: "free_form_text",
  template_id: null,
  voice_audio_id: null,
  sent_at: "2026-05-26T09:00:00Z",
  delivered_at: "2026-05-26T09:00:02Z",
  received_at: null,
  audit_user_id: "tech-001",
};

describe("SmsThreadBubble", () => {
  it("direction=outbound: renders right-aligned brand-indigo bubble", () => {
    const { container } = render(
      <SmsThreadBubble
        message={baseMessage}
        isOwnMessage={true}
        testID="bubble"
      />,
    );
    // Check right-aligned wrapper
    expect(container.querySelector(".flex.justify-end")).toBeTruthy();
    // Check brand bubble class
    expect(container.querySelector(".bg-brand-600.text-white")).toBeTruthy();
  });

  it("direction=inbound: renders left-aligned neutral bubble", () => {
    const inboundMessage: SmsMessage = {
      ...baseMessage,
      message_id: "msg-002",
      direction: "inbound",
      status: "received",
      sent_at: null,
      delivered_at: null,
      received_at: "2026-05-26T09:05:00Z",
    };
    const { container } = render(
      <SmsThreadBubble
        message={inboundMessage}
        isOwnMessage={false}
        testID="bubble-inbound"
      />,
    );
    expect(container.querySelector(".flex.justify-start")).toBeTruthy();
    expect(
      container.querySelector(".bg-neutral-100.text-neutral-900"),
    ).toBeTruthy();
  });

  it("status=pending_send: renders PendingBadge variant=pending", () => {
    const pendingMessage: SmsMessage = {
      ...baseMessage,
      status: "pending_send",
      sent_at: null,
      delivered_at: null,
    };
    render(
      <SmsThreadBubble
        message={pendingMessage}
        isOwnMessage={true}
        showDeliveryStatus
      />,
    );
    const badge = screen.getByTestId(
      `pending-badge-${pendingMessage.message_id}`,
    );
    expect(badge).toBeTruthy();
    expect(badge.getAttribute("data-variant")).toBe("pending");
  });

  it("status=delivered: renders delivery confirmation icon (✓)", () => {
    render(
      <SmsThreadBubble
        message={baseMessage}
        isOwnMessage={true}
        showDeliveryStatus
      />,
    );
    const checkmark = screen.getByTestId(`delivered-${baseMessage.message_id}`);
    expect(checkmark.textContent).toBe("✓");
  });

  it("status=failed: renders PendingBadge variant=failed", () => {
    const failedMessage: SmsMessage = {
      ...baseMessage,
      status: "failed",
    };
    render(
      <SmsThreadBubble
        message={failedMessage}
        isOwnMessage={true}
        showDeliveryStatus
      />,
    );
    const badge = screen.getByTestId(
      `failed-badge-${failedMessage.message_id}`,
    );
    expect(badge.getAttribute("data-variant")).toBe("failed");
  });

  it("showTimestamp=true: renders formatted relative timestamp", () => {
    const { container } = render(
      <SmsThreadBubble
        message={baseMessage}
        isOwnMessage={true}
        showTimestamp
      />,
    );
    // Should have a timestamp span (not empty)
    const captionSpans = container.querySelectorAll(".text-caption");
    expect(captionSpans.length).toBeGreaterThan(0);
  });

  it("isPending=true: renders pending badge", () => {
    render(
      <SmsThreadBubble
        message={{ ...baseMessage, status: "pending_send" }}
        isOwnMessage={true}
        isPending={true}
        showDeliveryStatus
      />,
    );
    const badge = screen.getByTestId(`pending-badge-${baseMessage.message_id}`);
    expect(badge).toBeTruthy();
  });

  it("body text is rendered inside the bubble", () => {
    render(<SmsThreadBubble message={baseMessage} isOwnMessage={true} />);
    expect(screen.getByText(baseMessage.body)).toBeTruthy();
  });

  // FE-B27: senderLabel tests
  it("test_sender_label_renders_outbound — senderLabel appears right-aligned below outbound bubble", () => {
    render(
      <SmsThreadBubble
        message={baseMessage}
        isOwnMessage={true}
        senderLabel="From: Jake"
      />,
    );
    const label = screen.getByTestId(`sender-label-${baseMessage.message_id}`);
    expect(label).toBeTruthy();
    expect(label.textContent).toBe("From: Jake");
    expect(label.className).toContain("text-right");
  });

  it("test_sender_label_renders_inbound — senderLabel appears left-aligned below inbound bubble", () => {
    const inboundMessage: SmsMessage = {
      ...baseMessage,
      message_id: "msg-inbound-001",
      direction: "inbound",
      status: "received",
      sent_at: null,
      delivered_at: null,
      received_at: "2026-07-11T10:00:00Z",
    };
    render(
      <SmsThreadBubble
        message={inboundMessage}
        isOwnMessage={false}
        senderLabel="From: John Smith"
      />,
    );
    const label = screen.getByTestId(
      `sender-label-${inboundMessage.message_id}`,
    );
    expect(label).toBeTruthy();
    expect(label.textContent).toBe("From: John Smith");
    expect(label.className).toContain("text-left");
  });

  it("test_sender_label_omitted — no sender label element in DOM when senderLabel not passed", () => {
    render(
      <SmsThreadBubble
        message={baseMessage}
        isOwnMessage={true}
        // senderLabel NOT passed
      />,
    );
    const label = document.querySelector(
      `[data-testid="sender-label-${baseMessage.message_id}"]`,
    );
    expect(label).toBeNull();
  });
});
