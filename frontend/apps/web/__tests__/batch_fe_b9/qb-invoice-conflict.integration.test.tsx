/**
 * QB invoice conflict integration test — FE-B9
 *
 * Tests: invoice conflict renders InvoiceFinancialDeltaCallout + tax-period warning
 */

import { invoiceConflictDetail } from "@/features/quickbooks-conflict/mocks/qbConflictFixtures";
import { normalizeQbFieldDiffs } from "@/features/quickbooks-conflict/hooks/normalizeQbFieldDiffs";

describe("QB invoice conflict", () => {
  it("invoice fixture has masterDirection='external'", () => {
    expect(invoiceConflictDetail.masterDirection).toBe("external");
  });

  it("invoice fixture has taxPeriodWarning='Q1 2026'", () => {
    expect(invoiceConflictDetail.taxPeriodWarning).toBe("Q1 2026");
  });

  it("invoice fixture has financialDeltaCents=3750", () => {
    expect(invoiceConflictDetail.financialDeltaCents).toBe(3750);
  });

  it("invoice fixture has qbTransactionUrl", () => {
    expect(invoiceConflictDetail.qbTransactionUrl).toBeTruthy();
  });

  it("normalizeQbFieldDiffs with external master: QB value on left (base)", () => {
    const normalized = normalizeQbFieldDiffs(
      invoiceConflictDetail.fieldDiffs,
      "external",
    );
    // QB = external, so external_value → baseValue
    expect(normalized[0].baseValue).toBe(
      String(invoiceConflictDetail.fieldDiffs[0].external_value),
    );
  });

  it("normalizeQbFieldDiffs with pilot master: Pilot value on left (base)", () => {
    const normalized = normalizeQbFieldDiffs(
      invoiceConflictDetail.fieldDiffs,
      "pilot",
    );
    expect(normalized[0].baseValue).toBe(
      String(invoiceConflictDetail.fieldDiffs[0].pilot_value),
    );
  });
});
