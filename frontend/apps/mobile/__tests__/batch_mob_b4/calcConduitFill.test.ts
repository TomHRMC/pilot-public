/**
 * Unit tests — calcConduitFill (MOB-B4)
 *
 * Verifies the TypeScript offline engine mirrors nec_service.py _calc_conduit_fill()
 * using the same inputs, same lookup tables, same NEC Table 1 fill limits.
 */

import { calcConduitFill } from "../../features/nec-calcs/utils/calcConduitFill";

describe("calcConduitFill", () => {
  // ---------------------------------------------------------------------------
  // Core formula correctness — 3+ conductors (40% max)
  // ---------------------------------------------------------------------------

  it('EMT 3/4", 3× #12 → fill ≈ 7.49%, compliant', () => {
    const result = calcConduitFill({
      conduit_trade_size: "3/4",
      conduit_type: "EMT",
      wire_gauge: "12",
      num_conductors: 3,
    });

    // total_fill = 3 × 0.0133 = 0.0399 sq in
    // conduit area = 0.533 sq in
    // fill_pct = (0.0399 / 0.533) × 100 = 7.4878...
    expect(result.calc_type).toBe("conduit_fill");
    expect(result.fill_pct).toBeCloseTo(7.49, 1);
    expect(result.max_fill_pct).toBe(40);
    expect(result.is_compliant).toBe(true);
    expect(result.conduit_type).toBe("EMT");
    expect(result.num_conductors).toBe(3);
  });

  it("3+ conductors: 40% max fill limit applied", () => {
    // Pack 20× #4 in EMT 1" conduit: 20 × 0.0824 / 0.864 × 100 = 190.7% → fail
    const result = calcConduitFill({
      conduit_trade_size: "1",
      conduit_type: "EMT",
      wire_gauge: "4",
      num_conductors: 20,
    });

    expect(result.max_fill_pct).toBe(40);
    expect(result.is_compliant).toBe(false);
  });

  // ---------------------------------------------------------------------------
  // 2-conductor limit: 31%
  // ---------------------------------------------------------------------------

  it("2 conductors: 31% max fill limit applied", () => {
    const result = calcConduitFill({
      conduit_trade_size: "3/4",
      conduit_type: "EMT",
      wire_gauge: "12",
      num_conductors: 2,
    });

    expect(result.max_fill_pct).toBe(31);
    expect(result.num_conductors).toBe(2);
    // 2 × 0.0133 / 0.533 × 100 = 4.99% — compliant
    expect(result.is_compliant).toBe(true);
  });

  it("2 conductors → non-compliant when >31%", () => {
    // 2× #3 (0.0973 sq in) in EMT 1/2" (0.304 sq in): 2×0.0973/0.304×100 = 64% → fail
    const result = calcConduitFill({
      conduit_trade_size: "1/2",
      conduit_type: "EMT",
      wire_gauge: "3",
      num_conductors: 2,
    });

    expect(result.max_fill_pct).toBe(31);
    expect(result.is_compliant).toBe(false);
  });

  // ---------------------------------------------------------------------------
  // 1-conductor limit: 53%
  // ---------------------------------------------------------------------------

  it("1 conductor: 53% max fill limit applied", () => {
    const result = calcConduitFill({
      conduit_trade_size: "3/4",
      conduit_type: "EMT",
      wire_gauge: "12",
      num_conductors: 1,
    });

    expect(result.max_fill_pct).toBe(53);
    expect(result.num_conductors).toBe(1);
    // 1 × 0.0133 / 0.533 × 100 = 2.50% — compliant
    expect(result.is_compliant).toBe(true);
  });

  it("1 conductor → non-compliant when >53%", () => {
    // 1× #3/0 (0.266 sq in) in EMT 1/2" (0.304 sq in): 0.266/0.304×100 = 87.5% → fail
    const result = calcConduitFill({
      conduit_trade_size: "1/2",
      conduit_type: "EMT",
      wire_gauge: "3/0",
      num_conductors: 1,
    });

    expect(result.max_fill_pct).toBe(53);
    expect(result.is_compliant).toBe(false);
  });

  // ---------------------------------------------------------------------------
  // Conduit type handling
  // ---------------------------------------------------------------------------

  it("RMC conduit type uses RMC area table", () => {
    const rmc = calcConduitFill({
      conduit_trade_size: "3/4",
      conduit_type: "RMC",
      wire_gauge: "12",
      num_conductors: 3,
    });
    const emt = calcConduitFill({
      conduit_trade_size: "3/4",
      conduit_type: "EMT",
      wire_gauge: "12",
      num_conductors: 3,
    });

    // RMC 3/4" area = 0.549, EMT 3/4" = 0.533 — different fill %
    expect(rmc.conduit_type).toBe("RMC");
    expect(rmc.conduit_area_sq_in).toBeCloseTo(0.549, 3);
    expect(emt.conduit_area_sq_in).toBeCloseTo(0.533, 3);
    expect(rmc.fill_pct).not.toBeCloseTo(emt.fill_pct, 2);
  });

  it("PVC40 conduit type uses PVC40 area table", () => {
    const result = calcConduitFill({
      conduit_trade_size: "3/4",
      conduit_type: "PVC40",
      wire_gauge: "12",
      num_conductors: 3,
    });

    expect(result.conduit_type).toBe("PVC40");
    expect(result.conduit_area_sq_in).toBeCloseTo(0.508, 3);
  });

  it("defaults to EMT when conduit_type is omitted", () => {
    const result = calcConduitFill({
      conduit_trade_size: "3/4",
      wire_gauge: "12",
      num_conductors: 3,
    });

    expect(result.conduit_type).toBe("EMT");
  });

  // ---------------------------------------------------------------------------
  // Wire gauge normalization
  // ---------------------------------------------------------------------------

  it("accepts '12 AWG' gauge string", () => {
    const result = calcConduitFill({
      conduit_trade_size: "3/4",
      conduit_type: "EMT",
      wire_gauge: "12 AWG",
      num_conductors: 3,
    });

    expect(result.wire_gauge_normalized).toBe("12");
    expect(result.fill_pct).toBeCloseTo(7.49, 1);
  });

  // ---------------------------------------------------------------------------
  // Validation errors
  // ---------------------------------------------------------------------------

  it("throws for unknown wire gauge", () => {
    expect(() =>
      calcConduitFill({
        conduit_trade_size: "3/4",
        conduit_type: "EMT",
        wire_gauge: "7",
        num_conductors: 3,
      }),
    ).toThrow(/unknown wire gauge/i);
  });

  it("throws for unknown conduit size", () => {
    expect(() =>
      calcConduitFill({
        conduit_trade_size: "5",
        conduit_type: "EMT",
        wire_gauge: "12",
        num_conductors: 3,
      }),
    ).toThrow(/unknown conduit size/i);
  });

  it("throws for num_conductors < 1", () => {
    expect(() =>
      calcConduitFill({
        conduit_trade_size: "3/4",
        conduit_type: "EMT",
        wire_gauge: "12",
        num_conductors: 0,
      }),
    ).toThrow(/num_conductors must be ≥ 1/i);
  });

  // ---------------------------------------------------------------------------
  // NEC citation
  // ---------------------------------------------------------------------------

  it("returns NEC Chapter 9 Table 1 citation", () => {
    const result = calcConduitFill({
      conduit_trade_size: "3/4",
      conduit_type: "EMT",
      wire_gauge: "12",
      num_conductors: 3,
    });

    expect(result.nec_article).toBe("NEC Chapter 9 Table 1");
    expect(result.nec_citation).toContain("40%");
  });
});
