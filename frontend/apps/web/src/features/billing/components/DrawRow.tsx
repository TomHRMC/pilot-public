/**
 * DrawRow — thin wrapper switching between editable (draft) and readonly
 *
 * Location: apps/web/src/features/billing/components/DrawRow.tsx
 *
 * BILLING-B1 Part B — Payment Schedule Builder (UI spec §3.4, §4.1).
 *
 * Per §G: all structural editing is draft-only. Once the schedule is
 * active/completed/cancelled, the row renders read-only (DrawRowReadonly).
 * The deposit is the sequence=1 row — no special component (§G).
 *
 * React Compiler (§32): no hand-memoization; component is pure.
 */

"use client";

import type { PaymentScheduleLineResponse } from "../hooks/usePaymentSchedule";
import type { PaymentScheduleLineUpdate } from "../hooks/useUpdateScheduleLine";
import { DrawRowEditable } from "./DrawRowEditable";
import { DrawRowReadonly } from "./DrawRowReadonly";

interface DrawRowProps {
  line: PaymentScheduleLineResponse;
  /** When true (status='draft'), the row is editable. */
  isEditable: boolean;
  /** Editable-only: fired on blur with the partial PATCH payload. */
  onCommit?: (lineId: string, payload: PaymentScheduleLineUpdate) => void;
  /** Editable-only: fired when the remove button is clicked. */
  onRemove?: (lineId: string) => void;
  /** Editable-only: fired when the reorder handle is activated. */
  onReorder?: (lineId: string, direction: "up" | "down") => void;
  /** Editable-only: whether an optimistic mutation is in flight. */
  isPending?: boolean;
  /** Readonly-only: slot for the generate-invoice action (pending draws). */
  generateActionSlot?: React.ReactNode;
}

export function DrawRow({
  line,
  isEditable,
  onCommit,
  onRemove,
  onReorder,
  isPending,
  generateActionSlot,
}: DrawRowProps) {
  if (isEditable) {
    return (
      <DrawRowEditable
        line={line}
        onCommit={onCommit ?? (() => {})}
        onRemove={onRemove ?? (() => {})}
        onReorder={onReorder ?? (() => {})}
        isPending={isPending}
      />
    );
  }
  return (
    <DrawRowReadonly line={line} generateActionSlot={generateActionSlot} />
  );
}
