/**
 * Unit tests — usePreviewBeforeSend hook
 *
 * Location: apps/web/__tests__/batch_fe_b6/unit/usePreviewBeforeSend.test.ts
 * Target: 20 unit tests covering hook contract enforcement
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
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { createElement } from "react";
import type { ReactNode } from "react";
import { usePreviewBeforeSend } from "@pilot/ui";
import type { PreviewInput } from "@pilot/ui";

// ── Test server ───────────────────────────────────────────────────────────────

const PREVIEW_RESPONSE = {
  rendered_subject: null,
  rendered_body: "Hi! I'm on my way, ETA about 20 minutes.",
  recipient_name: "Test Customer",
  recipient_address: "+15555551234",
  actual_channel: "sms",
  editable_variables: [
    {
      name: "eta_minutes",
      value: 20,
      label: "ETA (minutes)",
      type: "time_minutes",
    },
  ],
};

const SEND_RESPONSE = {
  communication_id: "comm-test-001",
  template_code: "on_my_way",
  actual_channel: "sms",
  channel_override_flag: false,
  status: "pending",
  rendered_message: "Hi! I'm on my way, ETA about 20 minutes.",
  rendered_subject: null,
  recipient_address: "+15555551234",
  sent_at: null,
};

let previewServerCalled = false;

const server = setupServer(
  http.post("/api/v1/communications/preview", () => {
    previewServerCalled = true;
    return HttpResponse.json(PREVIEW_RESPONSE);
  }),
  http.post("/api/v1/communications/send", () => {
    if (!previewServerCalled) {
      return HttpResponse.json(
        { detail: "preview_not_called" },
        { status: 403 },
      );
    }
    return HttpResponse.json(SEND_RESPONSE, { status: 201 });
  }),
  http.get("/api/v1/customers/:id/communications", () => {
    return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20 });
  }),
);

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  previewServerCalled = false;
});
afterAll(() => server.close());

// ── Helper ────────────────────────────────────────────────────────────────────

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const Wrapper = ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
  Wrapper.displayName = "TestQueryClientWrapper";
  return Wrapper;
}

const TEMPLATE_INPUT: PreviewInput = {
  mode: "template",
  customerId: "cust-001",
  templateCode: "on_my_way",
  jobId: "job-001",
  variables: { eta_minutes: 20 },
};

const FREE_FORM_INPUT: PreviewInput = {
  mode: "free-form",
  customerId: "cust-001",
  freeFormBody: "I'm on my way!",
};

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("usePreviewBeforeSend — initial state", () => {
  it("1. initial state: previewData is null, isModalOpen is false", () => {
    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });
    expect(result.current.previewData).toBeNull();
    expect(result.current.isModalOpen).toBe(false);
    expect(result.current.isPreviewLoading).toBe(false);
    expect(result.current.isSending).toBe(false);
  });
});

describe("usePreviewBeforeSend — preview()", () => {
  it("2. preview() calls POST /preview with correct payload", async () => {
    let capturedBody: unknown;
    server.use(
      http.post("/api/v1/communications/preview", async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json(PREVIEW_RESPONSE);
      }),
    );

    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });

    expect(capturedBody).toMatchObject({
      customer_id: "cust-001",
      template_code: "on_my_way",
      variables: { eta_minutes: 20 },
    });
  });

  it("3. preview() populates previewData after successful call", async () => {
    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });

    expect(result.current.previewData).not.toBeNull();
    expect(result.current.previewData?.rendered_body).toBe(
      PREVIEW_RESPONSE.rendered_body,
    );
  });

  it("4. preview() sets isModalOpen to true", async () => {
    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });

    expect(result.current.isModalOpen).toBe(true);
  });

  it("5. free-form mode synthesizes previewData locally — no server call", async () => {
    let previewCallCount = 0;
    server.use(
      http.post("/api/v1/communications/preview", () => {
        previewCallCount++;
        return HttpResponse.json(PREVIEW_RESPONSE);
      }),
    );

    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview(FREE_FORM_INPUT);
    });

    expect(previewCallCount).toBe(0);
    expect(result.current.previewData?.rendered_body).toBe("I'm on my way!");
    expect(result.current.isModalOpen).toBe(true);
  });

  it("6. free-form preview sets actual_channel from channelOverride", async () => {
    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview({
        mode: "free-form",
        customerId: "cust-001",
        freeFormBody: "Test message",
        channelOverride: "email",
      });
    });

    expect(result.current.previewData?.actual_channel).toBe("email");
  });
});

describe("usePreviewBeforeSend — send() enforcement", () => {
  it("7. send() throws if called before preview()", async () => {
    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await expect(async () => {
      await result.current.send();
    }).rejects.toThrow("send() called before preview()");
  });

  it("8. send() succeeds after preview()", async () => {
    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });

    previewServerCalled = true;
    let sendResult: unknown;
    await act(async () => {
      sendResult = await result.current.send();
    });

    expect(sendResult).toMatchObject({ communication_id: "comm-test-001" });
  });

  it("9. previewToken resets after closeModal() — subsequent send() throws", async () => {
    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });
    expect(result.current.isModalOpen).toBe(true);

    act(() => result.current.closeModal());

    expect(result.current.isModalOpen).toBe(false);
    expect(result.current.previewData).toBeNull();

    await expect(async () => {
      await result.current.send();
    }).rejects.toThrow("send() called before preview()");
  });

  it("10. channelOverride flows through to preview request", async () => {
    let capturedBody: { channel_override?: string } | undefined;
    server.use(
      http.post("/api/v1/communications/preview", async ({ request }) => {
        capturedBody = (await request.json()) as { channel_override?: string };
        return HttpResponse.json({
          ...PREVIEW_RESPONSE,
          actual_channel: "email",
        });
      }),
    );

    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview({
        ...TEMPLATE_INPUT,
        channelOverride: "email",
      });
    });

    expect(capturedBody?.channel_override).toBe("email");
  });
});

describe("usePreviewBeforeSend — callbacks", () => {
  it("11. onSendSuccess fires on 201 response", async () => {
    previewServerCalled = true;
    const onSendSuccess = vi.fn();

    const { result } = renderHook(
      () => usePreviewBeforeSend({ onSendSuccess }),
      { wrapper: createWrapper() },
    );

    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });

    await act(async () => {
      await result.current.send();
    });

    expect(onSendSuccess).toHaveBeenCalledOnce();
    expect(onSendSuccess).toHaveBeenCalledWith(
      expect.objectContaining({ communication_id: "comm-test-001" }),
    );
  });

  it("12. onSendError fires on 422 response", async () => {
    previewServerCalled = true;
    const onSendError = vi.fn();

    server.use(
      http.post("/api/v1/communications/send", () => {
        return HttpResponse.json(
          { detail: "Carrier failure" },
          { status: 422 },
        );
      }),
    );

    const { result } = renderHook(() => usePreviewBeforeSend({ onSendError }), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });

    await act(async () => {
      try {
        await result.current.send();
      } catch {
        // expected
      }
    });

    expect(onSendError).toHaveBeenCalledOnce();
  });
});

describe("usePreviewBeforeSend — send results & errors", () => {
  it("13. sendResult is populated after successful send", async () => {
    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });

    previewServerCalled = true;
    await act(async () => {
      await result.current.send();
    });

    expect(result.current.sendResult).not.toBeNull();
  });

  it("14. sendError is populated after send failure", async () => {
    server.use(
      http.post("/api/v1/communications/send", () => {
        return HttpResponse.json({ detail: "Server error" }, { status: 500 });
      }),
    );

    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });

    previewServerCalled = true;
    await act(async () => {
      try {
        await result.current.send();
      } catch {
        // expected
      }
    });

    expect(result.current.sendError).not.toBeNull();
  });

  it("15. previewToken retained on send failure — retry possible", async () => {
    server.use(
      http.post("/api/v1/communications/send", () => {
        return HttpResponse.json({ detail: "Failure" }, { status: 422 });
      }),
    );

    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });

    previewServerCalled = true;
    await act(async () => {
      try {
        await result.current.send();
      } catch {
        // expected
      }
    });

    // Retry server responds OK
    server.use(
      http.post("/api/v1/communications/send", () => {
        return HttpResponse.json(SEND_RESPONSE, { status: 201 });
      }),
    );

    // Should NOT throw (token retained on failure)
    await act(async () => {
      await result.current.send();
    });

    expect(result.current.sendResult).not.toBeNull();
  });

  it("16. quota exhaustion error surfaces as QUOTA_EXHAUSTED", async () => {
    server.use(
      http.post("/api/v1/communications/send", () => {
        return HttpResponse.json(
          { detail: "quota exhausted" },
          { status: 429 },
        );
      }),
    );

    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });

    previewServerCalled = true;
    await act(async () => {
      try {
        await result.current.send();
      } catch {
        // expected
      }
    });

    expect(result.current.sendError?.message).toBe("QUOTA_EXHAUSTED");
  });

  it("17. modal closes after successful send", async () => {
    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });

    expect(result.current.isModalOpen).toBe(true);
    previewServerCalled = true;

    await act(async () => {
      await result.current.send();
    });

    expect(result.current.isModalOpen).toBe(false);
  });

  it("18. closeModal() resets previewData and sendError", async () => {
    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });

    expect(result.current.previewData).not.toBeNull();

    act(() => result.current.closeModal());

    expect(result.current.previewData).toBeNull();
    expect(result.current.sendError).toBeNull();
  });

  it("19. sendResult resets to null after new preview() call", async () => {
    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    // First send
    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });
    previewServerCalled = true;
    await act(async () => {
      await result.current.send();
    });
    expect(result.current.sendResult).not.toBeNull();

    // Second preview resets sendResult
    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });

    expect(result.current.sendResult).toBeNull();
  });

  it("20. isSending returns to false after send completes", async () => {
    const { result } = renderHook(() => usePreviewBeforeSend(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.preview(TEMPLATE_INPUT);
    });

    previewServerCalled = true;
    await act(async () => {
      await result.current.send();
    });

    expect(result.current.isSending).toBe(false);
  });
});
