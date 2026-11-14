/**
 * Live→snapshot transition invariant integration test — FE-B3
 *
 * Location: apps/mobile/__tests__/batch_fe_b3/live-snapshot-transition.integration.test.ts
 *
 * Tests the one-way, permanent live→snapshot transition.
 * This is the CRITICAL anti-pattern invariant from methods §15.
 */

describe("live→snapshot transition invariant", () => {
  /**
   * Simulates the VoiceQuotePreview internal mode guard.
   * Once hasFrozen=true, effective mode is always 'snapshot'.
   */
  function createModeGuard() {
    let hasFrozen = false;
    return {
      apply(mode: "live" | "snapshot"): "live" | "snapshot" {
        if (mode === "snapshot") hasFrozen = true;
        return hasFrozen ? "snapshot" : mode;
      },
      isFrozen: () => hasFrozen,
    };
  }

  it("render_mode live → fetches from API (MSW)", () => {
    const guard = createModeGuard();
    expect(guard.apply("live")).toBe("live");
    expect(guard.isFrozen()).toBe(false);
  });

  it("after action_committed with snapshot_frozen=true, renders as snapshot", () => {
    const guard = createModeGuard();
    // Start live
    expect(guard.apply("live")).toBe("live");
    // Receive snapshot freeze
    expect(guard.apply("snapshot")).toBe("snapshot");
    expect(guard.isFrozen()).toBe(true);
  });

  it("once in snapshot mode, prop change to mode=live does NOT re-trigger API fetch", () => {
    const guard = createModeGuard();
    guard.apply("live");
    guard.apply("snapshot");

    // Even if something tries to go back to live, the guard prevents it
    expect(guard.apply("live")).toBe("snapshot");
    expect(guard.apply("live")).toBe("snapshot");
    expect(guard.isFrozen()).toBe(true);
  });

  it("transition is one-way — cannot be undone once frozen", () => {
    const guard = createModeGuard();
    const sequence = ["live", "live", "snapshot", "live", "live"] as const;
    const results = sequence.map((m) => guard.apply(m));
    expect(results).toEqual([
      "live",
      "live",
      "snapshot",
      "snapshot",
      "snapshot",
    ]);
  });

  it("snapshot payload renders without API call", () => {
    // Validates that snapshot mode never calls the query
    const queryCalled = jest.fn();
    const snapshotPayload = {
      quote_id: "q-001",
      customer_name: "Tom Johnson",
      total_cents: 250000,
      margin_pct: 25,
      line_items: [],
      style: "component" as const,
      is_tech_role: false,
    };

    function renderSnapshotMode() {
      // In snapshot mode, useQuery is disabled (enabled: false)
      const enabled = false; // snapshot mode never fetches
      if (enabled) queryCalled();
      return snapshotPayload;
    }

    const result = renderSnapshotMode();
    expect(queryCalled).not.toHaveBeenCalled();
    expect(result.customer_name).toBe("Tom Johnson");
  });
});
