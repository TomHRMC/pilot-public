/**
 * RemoveMethodConfirmModal unit tests — MFA-WIRE-1 Part B (spec §2.5, §10.4)
 *
 * Location: apps/web/src/features/account-settings/components/__tests__/RemoveMethodConfirmModal.test.tsx
 *
 * Verifies: focus moves to "Keep method" on open, Escape cancels, confirm
 * fires onConfirm, focus returns to the trigger button on close.
 */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, afterEach } from "vitest";
import { RemoveMethodConfirmModal } from "../RemoveMethodConfirmModal";

afterEach(() => {
  document.body.innerHTML = "";
});

function renderModal(
  open: boolean,
  overrides?: Partial<{
    onConfirm: () => void;
    onCancel: () => void;
  }>,
) {
  const onConfirm = overrides?.onConfirm ?? vi.fn();
  const onCancel = overrides?.onCancel ?? vi.fn();

  // Create a trigger button in the DOM so focus can return to it
  const trigger = document.createElement("button");
  trigger.id = "mfa-method-remove-totp";
  trigger.textContent = "Remove";
  document.body.appendChild(trigger);

  const result = render(
    <RemoveMethodConfirmModal
      open={open}
      methodLabel="Authenticator app"
      triggerButtonId="mfa-method-remove-totp"
      onConfirm={onConfirm}
      onCancel={onCancel}
    />,
  );

  return { ...result, onConfirm, onCancel, trigger };
}

describe("RemoveMethodConfirmModal", () => {
  it("renders modal when open=true", () => {
    renderModal(true);
    expect(screen.getByTestId("mfa-remove-modal")).toBeInTheDocument();
    expect(screen.getByText("Remove Authenticator app?")).toBeInTheDocument();
  });

  it("does not render when open=false", () => {
    renderModal(false);
    expect(screen.queryByTestId("mfa-remove-modal")).not.toBeInTheDocument();
  });

  it("moves focus to 'Keep method' on open", async () => {
    renderModal(true);
    // Focus is moved via setTimeout(0) — wait a tick
    await new Promise((r) => setTimeout(r, 10));
    const cancelBtn = screen.getByTestId("mfa-remove-modal-cancel");
    expect(document.activeElement).toBe(cancelBtn);
  });

  it("Escape key cancels", () => {
    const { onCancel } = renderModal(true);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("confirm button fires onConfirm", () => {
    const { onConfirm } = renderModal(true);
    fireEvent.click(screen.getByTestId("mfa-remove-modal-confirm"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("cancel button fires onCancel", () => {
    const { onCancel } = renderModal(true);
    fireEvent.click(screen.getByTestId("mfa-remove-modal-cancel"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("returns focus to the trigger button on close", async () => {
    const { onCancel, trigger, rerender } = renderModal(true);
    // Close the modal
    onCancel();
    rerender(
      <RemoveMethodConfirmModal
        open={false}
        methodLabel="Authenticator app"
        triggerButtonId="mfa-method-remove-totp"
        onConfirm={vi.fn()}
        onCancel={onCancel}
      />,
    );
    await new Promise((r) => setTimeout(r, 10));
    expect(document.activeElement).toBe(trigger);
  });
});
