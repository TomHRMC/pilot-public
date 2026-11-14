/**
 * PricebookItemForm Unit Tests — FE-B20
 *
 * Location: apps/web/src/features/catalog/components/__tests__/PricebookItemForm.test.tsx
 *
 * Rule 17: Web tests use vi.mock(), toBeInTheDocument(), userEvent
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PricebookItemForm } from "../PricebookItemForm";

describe("PricebookItemForm", () => {
  const mockOnSubmit = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    mockOnSubmit.mockClear();
    mockOnCancel.mockClear();
  });

  it("renders without crashing in create mode", () => {
    render(
      <PricebookItemForm
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
        isSubmitting={false}
      />,
    );
    expect(screen.getByLabelText(/SKU/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Description/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Unit Price/i)).toBeInTheDocument();
  });

  it("SKU input is editable in create mode (isEdit=false)", () => {
    render(
      <PricebookItemForm
        isEdit={false}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
        isSubmitting={false}
      />,
    );
    const skuInput = screen.getByLabelText(/SKU/i);
    expect(skuInput.tagName).toBe("INPUT");
    expect(skuInput).not.toHaveAttribute("readOnly");
  });

  it("SKU is read-only in edit mode (isEdit=true)", () => {
    render(
      <PricebookItemForm
        isEdit={true}
        initialValues={{ sku: "SW-200A", name: "Service Panel" }}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
        isSubmitting={false}
      />,
    );
    // SKU renders as a read-only div, not a functional input
    // The div has aria-label "SKU (read-only)" and shows the value
    const skuElement = screen.getByText("SW-200A");
    expect(skuElement.tagName).not.toBe("INPUT");
    expect(screen.getByText(/SKU cannot be changed/i)).toBeInTheDocument();
  });

  it("submit calls onSubmit with correct data shape", async () => {
    const user = userEvent.setup();

    render(
      <PricebookItemForm
        isEdit={false}
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
        isSubmitting={false}
      />,
    );

    await user.type(screen.getByLabelText(/SKU/i), "TEST-001");
    await user.type(screen.getByLabelText(/Name/i), "Test Item");
    await user.type(screen.getByLabelText(/Unit Price/i), "99.99");

    await user.click(screen.getByRole("button", { name: /Add Item/i }));

    expect(mockOnSubmit).toHaveBeenCalledOnce();
    expect(mockOnSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        sku: "TEST-001",
        name: "Test Item",
        initial_price_dollars: "99.99",
      }),
    );
  });

  it("cancel calls onCancel", async () => {
    const user = userEvent.setup();

    render(
      <PricebookItemForm
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
        isSubmitting={false}
      />,
    );

    await user.click(screen.getByRole("button", { name: /Cancel/i }));
    expect(mockOnCancel).toHaveBeenCalledOnce();
    expect(mockOnSubmit).not.toHaveBeenCalled();
  });

  it("shows submitting state when isSubmitting=true", () => {
    render(
      <PricebookItemForm
        onSubmit={mockOnSubmit}
        onCancel={mockOnCancel}
        isSubmitting={true}
      />,
    );
    expect(screen.getByRole("button", { name: /Saving/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Saving/i })).toBeDisabled();
  });
});
