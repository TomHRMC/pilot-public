/**
 * DrawRow Zod v4 validation schema
 *
 * Location: apps/web/src/features/billing/components/drawRowSchema.ts
 *
 * BILLING-B1 Part B — Payment Schedule Builder (UI spec §3.5–§3.8, §13.6).
 *
 * Mirrors the backend CHECKs (psl_basis_amount_chk, psl_trigger_detail_chk):
 *   - basis='percent'      → percent required, amount_cents null
 *   - basis='fixed_amount' → amount_cents required, percent null
 *   - trigger_type='date'      → trigger_date required
 *   - trigger_type='milestone' → milestone_label required
 *   - trigger_type='manual'    → neither required
 *
 * Rule 13 (§34): Zod v4 via zodResolver; top-level z.* helpers; unified `error`
 * param. This schema validates CLIENT-ENTERED form input only — API response
 * types come from @pilot/shared-types (never re-derive a backend shape as Zod).
 */

import { z } from "zod";

/**
 * The form values the DrawRow edits locally before PATCHing.
 * `percentInput` / `amountDollars` are string inputs (form-friendly); the
 * PATCH payload conversion to `percent` / `amount_cents` happens in the
 * component's submit handler, not in the schema.
 */
export const drawRowSchema = z
  .object({
    label: z
      .string({ error: "Draw label is required" })
      .min(1, "Draw label is required"),
    basis: z.enum(["percent", "fixed_amount"]),
    // String from the number input — validated conditionally below.
    // Required strings (not optional) so the RHF input/output types match;
    // defaultValues always provides these.
    percentInput: z.string(),
    // String dollars from the number input — validated conditionally below.
    amountDollars: z.string(),
    trigger_type: z.enum(["manual", "date", "milestone"]),
    trigger_date: z.string(),
    milestone_label: z.string(),
  })
  .superRefine((val, ctx) => {
    // ── basis XOR (psl_basis_amount_chk) ──────────────────────────────────
    if (val.basis === "percent") {
      const pct = parseFloat(val.percentInput);
      if (val.percentInput === "" || isNaN(pct)) {
        ctx.addIssue({
          code: "custom",
          path: ["percentInput"],
          message: "Enter a percent",
        });
      } else if (pct < 0 || pct > 100) {
        ctx.addIssue({
          code: "custom",
          path: ["percentInput"],
          message: "Percent must be between 0 and 100",
        });
      }
    }
    if (val.basis === "fixed_amount") {
      const dollars = parseFloat(val.amountDollars);
      if (val.amountDollars === "" || isNaN(dollars)) {
        ctx.addIssue({
          code: "custom",
          path: ["amountDollars"],
          message: "Enter a dollar amount",
        });
      } else if (dollars < 0) {
        ctx.addIssue({
          code: "custom",
          path: ["amountDollars"],
          message: "Amount cannot be negative",
        });
      }
    }

    // ── trigger detail (psl_trigger_detail_chk) ───────────────────────────
    if (val.trigger_type === "date" && val.trigger_date === "") {
      ctx.addIssue({
        code: "custom",
        path: ["trigger_date"],
        message: "Select a trigger date",
      });
    }
    if (val.trigger_type === "milestone" && val.milestone_label.trim() === "") {
      ctx.addIssue({
        code: "custom",
        path: ["milestone_label"],
        message: "Enter a milestone label",
      });
    }
  });

export type DrawRowFormValues = z.infer<typeof drawRowSchema>;
