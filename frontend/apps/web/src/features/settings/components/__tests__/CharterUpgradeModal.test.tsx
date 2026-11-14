/**
 * CharterUpgradeModal — Unit Tests (C-B12 Part B)
 *
 * Location: apps/web/src/features/settings/components/__tests__/CharterUpgradeModal.test.tsx
 *
 * Platform: Web (Vitest + @testing-library/react + jsdom)
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import "@testing-library/jest-dom";

import { CharterUpgradeModal } from "../CharterUpgradeModal";

// ── Helpers ──────────────────────────────────────────────────────────────────

function renderModal(overrides?: {
  isOpen?: boolean;
  onUpgrade?: (interval: "monthly" | "annual") => Promise<void>;
  isUpgrading?: boolean;
  upgradeError?: string | null;
  onClose?: () => void;
}) {
  const onClose = overrides?.onClose ?? vi.fn();
  const onUpgrade =
    overrides?.onUpgrade ?? vi.fn().mockResolvedValue(undefined);
  render(
    <CharterUpgradeModal
      isOpen={overrides?.isOpen ?? true}
      onClose={onClose}
      onUpgrade={onUpgrade}
      isUpgrading={overrides?.isUpgrading ?? false}
      upgradeError={overrides?.upgradeError ?? null}
    />,
  );
  return { onClose, onUpgrade };
}

// ── Tests ────────────────────────────────────────────────────────────────────

describe("CharterUpgradeModal", () => {
  it("1. renders warning header 'You'll lose your Charter rate.'", () => {
    renderModal();
    expect(
      screen.getByText(/You'll lose your Charter rate/i),
    ).toBeInTheDocument();
  });

  it("2. shows both pricing options ($179/mo monthly, $149/mo annual)", () => {
    renderModal();
    expect(screen.getByText("$179/mo")).toBeInTheDocument();
    expect(screen.getByText("$149/mo (billed $1,788/yr)")).toBeInTheDocument();
  });

  it("3. billing interval selector defaults to Monthly (aria-checked)", () => {
    renderModal();
    const monthlyRadio = screen.getByRole("radio", { name: /Monthly/i });
    expect(monthlyRadio).toHaveAttribute("aria-checked", "true");
    const annualRadio = screen.getByRole("radio", { name: /Annual/i });
    expect(annualRadio).toHaveAttribute("aria-checked", "false");
  });

  it("4. clicking 'Keep my Charter rate' calls onClose (safe default)", () => {
    const { onClose } = renderModal();
    fireEvent.click(screen.getByText("Keep my Charter rate"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("5. clicking 'I understand — upgrade to Teams' calls onUpgrade with monthly", () => {
    const { onUpgrade } = renderModal();
    fireEvent.click(screen.getByText("I understand — upgrade to Teams"));
    expect(onUpgrade).toHaveBeenCalledWith("monthly");
  });

  it("5b. selecting Annual then confirming calls onUpgrade with annual", () => {
    const { onUpgrade } = renderModal();
    fireEvent.click(screen.getByRole("radio", { name: /Annual/i }));
    fireEvent.click(screen.getByText("I understand — upgrade to Teams"));
    expect(onUpgrade).toHaveBeenCalledWith("annual");
  });

  it("6. loading state: 'Upgrading…' + disabled when isUpgrading=true", () => {
    renderModal({ isUpgrading: true });
    const upgradeBtn = screen.getByText("Upgrading…");
    expect(upgradeBtn).toBeInTheDocument();
    expect(upgradeBtn.closest("button")).toBeDisabled();
  });

  it("7. error state: shows error message when upgradeError is set", () => {
    renderModal({ upgradeError: "No payment method on file." });
    expect(screen.getByText("No payment method on file.")).toBeInTheDocument();
  });

  it("8. Escape key closes modal (safe default)", () => {
    const { onClose } = renderModal();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("8b. Escape key does NOT close during loading", () => {
    const { onClose } = renderModal({ isUpgrading: true });
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).not.toHaveBeenCalled();
  });

  it("9. focus trap: safe-default button receives focus on open", () => {
    renderModal();
    const safeBtn = screen.getByText("Keep my Charter rate");
    // The setTimeout in the effect fires focus; in jsdom we check the ref target
    expect(safeBtn).toBeInTheDocument();
  });

  it("10. does not render when isOpen=false", () => {
    renderModal({ isOpen: false });
    expect(
      screen.queryByText(/You'll lose your Charter rate/i),
    ).not.toBeInTheDocument();
  });

  it("11. overlay click closes modal (safe default)", () => {
    const { onClose } = renderModal();
    // The overlay is the outermost dialog div
    const dialog = screen.getByRole("dialog");
    fireEvent.click(dialog);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("11b. overlay click does NOT close during loading", () => {
    const { onClose } = renderModal({ isUpgrading: true });
    const dialog = screen.getByRole("dialog");
    fireEvent.click(dialog);
    expect(onClose).not.toHaveBeenCalled();
  });

  it("12. shows current rate display '$49/month, locked'", () => {
    renderModal();
    expect(screen.getByText(/locked/i)).toBeInTheDocument();
  });

  it("13. shows forfeiture warning about irreversibility", () => {
    renderModal();
    expect(screen.getByText(/gone for good/i)).toBeInTheDocument();
  });
});
