/**
 * Voice help flow integration tests — FE-B16
 *
 * Location: apps/web/src/__tests__/batch_fe_b16/voiceHelpFlow.integration.test.tsx
 *
 * RULE 1: Voice in help chat composes FE-B3 hooks only — no new WebSocket code.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { HelpChatMessages } from "@pilot/ui";

function Wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("Voice help flow \u2014 RULE 1 architecture compliance", () => {
  it("HelpChatMessages renders without any new WebSocket instantiation", () => {
    const wsConstructorSpy = vi
      .spyOn(global, "WebSocket")
      .mockImplementation(() => {
        throw new Error(
          "WebSocket should not be instantiated in HelpChatMessages",
        );
      });

    expect(() =>
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
      ),
    ).not.toThrow();

    wsConstructorSpy.mockRestore();
  });

  it("composer zone renders in the chat component", () => {
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
    expect(screen.getByTestId("help-composer")).toBeInTheDocument();
  });

  it("send button dispatches to onSendMessage (not a WebSocket send)", () => {
    const onSendMessage = vi.fn();
    render(
      <Wrapper>
        <HelpChatMessages
          session={null}
          messages={[]}
          isStreaming={false}
          isLoading={false}
          error={null}
          onSendMessage={onSendMessage}
          onFollowUpAction={vi.fn()}
          onEscalate={vi.fn()}
          onRequestTts={vi.fn()}
        />
      </Wrapper>,
    );
    fireEvent.change(screen.getByTestId("help-composer-input"), {
      target: { value: "Test question" },
    });
    fireEvent.click(screen.getByTestId("help-send-button"));
    expect(onSendMessage).toHaveBeenCalledWith("Test question", false);
  });
});
