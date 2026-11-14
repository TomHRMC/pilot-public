/**
 * HelpDrawer unit tests — FE-B16
 *
 * Location: apps/web/src/__tests__/batch_fe_b16/helpDrawer.unit.test.tsx
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { HelpDrawerHeader } from "../../features/help/components/HelpDrawerHeader";

describe("HelpDrawerHeader", () => {
  it("renders header with correct title for chat view", () => {
    render(
      <HelpDrawerHeader
        view="chat"
        onClose={vi.fn()}
        onToggleHistory={vi.fn()}
      />,
    );
    expect(screen.getByText("Help")).toBeInTheDocument();
  });

  it("renders header with history title for history view", () => {
    render(
      <HelpDrawerHeader
        view="history"
        onClose={vi.fn()}
        onToggleHistory={vi.fn()}
      />,
    );
    expect(screen.getByText("Chat history")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", () => {
    const onClose = vi.fn();
    render(
      <HelpDrawerHeader
        view="chat"
        onClose={onClose}
        onToggleHistory={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("help-drawer-close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onToggleHistory when history icon is clicked", () => {
    const onToggle = vi.fn();
    render(
      <HelpDrawerHeader
        view="chat"
        onClose={vi.fn()}
        onToggleHistory={onToggle}
      />,
    );
    fireEvent.click(screen.getByTestId("help-history-toggle"));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("highlights history button when in history view", () => {
    render(
      <HelpDrawerHeader
        view="history"
        onClose={vi.fn()}
        onToggleHistory={vi.fn()}
      />,
    );
    const historyBtn = screen.getByTestId("help-history-toggle");
    expect(historyBtn.className).toContain("text-brand-600");
  });
});
