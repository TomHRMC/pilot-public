/**
 * NEC 210.19(A)(1) Voltage Drop Calculator — Offline TypeScript Engine
 *
 * Location: apps/mobile/features/nec-calcs/utils/calcVoltageDrop.ts
 *
 * MIRRORS backend/services/nec_service.py _calc_voltage_drop() exactly.
 * Same input keys, same formula, same AWG lookup table.
 *
 * DO NOT rename input fields — they must match backend key names exactly
 * so the same inputs object can be sent to either the online API or this
 * offline function without transformation.
 *
 * Per batch-mob-b4-design.md §F.3.
 */

// ---------------------------------------------------------------------------
// NEC Chapter 9 Table 9 — AWG circular mils (CM) lookup
// Copied verbatim from backend/services/nec_service.py _AWG_CIRCULAR_MILS
// ---------------------------------------------------------------------------
const AWG_CIRCULAR_MILS: Record<string, number> = {
  "14": 4110.0,
  "12": 6530.0,
  "10": 10380.0,
  "8": 16510.0,
  "6": 26240.0,
  "4": 41740.0,
  "3": 52620.0,
  "2": 66360.0,
  "1": 83690.0,
  "1/0": 105600.0,
  "2/0": 133100.0,
  "3/0": 167800.0,
  "4/0": 211600.0,
  "250": 250000.0,
  "300": 300000.0,
  "350": 350000.0,
  "400": 400000.0,
  "500": 500000.0,
};

const K_COPPER = 12.9;

/** Normalize gauge string — mirrors nec_service.py _normalize_gauge() */
function normalizeGauge(wireGauge: string): string {
  return wireGauge
    .trim()
    .toUpperCase()
    .replace(/\s*(AWG|GAUGE|GA\.?|#)/g, "")
    .trim();
}

function round(val: number, decimals: number): number {
  return Math.round(val * Math.pow(10, decimals)) / Math.pow(10, decimals);
}

// ---------------------------------------------------------------------------
// Public interfaces
// ---------------------------------------------------------------------------

export interface VoltageDropInputs {
  /** Load current in amps (required, > 0) */
  amperage: number;
  /** One-way run length in feet (required, > 0) */
  distance_feet: number;
  /** AWG gauge string, e.g. "12 AWG" or "12" (required) */
  wire_gauge: string;
  /** Supply voltage (default: 120) */
  voltage?: number;
  /** 1 for single-phase, 3 for three-phase (default: 1) */
  phase?: number;
}

export interface VoltageDropResult {
  calc_type: "voltage_drop";
  /** Primary value — same as voltage_drop */
  result_value: number;
  is_compliant: boolean;
  nec_article: string;
  nec_citation: string;
  voltage_drop: number;
  voltage_drop_pct: number;
  wire_gauge: string;
  wire_gauge_normalized: string;
  amperage: number;
  distance_feet: number;
  voltage: number;
  phase: number;
}

// ---------------------------------------------------------------------------
// calcVoltageDrop — mirrors nec_service.py _calc_voltage_drop() exactly
// ---------------------------------------------------------------------------

export function calcVoltageDrop(inputs: VoltageDropInputs): VoltageDropResult {
  const {
    amperage,
    distance_feet,
    wire_gauge,
    voltage = 120,
    phase = 1,
  } = inputs;

  if (amperage <= 0) throw new Error("amperage must be > 0");
  if (distance_feet <= 0) throw new Error("distance_feet must be > 0");
  if (!wire_gauge) throw new Error("wire_gauge is required");

  const normalized = normalizeGauge(wire_gauge);
  const circularMils = AWG_CIRCULAR_MILS[normalized];
  if (circularMils == null) {
    throw new Error(
      `Unknown wire gauge: ${wire_gauge}. Use a standard AWG gauge.`,
    );
  }

  // Single-phase: multiplier = 2.0; Three-phase: multiplier = 1.732 (√3)
  const multiplier = phase === 3 ? 1.732 : 2.0;
  const voltageDrop =
    (multiplier * K_COPPER * amperage * distance_feet) / circularMils;
  const voltageDropPct = (voltageDrop / voltage) * 100;
  const isCompliant = voltageDropPct <= 3.0;

  return {
    calc_type: "voltage_drop",
    result_value: round(voltageDrop, 4),
    is_compliant: isCompliant,
    nec_article: "NEC 210.19(A)(1)",
    nec_citation:
      "NEC 210.19(A)(1) Informational Note 4 — Voltage drop ≤ 3% recommended",
    voltage_drop: round(voltageDrop, 4),
    voltage_drop_pct: round(voltageDropPct, 4),
    wire_gauge,
    wire_gauge_normalized: normalized,
    amperage,
    distance_feet,
    voltage,
    phase,
  };
}
