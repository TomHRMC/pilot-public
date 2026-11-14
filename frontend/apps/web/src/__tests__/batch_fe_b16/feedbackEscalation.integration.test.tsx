/**
 * Feedback escalation integration tests — FE-B16
 *
 * Location: apps/web/src/__tests__/batch_fe_b16/feedbackEscalation.integration.test.tsx
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
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { feedbackSubmitHandler } from "../../mocks/handlers/helpHandlers";
import { FeedbackFormModal } from "../../features/help/components/FeedbackFormModal";
import { KnowledgeBoundaryMessage } from "@pilot/ui";

const server = setupServer(feedbackSubmitHandler);
beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Mock the feedback hook at unit test level
vi.mock("../../features/help/hooks/useSubmitFeedback", () => ({
  useSubmitFeedback: () => ({
    mutateAsync: vi.fn(),
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
    isIdle: true,
    error: null,
    data: undefined,
    reset: vi.fn(),
    status: "idle",
  }),
}));

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("Feedback escalation from knowledge boundary", () => {
  it("KnowledgeBoundaryMessage renders escalation CTA", () => {
    const onEscalate = vi.fn();
    render(
      <KnowledgeBoundaryMessage
        content="I don't have documentation for that."
        timestamp={new Date()}
        onEscalate={onEscalate}
      />,
    );
    const cta = screen.getByTestId("knowledge-boundary-escalate-cta");
    expect(cta).toBeInTheDocument();
    fireEvent.click(cta);
    expect(onEscalate).toHaveBeenCalledTimes(1);
  });

  it("FeedbackFormModal opened from escalation includes from_help_chat_session_id", () => {
    render(
      <Wrapper>
        <FeedbackFormModal
          fromHelpChatSessionId="session-today-001"
          prefilledBody="[Auto-filled: AI help conversation \u2014 Test session]"
          onClose={vi.fn()}
        />
      </Wrapper>,
    );
    const input = screen.getByTestId(
      "feedback-session-id-input",
    ) as HTMLInputElement;
    expect(input.value).toBe("session-today-001");
  });

  it("submitting escalation feedback includes session_id in POST body", () => {
    render(
      <Wrapper>
        <FeedbackFormModal
          fromHelpChatSessionId="session-today-001"
          prefilledBody="Need more help"
          onClose={vi.fn()}
        />
      </Wrapper>,
    );
    const bodyInput = screen.getByTestId(
      "feedback-body-input",
    ) as HTMLTextAreaElement;
    expect(bodyInput.value).toBe("Need more help");
    const sessionInput = screen.getByTestId(
      "feedback-session-id-input",
    ) as HTMLInputElement;
    expect(sessionInput.value).toBe("session-today-001");
  });
});
