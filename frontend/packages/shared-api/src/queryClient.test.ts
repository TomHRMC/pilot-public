/**
 * createQueryClient unit tests
 *
 * Location: packages/shared-api/src/queryClient.test.ts
 */

import { describe, it, expect } from "vitest";
import { QueryClient } from "@tanstack/react-query";
import { createQueryClient } from "./queryClient";

describe("createQueryClient", () => {
  it("returns a QueryClient instance", () => {
    const client = createQueryClient();
    expect(client).toBeInstanceOf(QueryClient);
  });

  it("staleTime defaults to 300,000ms (5 minutes)", () => {
    const client = createQueryClient();
    const defaults = client.getDefaultOptions();
    expect(defaults.queries?.staleTime).toBe(300_000);
  });

  it("query retry is 1", () => {
    const client = createQueryClient();
    const defaults = client.getDefaultOptions();
    expect(defaults.queries?.retry).toBe(1);
  });

  it("mutation retry is 0", () => {
    const client = createQueryClient();
    const defaults = client.getDefaultOptions();
    expect(defaults.mutations?.retry).toBe(0);
  });
});
