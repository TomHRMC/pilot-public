/**
 * Help chat full flow integration tests — FE-B16
 *
 * Location: apps/web/src/__tests__/batch_fe_b16/helpChatFull.integration.test.tsx
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { setupServer } from "msw/node";
import { helpChatNormalHandler } from "../../mocks/handlers/helpHandlers";

const server = setupServer(helpChatNormalHandler);
beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

vi.mock("../../features/help/store/helpPanelStore", () => ({
  useHelpPanel: () => ({
    isOpen: true,
    view: "chat",
    context: null,
    activeSessionId: null,
    open: vi.fn(),
    close: vi.fn(),
    toggle: vi.fn(),
    openWithContext: vi.fn(),
    clearContext: vi.fn(),
    setActiveSession: vi.fn(),
    setView: vi.fn(),
  }),
}));

vi.mock("../../features/help/hooks/useHelpSessions", () => ({
  useHelpSessions: () => ({ groups: [], isLoading: false, error: null }),
}));

vi.mock("../../features/help/hooks/useHelpSessionFeedback", () => ({
  useHelpSessionFeedback: () => ({ mutate: vi.fn() }),
}));

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

import { HelpChatMessages } from "@pilot/ui";
import type { HelpChatMessage, HelpChatSession } from "@pilot/ui";

const session: HelpChatSession = {
  session_id: "session-001",
  title: "Test session",
  started_at: new Date().toISOString(),
  last_activity_at: new Date().toISOString(),
  message_count: 0,
  outcome: null,
};

describe("Help chat full flow integration", () => {
  it("renders empty chat with initial empty state", () => {
    render(
      <Wrapper>
        <HelpChatMessages
          session={null}
          messages={[]}
          isStreaming={false}
          isLoading={false}
          error={null}
          onSendMessage={vi.fn()}
          onFollowUpAction={vi.fn()}
          onEscalate={vi.fn()}
          onRequestTts={vi.fn()}
        />
      </Wrapper>,
    );
    expect(screen.getByTestId("help-empty-state")).toBeInTheDocument();
  });

  it("renders a user message after adding it to messages array", () => {
    const messages: HelpChatMessage[] = [
      {
        message_id: "msg-1",
        session_id: "session-001",
        role: "user",
        content: "How do I set up QuickBooks?",
        created_at: new Date().toISOString(),
        context_payload: null,
        voice_used: false,
        is_knowledge_boundary: false,
      },
    ];
    render(
      <Wrapper>
        <HelpChatMessages
          session={session}
          messages={messages}
          isStreaming={false}
          isLoading={false}
          error={null}
          onSendMessage={vi.fn()}
          onFollowUpAction={vi.fn()}
          onEscalate={vi.fn()}
          onRequestTts={vi.fn()}
        />
      </Wrapper>,
    );
    expect(screen.getByText("How do I set up QuickBooks?")).toBeInTheDocument();
    expect(screen.getByTestId("help-message-user")).toBeInTheDocument();
  });

  it("renders AI response after messages include assistant message", () => {
    const messages: HelpChatMessage[] = [
      {
        message_id: "msg-1",
        session_id: "session-001",
        role: "user",
        content: "How do I set up QuickBooks?",
        created_at: new Date().toISOString(),
        context_payload: null,
        voice_used: false,
        is_knowledge_boundary: false,
      },
      {
        message_id: "msg-2",
        session_id: "session-001",
        role: "assistant",
        content: "Go to Settings \u2192 Integrations \u2192 QuickBooks.",
        created_at: new Date().toISOString(),
        context_payload: null,
        retrieved_article_ids: ["article-qb"],
        voice_used: false,
        is_knowledge_boundary: false,
      },
    ];
    render(
      <Wrapper>
        <HelpChatMessages
          session={session}
          messages={messages}
          isStreaming={false}
          isLoading={false}
          error={null}
          onSendMessage={vi.fn()}
          onFollowUpAction={vi.fn()}
          onEscalate={vi.fn()}
          onRequestTts={vi.fn()}
        />
      </Wrapper>,
    );
    expect(screen.getByTestId("help-message-assistant")).toBeInTheDocument();
  });

  it("streaming state shows typing indicator", () => {
    render(
      <Wrapper>
        <HelpChatMessages
          session={session}
          messages={[
            {
              message_id: "msg-1",
              session_id: "session-001",
              role: "user",
              content: "Hello",
              created_at: new Date().toISOString(),
              context_payload: null,
              voice_used: false,
              is_knowledge_boundary: false,
            },
          ]}
          isStreaming={true}
          isLoading={false}
          error={null}
          onSendMessage={vi.fn()}
          onFollowUpAction={vi.fn()}
          onEscalate={vi.fn()}
          onRequestTts={vi.fn()}
        />
      </Wrapper>,
    );
    expect(screen.getByTestId("help-typing-indicator")).toBeInTheDocument();
  });
});
