/**
 * Unit tests — calcAmpacity (MOB-B4)
 *
 * Verifies the TypeScript offline engine mirrors nec_service.py _calc_ampacity()
 * using the same lookup tables, temperature correction, and bundling factors.
 */

import { calcAmpacity } from "../../features/nec-calcs/utils/calcAmpacity";

describe("calcAmpacity", () => {
  // ---------------------------------------------------------------------------
  // Core formula — 75°C, 30°C ambient, 3 conductors (baseline)
  // ---------------------------------------------------------------------------

  it("#12 copper, 75°C, 30°C ambient, 3 conductors → adjusted 25A (no derating)", () => {
    const result = calcAmpacity({
      wire_material: "copper",
      wire_gauge: "12",
      temp_rating_c: 75,
      conductor_count: 3,
      ambient_temp_c: 30,
    });

    // base = 25A, CF = sqrt((75-30)/(75-30)) = 1.0, bundling = 1.0 → adjusted = 25.0A
    expect(result.calc_type).toBe("ampacity");
    expect(result.base_ampacity).toBe(25.0);
    expect(result.temp_correction_factor).toBeCloseTo(1.0, 4);
    expect(result.bundling_adjustment_factor).toBe(1.0);
    expect(result.adjusted_ampacity).toBeCloseTo(25.0, 1);
    expect(result.result_value).toBeCloseTo(25.0, 1);
    expect(result.is_compliant).toBe(true);
  });

  // ---------------------------------------------------------------------------
  // Bundling derating — NEC Table 310.15(C)(1)
  // ---------------------------------------------------------------------------

  it("4 conductors → bundling factor 0.80 applied", () => {
    const result = calcAmpacity({
      wire_gauge: "12",
      temp_rating_c: 75,
      conductor_count: 4,
      ambient_temp_c: 30,
    });

    expect(result.bundling_adjustment_factor).toBe(0.8);
    // 25A × 1.0 × 0.8 = 20A
    expect(result.adjusted_ampacity).toBeCloseTo(20.0, 1);
  });

  it("6 conductors → bundling factor 0.80 applied", () => {
    const result = calcAmpacity({
      wire_gauge: "12",
      temp_rating_c: 75,
      conductor_count: 6,
      ambient_temp_c: 30,
    });

    expect(result.bundling_adjustment_factor).toBe(0.8);
  });

  it("7 conductors → bundling factor 0.70 applied", () => {
    const result = calcAmpacity({
      wire_gauge: "12",
      temp_rating_c: 75,
      conductor_count: 7,
      ambient_temp_c: 30,
    });

    expect(result.bundling_adjustment_factor).toBe(0.7);
  });

  it("10 conductors → bundling factor 0.50 applied", () => {
    const result = calcAmpacity({
      wire_gauge: "12",
      temp_rating_c: 75,
      conductor_count: 10,
      ambient_temp_c: 30,
    });

    expect(result.bundling_adjustment_factor).toBe(0.5);
  });

  // ---------------------------------------------------------------------------
  // 90°C table vs 75°C table
  // ---------------------------------------------------------------------------

  it("90°C rating → uses COPPER_AMPACITY_90C table (30A for #12)", () => {
    const result = calcAmpacity({
      wire_gauge: "12",
      temp_rating_c: 90,
      conductor_count: 3,
      ambient_temp_c: 30,
    });

    // 90°C table: #12 = 30A
    expect(result.base_ampacity).toBe(30.0);
    expect(result.adjusted_ampacity).toBeCloseTo(30.0, 1);
  });

  it("75°C rating → uses COPPER_AMPACITY_75C table (25A for #12)", () => {
    const result = calcAmpacity({
      wire_gauge: "12",
      temp_rating_c: 75,
      conductor_count: 3,
      ambient_temp_c: 30,
    });

    expect(result.base_ampacity).toBe(25.0);
  });

  // ---------------------------------------------------------------------------
  // Temperature correction
  // ---------------------------------------------------------------------------

  it("elevated ambient temp (40°C) reduces adjusted ampacity", () => {
    const at30 = calcAmpacity({
      wire_gauge: "12",
      temp_rating_c: 75,
      conductor_count: 3,
      ambient_temp_c: 30,
    });
    const at40 = calcAmpacity({
      wire_gauge: "12",
      temp_rating_c: 75,
      conductor_count: 3,
      ambient_temp_c: 40,
    });

    // CF at 40°C = sqrt((75-40)/(75-30)) = sqrt(35/45) = 0.8819
    expect(at40.temp_correction_factor).toBeCloseTo(0.8819, 3);
    expect(at40.adjusted_ampacity).toBeLessThan(at30.adjusted_ampacity);
  });

  // ---------------------------------------------------------------------------
  // Wire gauge normalization
  // ---------------------------------------------------------------------------

  it("accepts '12 AWG' string and normalizes", () => {
    const result = calcAmpacity({
      wire_gauge: "12 AWG",
      temp_rating_c: 75,
      conductor_count: 3,
      ambient_temp_c: 30,
    });

    expect(result.wire_gauge_normalized).toBe("12");
    expect(result.base_ampacity).toBe(25.0);
  });

  // ---------------------------------------------------------------------------
  // Defaults
  // ---------------------------------------------------------------------------

  it("defaults wire_material to copper", () => {
    const result = calcAmpacity({
      wire_gauge: "12",
    });

    expect(result.wire_material).toBe("copper");
  });

  it("defaults conductor_count to 3", () => {
    const result = calcAmpacity({
      wire_gauge: "12",
    });

    expect(result.conductor_count).toBe(3);
    expect(result.bundling_adjustment_factor).toBe(1.0);
  });

  it("defaults ambient_temp_c to 30.0", () => {
    const result = calcAmpacity({
      wire_gauge: "12",
    });

    expect(result.ambient_temp_c).toBe(30.0);
    expect(result.temp_correction_factor).toBeCloseTo(1.0, 4);
  });

  // ---------------------------------------------------------------------------
  // Validation errors
  // ---------------------------------------------------------------------------

  it("throws for aluminum wire material (not supported for MVP)", () => {
    expect(() =>
      calcAmpacity({
        wire_material: "aluminum",
        wire_gauge: "12",
      }),
    ).toThrow(/unsupported wire_material/i);
  });

  it("throws for unknown wire gauge", () => {
    expect(() =>
      calcAmpacity({
        wire_gauge: "7",
      }),
    ).toThrow(/unknown wire gauge/i);
  });

  it("throws for conductor_count < 1", () => {
    expect(() =>
      calcAmpacity({
        wire_gauge: "12",
        conductor_count: 0,
      }),
    ).toThrow(/conductor_count must be ≥ 1/i);
  });

  it("throws when ambient_temp >= conductor rating", () => {
    expect(() =>
      calcAmpacity({
        wire_gauge: "12",
        temp_rating_c: 75,
        ambient_temp_c: 75,
      }),
    ).toThrow(/ambient_temp_c/i);
  });

  // ---------------------------------------------------------------------------
  // NEC citation
  // ---------------------------------------------------------------------------

  it("returns NEC Table 310.12 article and citation", () => {
    const result = calcAmpacity({ wire_gauge: "12" });

    expect(result.nec_article).toBe("NEC Table 310.12");
    expect(result.nec_citation).toContain("THHN/THWN-2");
  });
});
