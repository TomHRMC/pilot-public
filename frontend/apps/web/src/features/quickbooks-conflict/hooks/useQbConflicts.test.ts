/**
 * useQbConflicts unit tests — FE-B9
 */

import { QB_CONFLICTS_QUERY_KEY } from "./useQbConflicts";
import type { QbConflictsParams } from "../types";

describe("useQbConflicts — query key", () => {
  it("constructs correct query key with entity_type param", () => {
    const params: QbConflictsParams = {
      entity_type: "invoice",
      status: "pending",
    };
    const key = QB_CONFLICTS_QUERY_KEY(params);
    expect(key).toEqual(["qb-conflicts", params]);
  });

  it("constructs correct query key with empty params", () => {
    const key = QB_CONFLICTS_QUERY_KEY({});
    expect(key).toEqual(["qb-conflicts", {}]);
  });

  it("query key differs by entity_type", () => {
    const k1 = QB_CONFLICTS_QUERY_KEY({ entity_type: "invoice" });
    const k2 = QB_CONFLICTS_QUERY_KEY({ entity_type: "customer" });
    expect(k1).not.toEqual(k2);
  });

  it("query key differs by status", () => {
    const k1 = QB_CONFLICTS_QUERY_KEY({ status: "pending" });
    const k2 = QB_CONFLICTS_QUERY_KEY({ status: "all" });
    expect(k1).not.toEqual(k2);
  });
});
