/**
 * RevertToDefaultDialog unit tests — FE-B11
 */

import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RevertToDefaultDialog } from "./RevertToDefaultDialog";

const baseProps = {
  settingLabel: "Auto-expire calendar conflicts",
  currentValue: 45,
  defaultValue: 30,
  unit: "days",
  onConfirm: vi.fn(),
  onCancel: vi.fn(),
  isReverting: false,
};

describe("RevertToDefaultDialog", () => {
  it("renders current value and default value", () => {
    render(<RevertToDefaultDialog {...baseProps} />);
    expect(screen.getByText(/45/)).toBeTruthy();
    expect(screen.getByText(/30/)).toBeTruthy();
  });

  it("renders setting label in confirmation text", () => {
    render(<RevertToDefaultDialog {...baseProps} />);
    expect(screen.getByText(/Auto-expire calendar conflicts/)).toBeTruthy();
  });

  it("renders unit suffix after both values", () => {
    render(<RevertToDefaultDialog {...baseProps} />);
    // "45 days" and "30 days" should appear
    const text = screen.getByRole("region").textContent ?? "";
    expect(text).toContain("45 days");
    expect(text).toContain("30 days");
  });

  it("calls onConfirm when Revert button clicked", () => {
    render(<RevertToDefaultDialog {...baseProps} />);
    fireEvent.click(screen.getByTestId("revert-dialog-confirm"));
    expect(baseProps.onConfirm).toHaveBeenCalled();
  });

  it("calls onCancel when Cancel button clicked", () => {
    render(<RevertToDefaultDialog {...baseProps} />);
    fireEvent.click(screen.getByTestId("revert-dialog-cancel"));
    expect(baseProps.onCancel).toHaveBeenCalled();
  });

  it("shows spinner when isReverting=true", () => {
    render(<RevertToDefaultDialog {...baseProps} isReverting={true} />);
    expect(screen.getByText(/Reverting/)).toBeTruthy();
  });

  it("disables buttons when isReverting=true", () => {
    render(<RevertToDefaultDialog {...baseProps} isReverting={true} />);
    const confirmBtn = screen.getByTestId(
      "revert-dialog-confirm",
    ) as HTMLButtonElement;
    const cancelBtn = screen.getByTestId(
      "revert-dialog-cancel",
    ) as HTMLButtonElement;
    expect(confirmBtn.disabled).toBe(true);
    expect(cancelBtn.disabled).toBe(true);
  });

  it("uses testID prefix when provided", () => {
    render(<RevertToDefaultDialog {...baseProps} testID="my-setting-revert" />);
    expect(screen.getByTestId("my-setting-revert-confirm")).toBeTruthy();
    expect(screen.getByTestId("my-setting-revert-cancel")).toBeTruthy();
  });
});
