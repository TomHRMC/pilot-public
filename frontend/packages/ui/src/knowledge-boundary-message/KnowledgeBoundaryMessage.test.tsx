/**
 * KnowledgeBoundaryMessage unit tests — FE-B16
 *
 * Location: packages/ui/src/knowledge-boundary-message/KnowledgeBoundaryMessage.test.tsx
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { KnowledgeBoundaryMessage } from "./web/KnowledgeBoundaryMessage";

const CONTENT =
  "I don't have specific documentation on that topic in our help content.";
const TIMESTAMP = new Date("2026-05-27T14:30:00Z");

describe("KnowledgeBoundaryMessage (web)", () => {
  it("renders the AI response content", () => {
    render(
      <KnowledgeBoundaryMessage
        content={CONTENT}
        timestamp={TIMESTAMP}
        onEscalate={vi.fn()}
      />,
    );
    expect(screen.getByText(CONTENT)).toBeInTheDocument();
  });

  it("renders the escalation CTA", () => {
    render(
      <KnowledgeBoundaryMessage
        content={CONTENT}
        timestamp={TIMESTAMP}
        onEscalate={vi.fn()}
      />,
    );
    expect(
      screen.getByTestId("knowledge-boundary-escalate-cta"),
    ).toBeInTheDocument();
    expect(screen.getByText(/Didn't find what you needed/)).toBeInTheDocument();
  });

  it("calls onEscalate when CTA is clicked", () => {
    const onEscalate = vi.fn();
    render(
      <KnowledgeBoundaryMessage
        content={CONTENT}
        timestamp={TIMESTAMP}
        onEscalate={onEscalate}
      />,
    );
    fireEvent.click(screen.getByTestId("knowledge-boundary-escalate-cta"));
    expect(onEscalate).toHaveBeenCalledTimes(1);
  });

  it("applies alert-50 background token", () => {
    render(
      <KnowledgeBoundaryMessage
        content={CONTENT}
        timestamp={TIMESTAMP}
        onEscalate={vi.fn()}
      />,
    );
    const container = screen.getByTestId("knowledge-boundary-message");
    expect(container.className).toContain("bg-alert-50");
  });

  it("displays formatted timestamp", () => {
    render(
      <KnowledgeBoundaryMessage
        content={CONTENT}
        timestamp={TIMESTAMP}
        onEscalate={vi.fn()}
      />,
    );
    // Should render a formatted time string (HH:MM format)
    const container = screen.getByTestId("knowledge-boundary-message");
    expect(container.textContent).toMatch(/\d{1,2}:\d{2}/);
  });
});
