/**
 * LineItemEditor unit tests — FE-B19
 *
 * Location: apps/web/src/features/quotes/components/__tests__/LineItemEditor.test.tsx
 *
 * Platform: Web (Vitest + @testing-library/react)
 */

import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LineItemEditor } from "../LineItemEditor";

// LineItemEditor in create mode calls useAddQuoteLine only in edit mode,
// but still imports it — mock to avoid network calls.
vi.mock("../../hooks/useAddQuoteLine", () => ({
  useAddQuoteLine: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}));

// PLP-FIX-2: mock useQcoLineTypes to return API-shaped data (avoids network calls)
const MOCK_LINE_TYPES = [
  {
    id: "type-discount",
    code: "discount",
    name: "Discount",
    is_default: false,
    is_active: true,
    is_tenant_override: false,
  },
  {
    id: "type-labor",
    code: "labor",
    name: "Labor",
    is_default: true,
    is_active: true,
    is_tenant_override: false,
  },
  {
    id: "type-material",
    code: "material",
    name: "Material",
    is_default: false,
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
  {
    id: "type-note",
    code: "note",
    name: "Note",
    is_default: false,
    is_active: true,
    is_tenant_override: false,
  },
];
vi.mock("../../hooks/useQcoLineTypes", () => ({
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

describe("LineItemEditor (create mode)", () => {
  it("renders empty state with Add Line Item button when no lines", () => {
    render(<LineItemEditor lines={[]} onLinesChange={vi.fn()} />, {
      wrapper: createWrapper(),
    });
    expect(screen.getByText(/No line items yet/i)).toBeInTheDocument();
    expect(screen.getByText(/\+ Add Line Item/i)).toBeInTheDocument();
  });

  it("adds a new row when Add Line Item is clicked", () => {
    const onLinesChange = vi.fn();
    render(<LineItemEditor lines={[]} onLinesChange={onLinesChange} />, {
      wrapper: createWrapper(),
    });
    fireEvent.click(screen.getByText(/\+ Add Line Item/i));
    expect(onLinesChange).toHaveBeenCalledOnce();
    const newLines = onLinesChange.mock.calls[0][0];
    expect(newLines).toHaveLength(1);
    expect(newLines[0].description).toBe("");
    expect(newLines[0].quantity).toBe(1);
    // PLP-FIX-2: new row defaults to the 'misc' type id from the API
    expect(newLines[0].qco_line_type_id).toBe("type-misc");
  });

  it("renders description and quantity inputs when lines are present", () => {
    const lines = [
      {
        localId: "local-1",
        qco_line_type_id: "c067e242-84dc-4d73-bdce-84aec6d0bd3a",
        description: "Panel upgrade",
        quantity: 1,
        unit_price_cents: 120000,
      },
    ];
    render(<LineItemEditor lines={lines} onLinesChange={vi.fn()} />, {
      wrapper: createWrapper(),
    });
    const descInput = screen.getByDisplayValue("Panel upgrade");
    expect(descInput).toBeInTheDocument();
    expect(screen.getByDisplayValue("1")).toBeInTheDocument(); // qty
  });

  it("calculates row total correctly (qty × unit_price_cents)", () => {
    const lines = [
      {
        localId: "local-1",
        qco_line_type_id: "c067e242-84dc-4d73-bdce-84aec6d0bd3a",
        description: "Wire",
        quantity: 100,
        unit_price_cents: 85, // $0.85
      },
    ];
    render(<LineItemEditor lines={lines} onLinesChange={vi.fn()} />, {
      wrapper: createWrapper(),
    });
    // Row total = 100 × $0.85 = $85.00; subtotal also $85.00
    expect(screen.getAllByText("$85.00")).toBeTruthy();
  });

  it("calls onLinesChange without the removed row when Remove is clicked", () => {
    const onLinesChange = vi.fn();
    const lines = [
      {
        localId: "local-1",
        qco_line_type_id: "c067e242-84dc-4d73-bdce-84aec6d0bd3a",
        description: "Item A",
        quantity: 1,
        unit_price_cents: 10000,
      },
      {
        localId: "local-2",
        qco_line_type_id: "c067e242-84dc-4d73-bdce-84aec6d0bd3a",
        description: "Item B",
        quantity: 2,
        unit_price_cents: 5000,
      },
    ];
    render(<LineItemEditor lines={lines} onLinesChange={onLinesChange} />, {
      wrapper: createWrapper(),
    });
    const removeButtons = screen.getAllByRole("button", {
      name: /Remove line/i,
    });
    fireEvent.click(removeButtons[0]!);
    const updatedLines = onLinesChange.mock.calls[0][0];
    expect(updatedLines).toHaveLength(1);
    expect(updatedLines[0].localId).toBe("local-2");
  });

  it("shows running subtotal that updates across all rows", () => {
    const lines = [
      {
        localId: "local-1",
        qco_line_type_id: "c067e242-84dc-4d73-bdce-84aec6d0bd3a",
        description: "A",
        quantity: 2,
        unit_price_cents: 50000, // $500
      },
      {
        localId: "local-2",
        qco_line_type_id: "c067e242-84dc-4d73-bdce-84aec6d0bd3a",
        description: "B",
        quantity: 1,
        unit_price_cents: 25000, // $250
      },
    ];
    render(<LineItemEditor lines={lines} onLinesChange={vi.fn()} />, {
      wrapper: createWrapper(),
    });
    // Subtotal = $1,000 + $250 = $1,250
    expect(screen.getByText("$1,250.00")).toBeInTheDocument();
  });

  // ── PLP-FIX-4 Issue 11: Unit Price raw-string editing ──────────────────────

  it("typing 5.50 into Unit Price persists as 550 cents on blur", () => {
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
    // Focus seeds the draft from current cents (0 → "")
    fireEvent.focus(priceInput);
    // Type 5.50 — raw string preserved during editing
    fireEvent.change(priceInput, { target: { value: "5.50" } });
    expect((priceInput as HTMLInputElement).value).toBe("5.50");
    // Blur → parseCentInput("5.50") = 550 → onLinesChange called
    fireEvent.blur(priceInput);
    expect(onLinesChange).toHaveBeenCalled();
    const updatedLines = onLinesChange.mock.calls[0][0];
    expect(updatedLines[0].unit_price_cents).toBe(550);
  });

  it("backspace in Unit Price works without reformatting mid-edit", () => {
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
    // Display shows formatted 2dp
    expect((priceInput as HTMLInputElement).value).toBe("5.50");
    // Focus seeds draft from cents
    fireEvent.focus(priceInput);
    // Backspace: remove the 0 → "5.5"
    fireEvent.change(priceInput, { target: { value: "5.5" } });
    expect((priceInput as HTMLInputElement).value).toBe("5.5");
    // Blur → parseCentInput("5.5") = 550 → same cents
    fireEvent.blur(priceInput);
    expect(onLinesChange).toHaveBeenCalled();
    const updatedLines = onLinesChange.mock.calls[0][0];
    expect(updatedLines[0].unit_price_cents).toBe(550);
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
    // After blur, the draft clears and display reverts to formatted cents
    const updatedLines = onLinesChange.mock.calls[0][0];
    // Re-render with updated lines to see the formatted display
    rerender(
      <LineItemEditor lines={updatedLines} onLinesChange={onLinesChange} />,
    );
    const priceAfterBlur = screen.getByLabelText(
      "Unit price",
    ) as HTMLInputElement;
    expect(priceAfterBlur.value).toBe("5.50");
  });
});
