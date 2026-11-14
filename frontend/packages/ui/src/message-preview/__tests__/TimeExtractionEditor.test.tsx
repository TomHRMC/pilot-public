/**
 * Unit tests — TimeExtractionEditor
 *
 * Location: packages/ui/src/message-preview/__tests__/TimeExtractionEditor.test.tsx
 * Runs in @pilot/ui vitest environment (React Native via jsdom stub).
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import "@testing-library/jest-dom";
import React from "react";
import { TimeExtractionEditor } from "../TimeExtractionEditor";

describe("TimeExtractionEditor — rendering", () => {
  it("1. renders with initial extracted minutes", () => {
    render(
      <TimeExtractionEditor
        initialMinutes={20}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByText("AI extracted: 20 min")).toBeInTheDocument();
  });

  it("2. renders all 6 quick-pick chips", () => {
    render(
      <TimeExtractionEditor
        initialMinutes={20}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByTestId("eta-chip-5")).toBeInTheDocument();
    expect(screen.getByTestId("eta-chip-10")).toBeInTheDocument();
    expect(screen.getByTestId("eta-chip-15")).toBeInTheDocument();
    expect(screen.getByTestId("eta-chip-20")).toBeInTheDocument();
    expect(screen.getByTestId("eta-chip-30")).toBeInTheDocument();
    expect(screen.getByTestId("eta-chip-45")).toBeInTheDocument();
  });

  it("3. renders Custom option chip", () => {
    render(
      <TimeExtractionEditor
        initialMinutes={20}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByTestId("eta-chip-custom")).toBeInTheDocument();
  });

  it("4. tapping a quick-pick chip updates summary", () => {
    render(
      <TimeExtractionEditor
        initialMinutes={20}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("eta-chip-30"));
    // Summary text should contain "30 min" — use getAllByText to handle multiple matches
    const matches = screen.getAllByText(/30 min/);
    expect(matches.length).toBeGreaterThan(0);
  });

  it("5. tapping Custom shows text input", () => {
    render(
      <TimeExtractionEditor
        initialMinutes={20}
        onConfirm={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("eta-chip-custom"));
    expect(screen.getByTestId("eta-custom-input")).toBeInTheDocument();
  });

  it("6. confirm button calls onConfirm with selected minutes", () => {
    const onConfirm = vi.fn();
    render(
      <TimeExtractionEditor
        initialMinutes={20}
        onConfirm={onConfirm}
        onCancel={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByTestId("eta-chip-15"));
    fireEvent.click(screen.getByTestId("eta-confirm-btn"));
    expect(onConfirm).toHaveBeenCalledWith(15);
  });

  it("7. cancel button calls onCancel", () => {
    const onCancel = vi.fn();
    render(
      <TimeExtractionEditor
        initialMinutes={20}
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    );
    fireEvent.click(screen.getByTestId("eta-cancel-btn"));
    expect(onCancel).toHaveBeenCalledOnce();
  });
});
