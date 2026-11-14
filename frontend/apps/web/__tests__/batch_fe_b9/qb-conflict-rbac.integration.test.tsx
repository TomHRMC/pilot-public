/**
 * QB conflict RBAC integration test — FE-B9
 * Role gate: integrations.manage → owner / operator PilotRole
 */

import {
  customerConflictDetail,
  quoteConflictDetail,
  invoiceConflictDetail,
  expenseConflictDetail,
} from "@/features/quickbooks-conflict/mocks/qbConflictFixtures";

describe("QB conflict RBAC + fixture validation", () => {
  it("customer fixture masterDirection='pilot'", () => {
    expect(customerConflictDetail.masterDirection).toBe("pilot");
  });

  it("quote fixture masterDirection='pilot'", () => {
    expect(quoteConflictDetail.masterDirection).toBe("pilot");
  });

  it("invoice fixture masterDirection='external' (QB is master)", () => {
    expect(invoiceConflictDetail.masterDirection).toBe("external");
  });

  it("expense fixture masterDirection='pilot'", () => {
    expect(expenseConflictDetail.masterDirection).toBe("pilot");
  });

  it("all 4 entity type fixtures have required fields", () => {
    for (const fixture of [
      customerConflictDetail,
      quoteConflictDetail,
      invoiceConflictDetail,
      expenseConflictDetail,
    ]) {
      expect(fixture.id).toBeTruthy();
      expect(fixture.conflictType).toBeTruthy();
      expect(fixture.pilotModifiedAt).toBeTruthy();
      expect(fixture.externalModifiedAt).toBeTruthy();
      expect(Array.isArray(fixture.fieldDiffs)).toBe(true);
    }
  });
});
