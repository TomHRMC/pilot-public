/**
 * Unit tests — calculateOffline router (MOB-B4)
 *
 * Verifies the calculateOffline() routing function dispatches correctly
 * and throws for unknown calc types.
 */

import { calculateOffline } from "../../features/nec-calcs/utils";

describe("calculateOffline", () => {
  it("routes 'voltage_drop' → calcVoltageDrop", () => {
    const result = calculateOffline("voltage_drop", {
      amperage: 20,
      distance_feet: 100,
      wire_gauge: "12",
      voltage: 120,
      phase: 1,
    });

    // (2 × 12.9 × 20 × 100) / 6530 = 7.902
    expect(result.calc_type).toBe("voltage_drop");
    expect(result.result_value).toBeCloseTo(7.902, 2);
    expect(result.is_compliant).toBe(false);
  });

  it("routes 'conduit_fill' → calcConduitFill", () => {
    const result = calculateOffline("conduit_fill", {
      conduit_trade_size: "3/4",
      conduit_type: "EMT",
      wire_gauge: "12",
      num_conductors: 3,
    });

    expect(result.calc_type).toBe("conduit_fill");
    expect(result.result_value).toBeCloseTo(7.49, 1);
    expect(result.is_compliant).toBe(true);
  });

  it("routes 'ampacity' → calcAmpacity", () => {
    const result = calculateOffline("ampacity", {
      wire_gauge: "12",
      temp_rating_c: 75,
      conductor_count: 3,
      ambient_temp_c: 30,
    });

    expect(result.calc_type).toBe("ampacity");
    expect(result.result_value).toBeCloseTo(25.0, 1);
    expect(result.is_compliant).toBe(true);
  });

  it("throws Error for unknown calc_type", () => {
    expect(() =>
      calculateOffline("unknown_type", { wire_gauge: "12" }),
    ).toThrow(/unknown calc_type/i);
  });

  it("throws Error for empty string calc_type", () => {
    expect(() => calculateOffline("", {})).toThrow(/unknown calc_type/i);
  });

  it("all three calc types return result_value, is_compliant, nec_citation", () => {
    const vd = calculateOffline("voltage_drop", {
      amperage: 20,
      distance_feet: 100,
      wire_gauge: "12",
      voltage: 120,
      phase: 1,
    });
    const cf = calculateOffline("conduit_fill", {
      conduit_trade_size: "3/4",
      wire_gauge: "12",
      num_conductors: 3,
    });
    const amp = calculateOffline("ampacity", {
      wire_gauge: "12",
    });

    for (const result of [vd, cf, amp]) {
      expect(typeof result.result_value).toBe("number");
      expect(typeof result.is_compliant).toBe("boolean");
      expect(typeof result.nec_citation).toBe("string");
      expect(result.nec_citation.length).toBeGreaterThan(0);
    }
  });
});
