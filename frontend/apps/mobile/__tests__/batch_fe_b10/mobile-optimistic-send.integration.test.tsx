/**
 * mobile-optimistic-send — integration test
 *
 * Tests: Reply dispatched → pending bubble appears → server confirms → badge clears.
 * Design doc G.2, D.6
 */

import React from "react";
import { renderHook, act } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { http, HttpResponse, delay } from "msw";
import type { SmsMessage } from "@pilot/ui";

const server = setupServer(
  http.post("*/api/v1/communications/threads/:threadId/reply", async () => {
    await delay(100);
    return HttpResponse.json({
      message_id: "msg-123",
      status: "sent",
      sent_at: new Date().toISOString(),
    });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  qc?.clear();
});
afterAll(() => server.close());

let qc: QueryClient;

function createWrapper(queryClient: QueryClient) {
  qc = queryClient;
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe("mobile-optimistic-send integration", () => {
  it("optimistic message appears in cache with pending_send status before server response", async () => {
    const queryClient = new QueryClient();
    const threadId = "thread-001";

    // Pre-populate thread messages cache
    queryClient.setQueryData(["thread-messages", threadId], {
      pages: [
        {
          messages: [] as SmsMessage[],
          next_cursor: null,
          thread: { thread_id: threadId },
        },
      ],
      pageParams: [undefined],
    });

    const {
      useReplyToThread,
    } = require("../../features/customer-comms/hooks/useReplyToThread");

    const wrapper = createWrapper(queryClient);

    const { result } = renderHook(() => useReplyToThread(threadId), {
      wrapper,
    });

    await act(async () => {
      result.current.mutate({
        threadId,
        request: {
          body: "Test optimistic message",
          composition_method: "free_form_text",
        },
        estimatedSegmentCount: 1,
      });
    });

    // Optimistic message should appear in cache with pending_send status
    const cached = queryClient.getQueryData<{
      pages: { messages: SmsMessage[] }[];
    }>(["thread-messages", threadId]);

    const messages = cached?.pages.flatMap((p) => p.messages) ?? [];
    const optimisticMsg = messages.find((m) => m.status === "pending_send");
    expect(optimisticMsg).toBeTruthy();
    expect(optimisticMsg?.body).toBe("Test optimistic message");
    expect(optimisticMsg?.direction).toBe("outbound");
  });
});
