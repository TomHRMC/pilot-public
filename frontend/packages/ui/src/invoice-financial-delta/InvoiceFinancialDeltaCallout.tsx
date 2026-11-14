/**
 * InvoiceFinancialDeltaCallout — QB invoice conflict financial summary
 *
 * Location: packages/ui/src/invoice-financial-delta/InvoiceFinancialDeltaCallout.tsx
 *
 * Established FE-B9. Injected via renderDomainSpecificFields slot on
 * <IntegrationConflictResolver> for invoice entity type conflicts only.
 *
 * Renders:
 *   - Financial delta between Pilot and QB amounts
 *   - AR impact description
 *   - Tax-period warning banner (only when taxPeriodWarning non-null)
 *   - QB deep-link (only when qbTransactionUrl non-null)
 *
 * RULE 7: Lives in packages/ui — reusable by future financial integrations.
 * RULE 0: All tokens from pilotPreset. Zero hex values.
 *
 * Tokens used:
 *   bg-alert-50 border-alert-200 — callout background
 *   text-alert-700 — tax-period warning text
 *   text-body-lg font-semibold — financial delta amount
 *   text-caption text-neutral-600 — meta labels
 */

import React from "react";

// ─── Types ─────────────────────────────────────────────────────────────────────

export interface InvoiceFinancialDeltaCalloutProps {
  /** Pilot's total amount in cents */
  pilotAmountCents: number;
  /** QuickBooks' total amount in cents */
  qbAmountCents: number;
  /** Delta = qbAmountCents - pilotAmountCents. Positive = QB higher; negative = Pilot higher */
  financialDeltaCents: number;
  /** Server-generated AR impact description — render verbatim */
  arImpactDescription: string;
  /** null → no tax-period banner rendered */
  taxPeriodWarning: string | null;
  /** null → no QB deep-link rendered */
  qbTransactionUrl: string | null;
  /** Test ID for e2e and unit tests */
  testID?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDollars(cents: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(cents / 100);
}

// ─── Component ────────────────────────────────────────────────────────────────

export function InvoiceFinancialDeltaCallout({
  pilotAmountCents,
  qbAmountCents,
  financialDeltaCents,
  arImpactDescription,
  taxPeriodWarning,
  qbTransactionUrl,
  testID,
}: InvoiceFinancialDeltaCalloutProps) {
  const deltaIsPositive = financialDeltaCents > 0;
  const deltaLabel = deltaIsPositive
    ? `QB is ${formatDollars(Math.abs(financialDeltaCents))} higher`
    : financialDeltaCents < 0
      ? `Pilot is ${formatDollars(Math.abs(financialDeltaCents))} higher`
      : "No financial difference";

  return (
    <div
      className="space-y-3 rounded-md border border-alert-200 bg-alert-50 p-4"
      data-testid={testID ?? "invoice-financial-delta-callout"}
    >
      {/* Tax-period warning banner — renders only when non-null */}
      {taxPeriodWarning !== null && (
        <div
          className="flex items-start gap-2 rounded border border-alert-200 bg-alert-50 px-3 py-2 text-caption text-alert-700"
          role="alert"
          data-testid="tax-period-warning-banner"
        >
          <span aria-hidden="true">⚠</span>
          <span>
            This invoice spans tax period <strong>{taxPeriodWarning}</strong>.
            Resolution may affect filed returns. Consider consulting your
            bookkeeper.
          </span>
        </div>
      )}

      {/* Financial delta summary */}
      <div className="space-y-1">
        <p className="text-caption font-medium text-neutral-600 uppercase tracking-wide">
          Financial Impact
        </p>
        <div className="flex items-baseline gap-3">
          <span
            className="text-body-lg font-semibold text-neutral-900"
            data-testid="financial-delta-amount"
          >
            {deltaLabel}
          </span>
        </div>

        {/* Side-by-side amounts */}
        <div className="flex gap-6 pt-1">
          <div>
            <p className="text-caption text-neutral-600">Pilot</p>
            <p
              className="text-body font-medium text-neutral-900"
              data-testid="pilot-amount"
            >
              {formatDollars(pilotAmountCents)}
            </p>
          </div>
          <div>
            <p className="text-caption text-neutral-600">QuickBooks</p>
            <p
              className="text-body font-medium text-neutral-900"
              data-testid="qb-amount"
            >
              {formatDollars(qbAmountCents)}
            </p>
          </div>
        </div>
      </div>

      {/* AR impact — server-generated copy rendered verbatim */}
      <p
        className="text-caption text-neutral-600"
        data-testid="ar-impact-description"
      >
        {arImpactDescription}
      </p>

      {/* QB deep-link — renders only when non-null */}
      {qbTransactionUrl !== null && (
        <a
          href={qbTransactionUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-caption text-brand-600 hover:text-brand-700 hover:underline"
          data-testid="qb-transaction-link"
        >
          View in QuickBooks →
        </a>
      )}
    </div>
  );
}
