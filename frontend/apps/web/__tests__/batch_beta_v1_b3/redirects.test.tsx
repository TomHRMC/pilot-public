/**
 * Redirect tests — BETA-B3
 *
 * Location: apps/web/__tests__/batch_beta_v1_b3/redirects.test.tsx
 *
 * Tests that /operations and /sync redirect pages call next/navigation redirect()
 * with the correct target paths.
 */

import { describe, it, expect, vi } from "vitest";

// Mock next/navigation before importing redirect pages
const redirectMock = vi.fn();
vi.mock("next/navigation", () => ({
  redirect: redirectMock,
}));

describe("/operations and /sync redirects", () => {
  it("/operations redirects to /settings/operations/field-operations", async () => {
    redirectMock.mockClear();
    // Dynamic import to ensure the mock is in place
    await import("../../src/app/(authed)/operations/page");
    // redirect() is called at module load / render time for Next.js server components
    // We verify the module exports a function and the redirect target is correct
    const mod = await import("../../src/app/(authed)/operations/page");
    expect(mod.default).toBeDefined();
    // Calling the page function should invoke redirect
    try {
      mod.default();
    } catch {
      // redirect() throws in Next.js — that's expected
    }
    expect(redirectMock).toHaveBeenCalledWith(
      "/settings/operations/field-operations",
    );
  });

  it("/sync redirects to /settings/sync-storage/background-sync", async () => {
    redirectMock.mockClear();
    const mod = await import("../../src/app/(authed)/sync/page");
    expect(mod.default).toBeDefined();
    try {
      mod.default();
    } catch {
      // redirect() throws in Next.js — that's expected
    }
    expect(redirectMock).toHaveBeenCalledWith(
      "/settings/sync-storage/background-sync",
    );
  });
});
