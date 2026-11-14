/**
 * LineItemEditor — inline table for managing quote line items
 *
 * Location: apps/web/src/features/quotes/components/LineItemEditor.tsx
 *
 * Supports two modes:
 *  1. Create flow (controlled): lines/onLinesChange props — local state, not yet persisted
 *  2. Edit flow on existing quote: quoteId + persistedLines — add-only (no DELETE/PATCH endpoint)
 *
 * PLP-FIX-2: QCO line types are resolved dynamically from GET /api/v1/qco-line-types
 *   via useQcoLineTypes(). UUIDs differ per environment BY DESIGN — `code` is the only
 *   stable cross-environment key. The hardcoded dev-seed UUID consts were deleted to
 *   fix Issue 5 from testing on the pre-release AWS environment (FK violation 500).
 */

"use client";

import React, { useState } from "react";
import { ErrorState } from "@pilot/ui";
import { useAddQuoteLine } from "../hooks/useAddQuoteLine";
import type { AddQuoteLineInput } from "../hooks/useAddQuoteLine";
import {
  useQcoLineTypes,
  resolveDefaultLineTypeId,
} from "../hooks/useQcoLineTypes";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export interface LocalLineItem {
  localId: string; // browser-only key for list rendering
  qco_line_type_id: string;
  description: string;
  quantity: number;
  unit_price_cents: number;
}

export interface PersistedLineItem {
  id: string;
  description: string;
  quantity: number;
  unit_price_cents: number;
  qco_line_type_id?: string | null;
}

interface LineItemEditorProps {
  // --- Create flow (controlled) ---
  lines?: LocalLineItem[];
  onLinesChange?: (lines: LocalLineItem[]) => void;

  // --- Edit flow (existing quote) ---
  quoteId?: string;
  persistedLines?: PersistedLineItem[];

  readOnly?: boolean;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function formatDollars(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

function parseCentInput(dollarStr: string): number {
  const n = parseFloat(dollarStr.replace(/[^0-9.]/g, ""));
  return isNaN(n) ? 0 : Math.round(n * 100);
}

function newLocalId(): string {
  return `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

// ---------------------------------------------------------------------------
// Empty row template — PLP-FIX-2: default type id resolved dynamically from API
// ---------------------------------------------------------------------------
function emptyLine(defaultTypeId: string): LocalLineItem {
  return {
    localId: newLocalId(),
    qco_line_type_id: defaultTypeId,
    description: "",
    quantity: 1,
    unit_price_cents: 0,
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export function LineItemEditor({
  lines,
  onLinesChange,
  quoteId,
  persistedLines = [],
  readOnly = false,
}: LineItemEditorProps) {
  const isCreateMode = lines !== undefined && onLinesChange !== undefined;

  // PLP-FIX-2: line types resolved dynamically from GET /api/v1/qco-line-types
  const {
    data: lineTypes,
    isPending: typesPending,
    isError: typesError,
  } = useQcoLineTypes();
  const defaultTypeId = resolveDefaultLineTypeId(lineTypes ?? []);

  // Edit mode: track a "new row" being added to an existing quote
  const [addingLine, setAddingLine] = useState<LocalLineItem | null>(null);
  const [addError, setAddError] = useState<string | null>(null);

  // PLP-FIX-4 Issue 11: raw-string draft for Unit Price editing.
  // While a row's price input is focused, the user types a raw string (digits +
  // at most one ".") that is NOT round-tripped through parseCentInput on every
  // keystroke. On blur, the raw string is parsed to cents and the draft clears,
  // reverting display to the formatted 2dp value.
  const [priceDraft, setPriceDraft] = useState<{
    key: string;
    raw: string;
  } | null>(null);
  // Separate draft for the add-row (edit mode) — single row at a time.
  const [addPriceDraft, setAddPriceDraft] = useState<string | null>(null);

  /** Allow digits and at most one decimal point. */
  function sanitizePriceRaw(input: string): string {
    const stripped = input.replace(/[^0-9.]/g, "");
    const firstDot = stripped.indexOf(".");
    if (firstDot === -1) return stripped;
    return (
      stripped.slice(0, firstDot + 1) +
      stripped.slice(firstDot + 1).replace(/\./g, "")
    );
  }

  const addLinesMutation = useAddQuoteLine(quoteId ?? "");

  // ------- Create-mode row change -------
  function handleLocalChange(
    localId: string,
    field: keyof Omit<LocalLineItem, "localId">,
    value: string | number,
  ) {
    if (!isCreateMode) return;
    onLinesChange!(
      lines!.map((l) =>
        l.localId === localId
          ? {
              ...l,
              [field]:
                field === "unit_price_cents"
                  ? parseCentInput(String(value))
                  : field === "quantity"
                    ? Math.max(1, Number(value))
                    : value,
            }
          : l,
      ),
    );
  }

  function handleAddRow() {
    if (!isCreateMode || !defaultTypeId) return;
    onLinesChange!([...lines!, emptyLine(defaultTypeId)]);
  }

  function handleRemoveRow(localId: string) {
    if (!isCreateMode) return;
    onLinesChange!(lines!.filter((l) => l.localId !== localId));
  }

  // ------- Edit-mode: add a new row to existing quote -------
  function handleStartAddEditRow() {
    if (!defaultTypeId) return;
    setAddingLine(emptyLine(defaultTypeId));
    setAddError(null);
  }

  function handleCancelAddEditRow() {
    setAddingLine(null);
    setAddError(null);
  }

  async function handleCommitEditRow() {
    if (!addingLine || !quoteId) return;
    setAddError(null);
    const position = persistedLines.length + 1;
    const input: AddQuoteLineInput = {
      position,
      qco_line_type_id: addingLine.qco_line_type_id,
      description: addingLine.description.trim(),
      quantity: addingLine.quantity,
      unit_price_cents: addingLine.unit_price_cents,
      customer_visible: true,
    };
    try {
      await addLinesMutation.mutateAsync(input);
      setAddingLine(null);
    } catch {
      setAddError("Failed to save line. Please try again.");
    }
  }

  // ------- Subtotal computation -------
  const localSubtotal = isCreateMode
    ? lines!.reduce((sum, l) => sum + l.quantity * l.unit_price_cents, 0)
    : persistedLines.reduce(
        (sum, l) => sum + l.quantity * l.unit_price_cents,
        0,
      );

  // ------- Render -------
  const displayLines: Array<
    LocalLineItem | (PersistedLineItem & { localId?: string })
  > = isCreateMode ? lines! : persistedLines;

  // PLP-FIX-2: error guard — a user must never add a line with no valid type id
  if (typesError) {
    return (
      <ErrorState
        type="server"
        title="Could not load line types"
        description="Check your connection and try again."
      />
    );
  }

  return (
    <div className="space-y-3">
      {/* Table header */}
      <div className="rounded-md border border-neutral-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-neutral-50">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-neutral-600 w-24">
                Type
              </th>
              <th className="px-3 py-2 text-left font-medium text-neutral-600">
                Description
              </th>
              <th className="px-3 py-2 text-right font-medium text-neutral-600 w-20">
                Qty
              </th>
              <th className="px-3 py-2 text-right font-medium text-neutral-600 w-28">
                Unit Price
              </th>
              <th className="px-3 py-2 text-right font-medium text-neutral-600 w-28">
                Total
              </th>
              {!readOnly && (
                <th className="px-3 py-2 w-10" aria-label="Actions" />
              )}
            </tr>
          </thead>

          <tbody className="divide-y divide-neutral-100">
            {displayLines.length === 0 && !addingLine && (
              <tr>
                <td
                  colSpan={readOnly ? 5 : 6}
                  className="px-3 py-6 text-center text-neutral-400 text-sm"
                >
                  No line items yet. Click &quot;Add Line Item&quot; below to
                  start.
                </td>
              </tr>
            )}

            {displayLines.map((line) => {
              const lineId =
                "localId" in line ? (line.localId as string) : line.id;
              const rowTotal = line.quantity * line.unit_price_cents;

              if (isCreateMode) {
                const localLine = line as LocalLineItem;
                return (
                  <tr key={lineId} className="hover:bg-neutral-50">
                    <td className="px-3 py-2">
                      <select
                        aria-label="Line type"
                        value={localLine.qco_line_type_id}
                        onChange={(e) =>
                          handleLocalChange(
                            localLine.localId,
                            "qco_line_type_id",
                            e.target.value,
                          )
                        }
                        className="w-full text-xs border border-neutral-200 rounded px-1 py-0.5 bg-white focus:outline-none focus:border-brand-400"
                      >
                        {(lineTypes ?? []).map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="text"
                        aria-label="Description"
                        value={localLine.description}
                        onChange={(e) =>
                          handleLocalChange(
                            localLine.localId,
                            "description",
                            e.target.value,
                          )
                        }
                        placeholder="Item description"
                        className="w-full border border-neutral-200 rounded px-2 py-0.5 text-sm focus:outline-none focus:border-brand-400"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="number"
                        aria-label="Quantity"
                        min={1}
                        value={localLine.quantity}
                        onChange={(e) =>
                          handleLocalChange(
                            localLine.localId,
                            "quantity",
                            e.target.value,
                          )
                        }
                        className="w-full text-right border border-neutral-200 rounded px-2 py-0.5 text-sm focus:outline-none focus:border-brand-400"
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        type="text"
                        aria-label="Unit price"
                        value={
                          priceDraft?.key === localLine.localId
                            ? priceDraft.raw
                            : localLine.unit_price_cents === 0
                              ? ""
                              : (localLine.unit_price_cents / 100).toFixed(2)
                        }
                        onChange={(e) => {
                          const raw = sanitizePriceRaw(e.target.value);
                          setPriceDraft({ key: localLine.localId, raw });
                        }}
                        onFocus={() =>
                          setPriceDraft({
                            key: localLine.localId,
                            raw:
                              localLine.unit_price_cents === 0
                                ? ""
                                : (localLine.unit_price_cents / 100).toFixed(2),
                          })
                        }
                        onBlur={() => {
                          if (priceDraft?.key === localLine.localId) {
                            handleLocalChange(
                              localLine.localId,
                              "unit_price_cents",
                              priceDraft.raw,
                            );
                            setPriceDraft(null);
                          }
                        }}
                        placeholder="0.00"
                        className="w-full text-right border border-neutral-200 rounded px-2 py-0.5 text-sm focus:outline-none focus:border-brand-400"
                      />
                    </td>
                    <td className="px-3 py-2 text-right text-neutral-700 font-medium">
                      {formatDollars(rowTotal)}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <button
                        type="button"
                        onClick={() => handleRemoveRow(localLine.localId)}
                        aria-label="Remove line"
                        className="text-neutral-400 hover:text-alert-600 transition-colors"
                      >
                        ×
                      </button>
                    </td>
                  </tr>
                );
              }

              // Persisted (read-only in edit mode — add-only; no DELETE/PATCH)
              return (
                <tr key={lineId} className="hover:bg-neutral-50">
                  <td className="px-3 py-2 text-xs text-neutral-500 capitalize">
                    {(lineTypes ?? []).find(
                      (t) =>
                        t.id === (line as PersistedLineItem).qco_line_type_id,
                    )?.name ?? "—"}
                  </td>
                  <td className="px-3 py-2 text-neutral-700">
                    {line.description}
                  </td>
                  <td className="px-3 py-2 text-right text-neutral-700">
                    {line.quantity}
                  </td>
                  <td className="px-3 py-2 text-right text-neutral-700">
                    {formatDollars(line.unit_price_cents)}
                  </td>
                  <td className="px-3 py-2 text-right text-neutral-700 font-medium">
                    {formatDollars(rowTotal)}
                  </td>
                  {!readOnly && <td />}
                </tr>
              );
            })}

            {/* Edit-mode: new row being entered */}
            {!isCreateMode && addingLine && (
              <tr className="bg-brand-50">
                <td className="px-3 py-2">
                  <select
                    aria-label="New line type"
                    value={addingLine.qco_line_type_id}
                    onChange={(e) =>
                      setAddingLine({
                        ...addingLine,
                        qco_line_type_id: e.target.value,
                      })
                    }
                    className="w-full text-xs border border-brand-200 rounded px-1 py-0.5 bg-white focus:outline-none focus:border-brand-400"
                  >
                    {(lineTypes ?? []).map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-2">
                  <input
                    type="text"
                    aria-label="New description"
                    value={addingLine.description}
                    onChange={(e) =>
                      setAddingLine({
                        ...addingLine,
                        description: e.target.value,
                      })
                    }
                    placeholder="Item description"
                    autoFocus
                    className="w-full border border-brand-200 rounded px-2 py-0.5 text-sm focus:outline-none focus:border-brand-400"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="number"
                    aria-label="New quantity"
                    min={1}
                    value={addingLine.quantity}
                    onChange={(e) =>
                      setAddingLine({
                        ...addingLine,
                        quantity: Math.max(1, Number(e.target.value)),
                      })
                    }
                    className="w-full text-right border border-brand-200 rounded px-2 py-0.5 text-sm focus:outline-none focus:border-brand-400"
                  />
                </td>
                <td className="px-3 py-2">
                  <input
                    type="text"
                    aria-label="New unit price"
                    value={
                      addPriceDraft !== null
                        ? addPriceDraft
                        : addingLine.unit_price_cents === 0
                          ? ""
                          : (addingLine.unit_price_cents / 100).toFixed(2)
                    }
                    onChange={(e) => {
                      const raw = sanitizePriceRaw(e.target.value);
                      setAddPriceDraft(raw);
                    }}
                    onFocus={() =>
                      setAddPriceDraft(
                        addingLine.unit_price_cents === 0
                          ? ""
                          : (addingLine.unit_price_cents / 100).toFixed(2),
                      )
                    }
                    onBlur={() => {
                      if (addPriceDraft !== null) {
                        setAddingLine({
                          ...addingLine,
                          unit_price_cents: parseCentInput(addPriceDraft),
                        });
                        setAddPriceDraft(null);
                      }
                    }}
                    placeholder="0.00"
                    className="w-full text-right border border-brand-200 rounded px-2 py-0.5 text-sm focus:outline-none focus:border-brand-400"
                  />
                </td>
                <td className="px-3 py-2 text-right text-neutral-700 font-medium">
                  {formatDollars(
                    addingLine.quantity * addingLine.unit_price_cents,
                  )}
                </td>
                <td className="px-3 py-2 text-center">
                  <button
                    type="button"
                    onClick={handleCancelAddEditRow}
                    aria-label="Cancel new line"
                    className="text-neutral-400 hover:text-alert-600 transition-colors"
                  >
                    ×
                  </button>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Errors from edit-mode save */}
      {addError && <p className="text-xs text-alert-600 px-1">{addError}</p>}

      {/* Footer: Add button + running subtotal */}
      <div className="flex items-center justify-between">
        {!readOnly && (
          <div className="flex gap-2">
            {isCreateMode ? (
              <button
                type="button"
                onClick={handleAddRow}
                disabled={typesPending || !defaultTypeId}
                className="text-sm text-brand-600 font-medium hover:underline px-2 py-1 rounded border border-brand-200 hover:bg-brand-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {typesPending ? "Loading types…" : "+ Add Line Item"}
              </button>
            ) : addingLine ? (
              <button
                type="button"
                onClick={() => void handleCommitEditRow()}
                disabled={addLinesMutation.isPending}
                className="text-sm text-white bg-brand-600 font-medium px-3 py-1 rounded hover:bg-brand-700 transition-colors disabled:opacity-50"
              >
                {addLinesMutation.isPending ? "Saving…" : "Save Line"}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleStartAddEditRow}
                disabled={typesPending || !defaultTypeId}
                className="text-sm text-brand-600 font-medium hover:underline px-2 py-1 rounded border border-brand-200 hover:bg-brand-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {typesPending ? "Loading types…" : "+ Add Line Item"}
              </button>
            )}
          </div>
        )}

        <div className="ml-auto text-sm font-medium text-neutral-700">
          Subtotal:{" "}
          <span className="text-neutral-900 font-semibold">
            {formatDollars(localSubtotal)}
          </span>
        </div>
      </div>
    </div>
  );
}
