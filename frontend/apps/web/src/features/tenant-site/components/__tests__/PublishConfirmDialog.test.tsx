/**
 * PublishConfirmDialog — Unit Tests
 *
 * Location: apps/web/src/features/tenant-site/components/__tests__/PublishConfirmDialog.test.tsx
 *
 * Tests normal publish variant, 409 overwrite variant, close behavior, checkbox gate.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";
import { PublishConfirmDialog } from "../PublishConfirmDialog";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
    [key: string]: unknown;
  }) => React.createElement("a", { href, ...rest }, children),
}));

const defaultProps = {
  open: true,
  onClose: vi.fn(),
  onConfirm: vi.fn(),
  isPublishing: false,
  slug: "my-shop",
  displayName: "My Shop",
};

describe("PublishConfirmDialog", () => {
  it("renders nothing when open=false", () => {
    render(<PublishConfirmDialog {...defaultProps} open={false} />);
    expect(screen.queryByTestId("publish-confirm-dialog")).toBeNull();
  });

  it("renders dialog with title when open", () => {
    render(<PublishConfirmDialog {...defaultProps} />);
    expect(
      screen.getByText("Publish your compliance site"),
    ).toBeInTheDocument();
    expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
  });

  it("shows normal variant with Publish button when no overwriteConflict", () => {
    render(<PublishConfirmDialog {...defaultProps} />);
    expect(screen.getByTestId("publish-confirm-btn")).toBeInTheDocument();
    expect(screen.queryByTestId("publish-overwrite-confirm-btn")).toBeNull();
  });

  it("calls onConfirm(false) when Publish button clicked in normal variant", () => {
    const onConfirm = vi.fn();
    render(<PublishConfirmDialog {...defaultProps} onConfirm={onConfirm} />);
    fireEvent.click(screen.getByTestId("publish-confirm-btn"));
    expect(onConfirm).toHaveBeenCalledWith(false);
  });

  it("calls onClose when close button clicked", () => {
    const onClose = vi.fn();
    render(<PublishConfirmDialog {...defaultProps} onClose={onClose} />);
    fireEvent.click(screen.getByTestId("publish-dialog-close"));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when overlay clicked", () => {
    const onClose = vi.fn();
    render(<PublishConfirmDialog {...defaultProps} onClose={onClose} />);
    fireEvent.click(screen.getByTestId("publish-confirm-overlay"));
    expect(onClose).toHaveBeenCalled();
  });

  it("shows overwrite variant when overwriteConflict is provided", () => {
    render(
      <PublishConfirmDialog
        {...defaultProps}
        overwriteConflict={{
          current_url: "https://old.example.com",
          new_url: "https://new.p4tsites.com",
          brand_status: "active",
        }}
      />,
    );
    expect(
      screen.getByTestId("publish-overwrite-confirm-btn"),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("publish-confirm-btn")).toBeNull();
    expect(screen.getByText("https://old.example.com")).toBeInTheDocument();
    expect(screen.getByText("https://new.p4tsites.com")).toBeInTheDocument();
  });

  it("overwrite confirm button is disabled until checkbox is checked", () => {
    render(
      <PublishConfirmDialog
        {...defaultProps}
        overwriteConflict={{
          current_url: "https://old.example.com",
          new_url: "https://new.p4tsites.com",
          brand_status: "active",
        }}
      />,
    );
    const confirmBtn = screen.getByTestId("publish-overwrite-confirm-btn");
    expect(confirmBtn).toBeDisabled();

    const checkbox = screen.getByTestId("publish-overwrite-checkbox");
    fireEvent.click(checkbox);
    expect(confirmBtn).not.toBeDisabled();
  });

  it("calls onConfirm(true) when overwrite confirm button clicked after checkbox", () => {
    const onConfirm = vi.fn();
    render(
      <PublishConfirmDialog
        {...defaultProps}
        onConfirm={onConfirm}
        overwriteConflict={{
          current_url: "https://old.example.com",
          new_url: "https://new.p4tsites.com",
          brand_status: "active",
        }}
      />,
    );
    fireEvent.click(screen.getByTestId("publish-overwrite-checkbox"));
    fireEvent.click(screen.getByTestId("publish-overwrite-confirm-btn"));
    expect(onConfirm).toHaveBeenCalledWith(true);
  });

  it("shows Publishing... text when isPublishing=true", () => {
    render(<PublishConfirmDialog {...defaultProps} isPublishing={true} />);
    expect(screen.getByText("Publishing…")).toBeInTheDocument();
  });
});
