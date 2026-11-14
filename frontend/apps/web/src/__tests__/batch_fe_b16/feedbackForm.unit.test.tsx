/**
 * FeedbackFormModal unit tests — FE-B16
 *
 * Location: apps/web/src/__tests__/batch_fe_b16/feedbackForm.unit.test.tsx
 *
 * Unit tests mock the mutation hook directly (network layer is tested
 * in the integration suite feedbackEscalation.integration.test.tsx).
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FeedbackFormModal } from "../../features/help/components/FeedbackFormModal";

// Mock the feedback hook at the unit test level — network is tested in integration suite
const mockMutateAsync = vi.fn();
const mockMutationState = {
  mutateAsync: mockMutateAsync,
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  isSuccess: false,
  isIdle: true,
  error: null,
  data: undefined,
  reset: vi.fn(),
  status: "idle" as const,
  variables: undefined,
  submittedAt: 0,
  failureCount: 0,
  failureReason: null,
  context: undefined,
  isPaused: false,
};

vi.mock("../../features/help/hooks/useSubmitFeedback", () => ({
  useSubmitFeedback: () => mockMutationState,
}));

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("FeedbackFormModal", () => {
  it("renders category radio options", () => {
    render(
      <Wrapper>
        <FeedbackFormModal onClose={vi.fn()} />
      </Wrapper>,
    );
    expect(screen.getByTestId("feedback-category-bug")).toBeInTheDocument();
    expect(
      screen.getByTestId("feedback-category-feature_request"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("feedback-category-question"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("feedback-category-general")).toBeInTheDocument();
  });

  it("submit button is present in the form", () => {
    render(
      <Wrapper>
        <FeedbackFormModal onClose={vi.fn()} />
      </Wrapper>,
    );
    expect(screen.getByTestId("feedback-submit-btn")).toBeInTheDocument();
  });

  it("shows confirmation banner when mutation is in success state", () => {
    // Render the modal with the hook reporting success
    vi.mocked(mockMutationState).isSuccess = true;
    vi.mocked(mockMutationState).data = {
      submission_id: "sub-001",
      category: "general",
      submitted_at: new Date().toISOString(),
      confirmation_message: "Thanks for your feedback!",
    } as never;

    render(
      <Wrapper>
        <FeedbackFormModal onClose={vi.fn()} />
      </Wrapper>,
    );
    expect(screen.getByTestId("feedback-success-banner")).toBeInTheDocument();

    // Reset for other tests
    vi.mocked(mockMutationState).isSuccess = false;
    vi.mocked(mockMutationState).data = undefined;
  });

  it("threads from_help_chat_session_id when escalating from chat", () => {
    render(
      <Wrapper>
        <FeedbackFormModal
          fromHelpChatSessionId="session-today-001"
          prefilledBody="[Auto-filled: AI help conversation — Test session]"
          onClose={vi.fn()}
        />
      </Wrapper>,
    );
    const sessionInput = screen.getByTestId(
      "feedback-session-id-input",
    ) as HTMLInputElement;
    expect(sessionInput.value).toBe("session-today-001");
  });

  it("pre-fills body when escalating from chat", () => {
    const prefilledBody =
      "[Auto-filled: AI help conversation — Test session]\n\nNotes here";
    render(
      <Wrapper>
        <FeedbackFormModal
          fromHelpChatSessionId="session-today-001"
          prefilledBody={prefilledBody}
          onClose={vi.fn()}
        />
      </Wrapper>,
    );
    const bodyInput = screen.getByTestId(
      "feedback-body-input",
    ) as HTMLTextAreaElement;
    expect(bodyInput.value).toBe(prefilledBody);
  });

  it("calls onClose when modal close button is clicked", () => {
    const onClose = vi.fn();
    render(
      <Wrapper>
        <FeedbackFormModal onClose={onClose} />
      </Wrapper>,
    );
    fireEvent.click(screen.getByTestId("feedback-modal-close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
