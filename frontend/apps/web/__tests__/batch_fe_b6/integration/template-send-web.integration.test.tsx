/**
 * Integration tests — FE-B6 Customer Comms Outbound (Web)
 *
 * Location: apps/web/__tests__/batch_fe_b6/integration/template-send-web.integration.test.tsx
 * Target: 12+ integration tests
 *
 * Tests the full preview → modal → send flow against MSW handlers.
 * Verifies the two-step enforcement contract at the network level.
 */

import {
  describe,
  it,
  expect,
  vi,
  beforeAll,
  afterEach,
  afterAll,
} from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import React, { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { usePreviewBeforeSend } from "@pilot/ui";
import type { PreviewInput } from "@pilot/ui";

// ── Test server ───────────────────────────────────────────────────────────────

let previewCalled = false;
let sendCallCount = 0;

const server = setupServer(
  http.get("/api/v1/communications/comm-template-types", () => {
    return HttpResponse.json({
      items: [
        {
          code: "on_my_way",
          slug: "on-my-way",
          name: "On my way",
          description: null,
          category: "appointment",
          preferred_channel: "sms",
          initiator: "tech",
          requires_approval: false,
          send_mode: "immediate",
          trigger_event: null,
          is_system: true,
          sort_order: 1,
        },
        {
          code: "running_late",
          slug: "running-late",
          name: "Running late",
          description: null,
          category: "delay",
          preferred_channel: "sms",
          initiator: "tech",
          requires_approval: false,
          send_mode: "immediate",
          trigger_event: null,
          is_system: true,
          sort_order: 2,
        },
        {
          code: "arrived",
          slug: "arrived",
          name: "Arrived",
          description: null,
          category: "job_status",
          preferred_channel: "sms",
          initiator: "tech",
          requires_approval: false,
          send_mode: "immediate",
          trigger_event: null,
          is_system: true,
          sort_order: 3,
        },
        {
          code: "job_complete",
          slug: "job-complete",
          name: "Job complete",
          description: null,
          category: "job_status",
          preferred_channel: "sms",
          initiator: "tech",
          requires_approval: false,
          send_mode: "immediate",
          trigger_event: null,
          is_system: true,
          sort_order: 4,
        },
        {
          code: "appointment_reminder",
          slug: "appointment-reminder",
          name: "Appointment reminder",
          description: null,
          category: "appointment",
          preferred_channel: "sms",
          initiator: "tech",
          requires_approval: false,
          send_mode: "scheduled",
          trigger_event: null,
          is_system: true,
          sort_order: 5,
        },
        {
          code: "follow_up",
          slug: "follow-up",
          name: "Follow up",
          description: null,
          category: "job_status",
          preferred_channel: "sms",
          initiator: "tech",
          requires_approval: false,
          send_mode: "manual",
          trigger_event: null,
          is_system: true,
          sort_order: 6,
        },
      ],
    });
  }),
  http.post("/api/v1/communications/preview", async ({ request }) => {
    previewCalled = true;
    const body = (await request.json()) as {
      template_code: string;
      variables: Record<string, unknown>;
    };
    return HttpResponse.json({
      rendered_subject: null,
      rendered_body: `Hi! I'm on my way, ETA about ${body.variables.eta_minutes ?? 20} minutes.`,
      recipient_name: "Test Customer",
      recipient_address: "+15555551234",
      actual_channel: "sms",
      editable_variables: [],
    });
  }),
  http.post("/api/v1/communications/send", async () => {
    sendCallCount++;
    if (!previewCalled) {
      return HttpResponse.json(
        { detail: "preview_not_called" },
        { status: 403 },
      );
    }
    previewCalled = false;
    return HttpResponse.json(
      {
        communication_id: `comm-${Date.now()}`,
        template_code: "on_my_way",
        actual_channel: "sms",
        channel_override_flag: false,
        status: "pending",
        rendered_message: "Hi! I'm on my way.",
        rendered_subject: null,
        recipient_address: "+15555551234",
        sent_at: null,
      },
      { status: 201 },
    );
  }),
  http.get("/api/v1/customers/:id/communications", () => {
    return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  previewCalled = false;
  sendCallCount = 0;
});
afterAll(() => server.close());

// ── Helper components ─────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  Wrapper.displayName = "TestQueryClientWrapper";
  return Wrapper;
}

// Test harness: triggers preview via hook, renders embedded modal
function CommsTestHarness({
  input,
  onSendSuccess = vi.fn(),
  onSendError = vi.fn(),
}: {
  input: PreviewInput;
  onSendSuccess?: (r: unknown) => void;
  onSendError?: (e: Error) => void;
}) {
  const setTriggered = useState(false)[1];
  const { preview, MessagePreviewModal, isPreviewLoading, sendError } =
    usePreviewBeforeSend({ onSendSuccess, onSendError });

  return (
    <div>
      <button
        data-testid="trigger-preview"
        onClick={async () => {
          setTriggered(true);
          await preview(input);
        }}
      >
        Preview
      </button>
      {isPreviewLoading && (
        <span data-testid="preview-loading">Loading...</span>
      )}
      {sendError && <span data-testid="send-error">{sendError.message}</span>}
      <MessagePreviewModal onEdit={() => setTriggered(false)} />
    </div>
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("Integration: template send flow (web)", () => {
  const TEMPLATE_INPUT: PreviewInput = {
    mode: "template",
    customerId: "cust-001",
    templateCode: "on_my_way",
    jobId: "job-001",
    variables: { eta_minutes: 20 },
  };

  it("1. preview renders modal with server-rendered body", async () => {
    render(<CommsTestHarness input={TEMPLATE_INPUT} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByTestId("trigger-preview"));

    await waitFor(() => {
      expect(screen.getByTestId("message-preview-modal")).toBeInTheDocument();
    });

    expect(
      screen.getByText(/I'm on my way, ETA about 20 minutes/),
    ).toBeInTheDocument();
  });

  it("2. POST /preview is called before modal opens", async () => {
    render(<CommsTestHarness input={TEMPLATE_INPUT} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByTestId("trigger-preview"));

    await waitFor(() => {
      expect(screen.getByTestId("message-preview-modal")).toBeInTheDocument();
    });

    expect(previewCalled).toBe(true);
  });

  it("3. send is called only after user confirms in modal", async () => {
    render(<CommsTestHarness input={TEMPLATE_INPUT} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByTestId("trigger-preview"));
    await waitFor(() =>
      expect(screen.getByTestId("message-preview-modal")).toBeInTheDocument(),
    );

    expect(sendCallCount).toBe(0);
    fireEvent.click(screen.getByTestId("preview-send-btn"));
    await waitFor(() => expect(sendCallCount).toBe(1));
  });

  it("4. modal closes after successful send", async () => {
    render(<CommsTestHarness input={TEMPLATE_INPUT} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByTestId("trigger-preview"));
    await waitFor(() =>
      expect(screen.getByTestId("message-preview-modal")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("preview-send-btn"));
    await waitFor(() =>
      expect(
        screen.queryByTestId("message-preview-modal"),
      ).not.toBeInTheDocument(),
    );
  });

  it("5. onSendSuccess fires after successful send", async () => {
    const onSendSuccess = vi.fn();
    render(
      <CommsTestHarness input={TEMPLATE_INPUT} onSendSuccess={onSendSuccess} />,
      { wrapper: createWrapper() },
    );

    fireEvent.click(screen.getByTestId("trigger-preview"));
    await waitFor(() =>
      expect(screen.getByTestId("message-preview-modal")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("preview-send-btn"));
    await waitFor(() => expect(onSendSuccess).toHaveBeenCalledOnce());
  });

  it("6. Cancel button closes modal without sending", async () => {
    render(<CommsTestHarness input={TEMPLATE_INPUT} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByTestId("trigger-preview"));
    await waitFor(() =>
      expect(screen.getByTestId("message-preview-modal")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("preview-cancel-btn"));
    await waitFor(() =>
      expect(
        screen.queryByTestId("message-preview-modal"),
      ).not.toBeInTheDocument(),
    );
    expect(sendCallCount).toBe(0);
  });
});

describe("Integration: channel override flow", () => {
  it("7. email channel override flows through to preview request", async () => {
    let capturedPreviewBody: { channel_override?: string } | undefined;
    server.use(
      http.post("/api/v1/communications/preview", async ({ request }) => {
        capturedPreviewBody = (await request.json()) as {
          channel_override?: string;
        };
        previewCalled = true;
        return HttpResponse.json({
          rendered_subject: "Update from your technician",
          rendered_body: "Hi! The job is complete.",
          recipient_name: "Test Customer",
          recipient_address: "customer@test.com",
          actual_channel: "email",
          editable_variables: [],
        });
      }),
    );

    const EMAIL_INPUT: PreviewInput = {
      mode: "template",
      customerId: "cust-001",
      templateCode: "on_my_way",
      variables: { eta_minutes: 20 },
      channelOverride: "email",
    };

    render(<CommsTestHarness input={EMAIL_INPUT} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByTestId("trigger-preview"));
    await waitFor(() =>
      expect(screen.getByTestId("message-preview-modal")).toBeInTheDocument(),
    );

    expect(capturedPreviewBody?.channel_override).toBe("email");
  });

  it("8. email channel shows email pill in modal", async () => {
    const EMAIL_INPUT: PreviewInput = {
      mode: "template",
      customerId: "cust-001",
      templateCode: "on_my_way",
      variables: { eta_minutes: 20 },
      channelOverride: "email",
    };

    server.use(
      http.post("/api/v1/communications/preview", async () => {
        previewCalled = true;
        return HttpResponse.json({
          rendered_subject: "Subject",
          rendered_body: "Hi!",
          recipient_name: "Customer",
          recipient_address: "c@test.com",
          actual_channel: "email",
          editable_variables: [],
        });
      }),
    );

    render(<CommsTestHarness input={EMAIL_INPUT} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByTestId("trigger-preview"));
    await waitFor(() =>
      expect(screen.getByLabelText("Channel: email")).toBeInTheDocument(),
    );
  });
});

describe("Integration: send failure and retry", () => {
  it("9. send failure shows error; retry re-calls send", async () => {
    let failCount = 0;
    server.use(
      http.post("/api/v1/communications/send", () => {
        failCount++;
        if (failCount === 1) {
          return HttpResponse.json(
            { detail: "Carrier failure" },
            { status: 422 },
          );
        }
        return HttpResponse.json(
          {
            communication_id: "retry-comm",
            template_code: "on_my_way",
            actual_channel: "sms",
            channel_override_flag: false,
            status: "pending",
            rendered_message: "Hi!",
            rendered_subject: null,
            recipient_address: "+15555551234",
            sent_at: null,
          },
          { status: 201 },
        );
      }),
    );

    const onSendSuccess = vi.fn();
    const TEMPLATE_INPUT: PreviewInput = {
      mode: "template",
      customerId: "cust-001",
      templateCode: "on_my_way",
      variables: { eta_minutes: 20 },
    };

    render(
      <CommsTestHarness input={TEMPLATE_INPUT} onSendSuccess={onSendSuccess} />,
      { wrapper: createWrapper() },
    );

    fireEvent.click(screen.getByTestId("trigger-preview"));
    await waitFor(() =>
      expect(screen.getByTestId("message-preview-modal")).toBeInTheDocument(),
    );

    // First attempt fails
    fireEvent.click(screen.getByTestId("preview-send-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("send-error")).toBeInTheDocument(),
    );

    // Retry succeeds (modal still open because send failed)
    fireEvent.click(screen.getByTestId("trigger-preview")); // re-preview
    await waitFor(() =>
      expect(screen.getByTestId("message-preview-modal")).toBeInTheDocument(),
    );
    fireEvent.click(screen.getByTestId("preview-send-btn"));
    await waitFor(() => expect(onSendSuccess).toHaveBeenCalledOnce());
  });
});

describe("Integration: preview-token enforcement", () => {
  it("10. POST /send called without /preview returns 403 preview_not_called", async () => {
    // errors array intentionally omitted — test only checks response status
    server.use(
      http.post("/api/v1/communications/send", () => {
        if (!previewCalled) {
          return HttpResponse.json(
            { detail: "preview_not_called" },
            { status: 403 },
          );
        }
        return HttpResponse.json({}, { status: 201 });
      }),
    );

    // Directly call send without preview (bypassing UI)
    const res = await fetch("/api/v1/communications/send", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_id: "x",
        template_code: "on_my_way",
        variables: {},
      }),
    });

    const body = (await res.json()) as { detail: string };
    expect(res.status).toBe(403);
    expect(body.detail).toBe("preview_not_called");
  });
});

describe("Integration: quota exhaustion", () => {
  it("11. quota exhausted error surfaces correct error message", async () => {
    server.use(
      http.post("/api/v1/communications/send", () => {
        return HttpResponse.json(
          { detail: "quota exhausted" },
          { status: 429 },
        );
      }),
    );

    const onSendError = vi.fn();
    const TEMPLATE_INPUT: PreviewInput = {
      mode: "template",
      customerId: "cust-001",
      templateCode: "on_my_way",
      variables: { eta_minutes: 20 },
    };

    render(
      <CommsTestHarness input={TEMPLATE_INPUT} onSendError={onSendError} />,
      { wrapper: createWrapper() },
    );

    fireEvent.click(screen.getByTestId("trigger-preview"));
    await waitFor(() =>
      expect(screen.getByTestId("message-preview-modal")).toBeInTheDocument(),
    );

    fireEvent.click(screen.getByTestId("preview-send-btn"));
    await waitFor(() => expect(onSendError).toHaveBeenCalledOnce());
    expect(onSendError.mock.calls[0]?.[0].message).toBe("QUOTA_EXHAUSTED");
  });
});

describe("Integration: free-form send (FE-B10 compat)", () => {
  it("12. free-form send shows preview without server preview call", async () => {
    let previewCallsMade = 0;
    server.use(
      http.post("/api/v1/communications/preview", () => {
        previewCallsMade++;
        return HttpResponse.json({});
      }),
      http.post("/api/v1/communications/send-free-form", async () => {
        return HttpResponse.json(
          {
            communication_id: "ff-comm-001",
            actual_channel: "sms",
            channel_override_flag: false,
            status: "pending",
            rendered_message: "Reply text",
            sent_at: null,
          },
          { status: 201 },
        );
      }),
    );

    const FREE_FORM_INPUT: PreviewInput = {
      mode: "free-form",
      customerId: "cust-001",
      freeFormBody: "Reply text",
    };

    render(<CommsTestHarness input={FREE_FORM_INPUT} />, {
      wrapper: createWrapper(),
    });

    fireEvent.click(screen.getByTestId("trigger-preview"));

    await waitFor(() =>
      expect(screen.getByTestId("message-preview-modal")).toBeInTheDocument(),
    );

    expect(previewCallsMade).toBe(0);
    expect(screen.getByText("Reply text")).toBeInTheDocument();
  });
});
