/**
 * VoiceApprovalHandler unit tests (web)
 *
 * Location: apps/web/src/features/voice-approval/__tests__/VoiceApprovalHandler.test.tsx
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import React from "react";
import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import {
  VoiceApprovalHandler,
  VoiceLineEditRefusal,
} from "../VoiceApprovalHandler";

const server = setupServer(
  http.post("/api/v1/quotes/:id/approve", () =>
    HttpResponse.json({
      id: "q1",
      status: "approved",
      quote_version_id: "qv-2",
      approved_at: new Date().toISOString(),
    }),
  ),
  http.post("/api/v1/quotes/:id/reject", () =>
    HttpResponse.json({
      id: "q1",
      status: "rejected",
      rejected_at: new Date().toISOString(),
    }),
  ),
  http.post("/api/v1/quotes/:id/kickback", () =>
    HttpResponse.json({
      id: "q1",
      status: "draft",
      kicked_back_at: new Date().toISOString(),
    }),
  ),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const baseProps = {
  quoteId: "q1",
  quoteNumber: "Q-001",
  customerName: "Johnson Electric",
  onIntentHandled: vi.fn(),
};

describe("VoiceApprovalHandler", () => {
  it("renders nothing when no intent", () => {
    const { container } = render(
      <VoiceApprovalHandler {...baseProps} detectedIntent={null} />,
      { wrapper },
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders VoiceConfirmTurn prompt for approve_quote intent", () => {
    render(
      <VoiceApprovalHandler {...baseProps} detectedIntent="approve_quote" />,
      { wrapper },
    );
    expect(
      screen.getByText(/approve quote #Q-001 for Johnson Electric/i),
    ).toBeTruthy();
  });

  it("renders prompt for reject_quote intent", () => {
    render(
      <VoiceApprovalHandler {...baseProps} detectedIntent="reject_quote" />,
      { wrapper },
    );
    expect(screen.getByText(/reject quote #Q-001/i)).toBeTruthy();
  });

  it("renders prompt for request_quote_edits intent", () => {
    render(
      <VoiceApprovalHandler
        {...baseProps}
        detectedIntent="request_quote_edits"
      />,
      { wrapper },
    );
    expect(screen.getByText(/kick back/i)).toBeTruthy();
  });

  it("calls onIntentHandled after cancel", () => {
    const onIntentHandled = vi.fn();
    render(
      <VoiceApprovalHandler
        {...baseProps}
        detectedIntent="approve_quote"
        onIntentHandled={onIntentHandled}
      />,
      { wrapper },
    );
    fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
    expect(onIntentHandled).toHaveBeenCalledOnce();
  });

  it("fires approve mutation on confirm and calls onIntentHandled", async () => {
    let approveCalled = false;
    server.use(
      http.post("/api/v1/quotes/:id/approve", () => {
        approveCalled = true;
        return HttpResponse.json({
          id: "q1",
          status: "approved",
          quote_version_id: "qv-2",
          approved_at: new Date().toISOString(),
        });
      }),
    );

    const onIntentHandled = vi.fn();
    render(
      <VoiceApprovalHandler
        {...baseProps}
        detectedIntent="approve_quote"
        onIntentHandled={onIntentHandled}
      />,
      { wrapper },
    );

    fireEvent.click(screen.getByTestId("voice-confirm-confirm-btn"));
    await waitFor(() => expect(approveCalled).toBe(true));
    await waitFor(() => expect(onIntentHandled).toHaveBeenCalledOnce());
  });
});

describe("VoiceLineEditRefusal", () => {
  it("renders refusal message without VoiceConfirmTurn", () => {
    render(<VoiceLineEditRefusal />);
    expect(screen.getByText(/voice can approve.*line edits/i)).toBeTruthy();
    expect(screen.queryByTestId("voice-confirm-confirm-btn")).toBeNull();
  });
});
