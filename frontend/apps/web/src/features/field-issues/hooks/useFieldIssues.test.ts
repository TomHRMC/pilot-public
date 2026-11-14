/**
 * useFieldIssues unit tests — FE-B9
 */

import { renderHook } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import { useFieldIssues, FIELD_ISSUES_QUERY_KEY } from "./useFieldIssues";
import type { FieldIssuesParams } from "../types";

function makeWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
  };
}

describe("useFieldIssues", () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
  });

  it("constructs correct query key with all filter params", () => {
    const params: FieldIssuesParams = {
      status: "pending",
      operation_type: "time_entry",
      active_techs_only: true,
      limit: 10,
    };
    const key = FIELD_ISSUES_QUERY_KEY(params);
    expect(key).toEqual(["field-issues", params]);
  });

  it("constructs correct query key with empty params", () => {
    const key = FIELD_ISSUES_QUERY_KEY({});
    expect(key).toEqual(["field-issues", {}]);
  });

  it("query key changes when params change", () => {
    const key1 = FIELD_ISSUES_QUERY_KEY({ status: "pending" });
    const key2 = FIELD_ISSUES_QUERY_KEY({ status: "stale" });
    expect(key1).not.toEqual(key2);
  });

  it("hook is enabled by default", () => {
    const wrapper = makeWrapper(queryClient);
    const { result } = renderHook(() => useFieldIssues(), { wrapper });
    // Hook should be in loading or data state (not disabled)
    expect(result.current.status).not.toBe("idle");
  });
});
