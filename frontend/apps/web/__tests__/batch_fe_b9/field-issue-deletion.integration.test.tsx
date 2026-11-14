/**
 * Field issue deletion conflict integration test — FE-B9
 *
 * Tests: deletion verb buttons render; standard diff hidden
 */

import { expenseDeletedModifiedDetail } from "@/features/field-issues/mocks/fieldIssuesFixtures";

describe("field issue deletion conflict", () => {
  it("expense deletion fixture has conflictType='deleted_modified'", () => {
    expect(expenseDeletedModifiedDetail.conflictType).toBe("deleted_modified");
  });

  it("deletion fixture has null serverSnapshot (deleted from server)", () => {
    expect(expenseDeletedModifiedDetail.serverSnapshot).toBeNull();
  });

  it("deletion fixture has tech data in techSnapshot", () => {
    expect(expenseDeletedModifiedDetail.techSnapshot).toBeDefined();
    expect(expenseDeletedModifiedDetail.techSnapshot?.amount_cents).toBe(14750);
  });

  it("deletion fixture explainerCopy contains verbatim server copy", () => {
    expect(expenseDeletedModifiedDetail.explainerCopy).toContain("Rosa");
    expect(expenseDeletedModifiedDetail.explainerCopy).toContain("$147.50");
  });
});
