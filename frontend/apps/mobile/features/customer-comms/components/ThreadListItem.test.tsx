/**
 * ThreadListItem — unit tests
 *
 * Location: apps/mobile/features/customer-comms/components/ThreadListItem.test.tsx
 *
 * Tests per design doc G.1.
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThreadListItem } from "./ThreadListItem";
import type { SmsThreadListItem } from "@pilot/ui";

const baseThread: SmsThreadListItem = {
  thread_id: "thread-001",
  customer_id: "customer-001",
  customer_name: "John Smith",
  last_message_preview: "On my way — ETA 10 mins.",
  last_message_at: new Date(Date.now() - 60_000).toISOString(), // 1 min ago
  last_message_direction: "outbound",
  unread_count: 0,
  originating_job_id: "job-001",
  originating_job_display: "Job #1042 — Panel Upgrade",
  customer_sms_opted_out: false,
};

describe("ThreadListItem", () => {
  it("renders customer name, preview, relative time", () => {
    const onPress = jest.fn();
    render(
      <ThreadListItem
        thread={baseThread}
        onPress={onPress}
        testID="thread-item"
      />,
    );
    expect(screen.getByText("John Smith")).toBeTruthy();
    expect(screen.getByText(/on my way/i)).toBeTruthy();
    expect(screen.getByText(/1m|just now/i)).toBeTruthy();
  });

  it("with unread_count=2: renders unread badge", () => {
    const threadWithUnread: SmsThreadListItem = {
      ...baseThread,
      thread_id: "thread-002",
      unread_count: 2,
    };
    render(<ThreadListItem thread={threadWithUnread} onPress={jest.fn()} />);
    expect(
      screen.getByTestId(`unread-badge-${threadWithUnread.thread_id}`),
    ).toBeTruthy();
    expect(screen.getByText("2")).toBeTruthy();
  });

  it("with unread_count=0: no unread badge rendered", () => {
    render(<ThreadListItem thread={baseThread} onPress={jest.fn()} />);
    expect(
      screen.queryByTestId(`unread-badge-${baseThread.thread_id}`),
    ).toBeNull();
  });

  it("opted-out thread shows opt-out indicator", () => {
    const optedOutThread: SmsThreadListItem = {
      ...baseThread,
      thread_id: "thread-opt",
      customer_sms_opted_out: true,
    };
    render(<ThreadListItem thread={optedOutThread} onPress={jest.fn()} />);
    expect(
      screen.getByTestId(`opted-out-${optedOutThread.thread_id}`),
    ).toBeTruthy();
  });

  it("tap calls onPress with thread_id", () => {
    const onPress = jest.fn();
    render(
      <ThreadListItem
        thread={baseThread}
        onPress={onPress}
        testID="thread-item"
      />,
    );
    fireEvent.press(screen.getByTestId("thread-item"));
    expect(onPress).toHaveBeenCalledWith(baseThread.thread_id);
  });

  it("outbound last message shows 'You: ' prefix", () => {
    render(
      <ThreadListItem
        thread={{ ...baseThread, last_message_direction: "outbound" }}
        onPress={jest.fn()}
      />,
    );
    expect(screen.getByText(/you: on my way/i)).toBeTruthy();
  });
});
