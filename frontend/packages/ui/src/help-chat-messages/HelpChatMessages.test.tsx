/**
 * HelpChatMessages unit tests — FE-B16
 *
 * Location: packages/ui/src/help-chat-messages/HelpChatMessages.test.tsx
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { HelpChatMessages } from "./web/HelpChatMessages";
import type { HelpChatMessage, HelpChatSession } from "./types";

const mockSession: HelpChatSession = {
  session_id: "session-001",
  title: "Test session",
  started_at: new Date().toISOString(),
  last_activity_at: new Date().toISOString(),
  message_count: 2,
  outcome: null,
};

const userMessage: HelpChatMessage = {
  message_id: "msg-001",
  session_id: "session-001",
  role: "user",
  content: "How do I connect QuickBooks?",
  created_at: new Date().toISOString(),
  context_payload: null,
  voice_used: false,
  is_knowledge_boundary: false,
};

const aiMessage: HelpChatMessage = {
  message_id: "msg-002",
  session_id: "session-001",
  role: "assistant",
  content: "Go to Settings → Integrations → QuickBooks.",
  created_at: new Date().toISOString(),
  context_payload: null,
  retrieved_article_ids: ["article-qb-001"],
  voice_used: false,
  is_knowledge_boundary: false,
};

const boundaryMessage: HelpChatMessage = {
  message_id: "msg-003",
  session_id: "session-001",
  role: "assistant",
  content: "I don't have specific documentation on that topic.",
  created_at: new Date().toISOString(),
  context_payload: null,
  retrieved_article_ids: [],
  voice_used: false,
  is_knowledge_boundary: true,
};

const defaultProps = {
  session: mockSession,
  messages: [],
  isStreaming: false,
  isLoading: false,
  error: null,
  onSendMessage: vi.fn(),
  onFollowUpAction: vi.fn(),
  onEscalate: vi.fn(),
  onRequestTts: vi.fn(),
};

describe("HelpChatMessages (web)", () => {
  it("renders empty state when no messages", () => {
    render(<HelpChatMessages {...defaultProps} messages={[]} />);
    expect(screen.getByTestId("help-empty-state")).toBeInTheDocument();
    expect(
      screen.getByText(/Hi! What can I help you with/),
    ).toBeInTheDocument();
  });

  it("renders user message bubble with correct testid", () => {
    render(<HelpChatMessages {...defaultProps} messages={[userMessage]} />);
    expect(screen.getByTestId("help-message-user")).toBeInTheDocument();
    expect(
      screen.getByText("How do I connect QuickBooks?"),
    ).toBeInTheDocument();
  });

  it("renders AI message bubble with correct testid", () => {
    render(<HelpChatMessages {...defaultProps} messages={[aiMessage]} />);
    expect(screen.getByTestId("help-message-assistant")).toBeInTheDocument();
    expect(
      screen.getByText("Go to Settings → Integrations → QuickBooks."),
    ).toBeInTheDocument();
  });

  it("renders KnowledgeBoundaryMessage when is_knowledge_boundary is true", () => {
    render(<HelpChatMessages {...defaultProps} messages={[boundaryMessage]} />);
    expect(
      screen.getByTestId("knowledge-boundary-message"),
    ).toBeInTheDocument();
    // Must NOT render the standard assistant bubble
    expect(
      screen.queryByTestId("help-message-assistant"),
    ).not.toBeInTheDocument();
  });

  it("renders streaming typing indicator when isStreaming is true", () => {
    render(<HelpChatMessages {...defaultProps} isStreaming={true} />);
    expect(screen.getByTestId("help-typing-indicator")).toBeInTheDocument();
  });

  it("does not render typing indicator when not streaming", () => {
    render(<HelpChatMessages {...defaultProps} isStreaming={false} />);
    expect(
      screen.queryByTestId("help-typing-indicator"),
    ).not.toBeInTheDocument();
  });

  it("renders the composer zone", () => {
    render(<HelpChatMessages {...defaultProps} />);
    expect(screen.getByTestId("help-composer")).toBeInTheDocument();
    expect(screen.getByTestId("help-composer-input")).toBeInTheDocument();
  });

  it("calls onSendMessage when Send is clicked with text", () => {
    const onSendMessage = vi.fn();
    render(
      <HelpChatMessages {...defaultProps} onSendMessage={onSendMessage} />,
    );
    const input = screen.getByTestId("help-composer-input");
    fireEvent.change(input, { target: { value: "My question" } });
    fireEvent.click(screen.getByTestId("help-send-button"));
    expect(onSendMessage).toHaveBeenCalledWith("My question", false);
  });

  it("send button is disabled when input is empty", () => {
    render(<HelpChatMessages {...defaultProps} />);
    expect(screen.getByTestId("help-send-button")).toBeDisabled();
  });

  it("renders anonymization notice", () => {
    render(<HelpChatMessages {...defaultProps} />);
    expect(screen.getByTestId("help-anonymization-notice")).toBeInTheDocument();
    expect(
      screen.getByText(/Personal info is removed before use/),
    ).toBeInTheDocument();
  });

  it("renders follow-up action buttons on AI messages", () => {
    render(<HelpChatMessages {...defaultProps} messages={[aiMessage]} />);
    expect(screen.getByText("Read full article")).toBeInTheDocument();
    expect(screen.getByText("Walk me through it")).toBeInTheDocument();
    expect(screen.getByText("✓ That answered it")).toBeInTheDocument();
  });

  it("calls onFollowUpAction when a follow-up button is clicked", () => {
    const onFollowUpAction = vi.fn();
    render(
      <HelpChatMessages
        {...defaultProps}
        messages={[aiMessage]}
        onFollowUpAction={onFollowUpAction}
      />,
    );
    fireEvent.click(screen.getByText("✓ That answered it"));
    expect(onFollowUpAction).toHaveBeenCalledWith(
      "that_answered_it",
      aiMessage,
    );
  });

  // RULE 2 verification: no MessagePreviewModal in this component
  it("does not import or use MessagePreviewModal", () => {
    // This test verifies the rendered output never contains preview modal elements
    render(
      <HelpChatMessages
        {...defaultProps}
        messages={[userMessage, aiMessage]}
      />,
    );
    expect(
      screen.queryByTestId("message-preview-modal"),
    ).not.toBeInTheDocument();
    expect(screen.queryByText("Preview message")).not.toBeInTheDocument();
  });
});
