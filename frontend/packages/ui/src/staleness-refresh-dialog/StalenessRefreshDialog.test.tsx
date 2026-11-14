/**
 * StalenessRefreshDialog — Unit Tests
 *
 * Location: packages/ui/src/staleness-refresh-dialog/StalenessRefreshDialog.test.tsx
 * Per batch-fe-b4-design.md §I.1
 * Target: 8 tests
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { StalenessRefreshDialog } from "./StalenessRefreshDialog";

describe("StalenessRefreshDialog", () => {
  it("renders nothing when isOpen=false", () => {
    const { container } = render(
      <StalenessRefreshDialog
        isOpen={false}
        onRetry={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders dialog when isOpen=true", () => {
    render(
      <StalenessRefreshDialog
        isOpen={true}
        onRetry={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("shows default title when no title prop", () => {
    render(
      <StalenessRefreshDialog
        isOpen={true}
        onRetry={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(
      screen.getByText("This record was updated while you were working"),
    ).toBeInTheDocument();
  });

  it("shows custom title when title prop provided", () => {
    render(
      <StalenessRefreshDialog
        isOpen={true}
        onRetry={vi.fn()}
        onCancel={vi.fn()}
        title="Schedule changed while you were working"
      />,
    );
    expect(
      screen.getByText("Schedule changed while you were working"),
    ).toBeInTheDocument();
  });

  it("calls onRetry when Retry button clicked", () => {
    const onRetry = vi.fn();
    render(
      <StalenessRefreshDialog
        isOpen={true}
        onRetry={onRetry}
        onCancel={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByText("Retry with updated data"));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("calls onCancel when Cancel button clicked", () => {
    const onCancel = vi.fn();
    render(
      <StalenessRefreshDialog
        isOpen={true}
        onRetry={vi.fn()}
        onCancel={onCancel}
      />,
    );

    fireEvent.click(screen.getByText("Cancel"));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("disables Retry button when isRetrying=true", () => {
    render(
      <StalenessRefreshDialog
        isOpen={true}
        onRetry={vi.fn()}
        onCancel={vi.fn()}
        isRetrying={true}
      />,
    );

    const retryButton = screen.getByText("Retrying…");
    expect(retryButton).toBeDisabled();
  });

  it("renders children as custom content", () => {
    render(
      <StalenessRefreshDialog
        isOpen={true}
        onRetry={vi.fn()}
        onCancel={vi.fn()}
      >
        <p>Custom conflict content</p>
      </StalenessRefreshDialog>,
    );

    expect(screen.getByText("Custom conflict content")).toBeInTheDocument();
  });

  it("has correct ARIA dialog role", () => {
    render(
      <StalenessRefreshDialog
        isOpen={true}
        onRetry={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
  });
});
