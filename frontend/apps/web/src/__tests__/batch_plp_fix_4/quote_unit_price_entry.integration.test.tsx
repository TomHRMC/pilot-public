/**
 * PLP-FIX-4 Integration: Quote Unit Price raw-string entry
 *
 * Location: apps/web/src/__tests__/batch_plp_fix_4/quote_unit_price_entry.integration.test.tsx
 *
 * Verifies:
 *  1. Add-line flow: 5.50 entry persists as 550 cents
 *  2. Editing a persisted row's price allows backspace + decimal
 *  3. Blur formats to 2dp
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LineItemEditor } from "../../features/quotes/components/LineItemEditor";

// Mock hooks to avoid network calls
vi.mock("../../features/quotes/hooks/useAddQuoteLine", () => ({
  useAddQuoteLine: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

const MOCK_LINE_TYPES = [
  {
    id: "type-labor",
    code: "labor",
    name: "Labor",
    is_default: true,
    is_active: true,
    is_tenant_override: false,
  },
  {
    id: "type-misc",
    code: "misc",
    name: "Misc",
    is_default: false,
    is_active: true,
    is_tenant_override: false,
  },
];
vi.mock("../../features/quotes/hooks/useQcoLineTypes", () => ({
  useQcoLineTypes: () => ({
    data: MOCK_LINE_TYPES,
    isPending: false,
    isError: false,
  }),
  resolveDefaultLineTypeId: (
    types: { id: string; code: string; is_default: boolean }[],
  ) => {
    if (types.length === 0) return null;
    return (
      types.find((t) => t.code === "misc")?.id ??
      types.find((t) => t.is_default)?.id ??
      types[0]!.id
    );
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  function TestWrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  }
  return TestWrapper;
}

describe("PLP-FIX-4 — Quote Unit Price raw-string entry", () => {
  it("add-line flow: 5.50 entry persists as 550 cents", () => {
    const onLinesChange = vi.fn();
    const lines = [
      {
        localId: "local-1",
        qco_line_type_id: "type-labor",
        description: "Labor",
        quantity: 1,
        unit_price_cents: 0,
      },
    ];
    render(<LineItemEditor lines={lines} onLinesChange={onLinesChange} />, {
      wrapper: createWrapper(),
    });

    const priceInput = screen.getByLabelText("Unit price");
    fireEvent.focus(priceInput);
    fireEvent.change(priceInput, { target: { value: "5.50" } });
    // Raw string preserved during editing
    expect((priceInput as HTMLInputElement).value).toBe("5.50");
    // Blur commits
    fireEvent.blur(priceInput);

    expect(onLinesChange).toHaveBeenCalled();
    const updated = onLinesChange.mock.calls[0][0];
    expect(updated[0].unit_price_cents).toBe(550);
  });

  it("editing a persisted row allows backspace + decimal", () => {
    const onLinesChange = vi.fn();
    const lines = [
      {
        localId: "local-1",
        qco_line_type_id: "type-labor",
        description: "Labor",
        quantity: 1,
        unit_price_cents: 550, // $5.50
      },
    ];
    render(<LineItemEditor lines={lines} onLinesChange={onLinesChange} />, {
      wrapper: createWrapper(),
    });

    const priceInput = screen.getByLabelText("Unit price");
    // Display shows formatted
    expect((priceInput as HTMLInputElement).value).toBe("5.50");

    // Focus → seed draft
    fireEvent.focus(priceInput);
    // Backspace: "5.5"
    fireEvent.change(priceInput, { target: { value: "5.5" } });
    expect((priceInput as HTMLInputElement).value).toBe("5.5");

    // Type decimal + digit: "5.55"
    fireEvent.change(priceInput, { target: { value: "5.55" } });
    expect((priceInput as HTMLInputElement).value).toBe("5.55");

    // Blur → 555 cents
    fireEvent.blur(priceInput);
    expect(onLinesChange).toHaveBeenCalled();
    const updated = onLinesChange.mock.calls[0][0];
    expect(updated[0].unit_price_cents).toBe(555);
  });

  it("blur formats display back to 2dp", () => {
    const onLinesChange = vi.fn();
    const lines = [
      {
        localId: "local-1",
        qco_line_type_id: "type-labor",
        description: "Labor",
        quantity: 1,
        unit_price_cents: 0,
      },
    ];
    const { rerender } = render(
      <LineItemEditor lines={lines} onLinesChange={onLinesChange} />,
      { wrapper: createWrapper() },
    );

    const priceInput = screen.getByLabelText("Unit price");
    fireEvent.focus(priceInput);
    fireEvent.change(priceInput, { target: { value: "5.5" } });
    fireEvent.blur(priceInput);

    const updated = onLinesChange.mock.calls[0][0];
    rerender(<LineItemEditor lines={updated} onLinesChange={onLinesChange} />);

    const priceAfter = screen.getByLabelText("Unit price") as HTMLInputElement;
    expect(priceAfter.value).toBe("5.50");
  });
});
