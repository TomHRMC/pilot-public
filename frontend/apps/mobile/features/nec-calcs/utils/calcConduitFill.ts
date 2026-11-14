/**
 * NEC Chapter 9 Table 1 Conduit Fill Calculator — Offline TypeScript Engine
 *
 * Location: apps/mobile/features/nec-calcs/utils/calcConduitFill.ts
 *
 * MIRRORS backend/services/nec_service.py _calc_conduit_fill() exactly.
 * Same input keys, same formula, same conduit/wire area lookup tables.
 *
 * Per batch-mob-b4-design.md §F.3.
 */

// ---------------------------------------------------------------------------
// NEC Chapter 9 Table 5 — THHN/THWN-2 conductor outer area (sq in)
// Copied verbatim from backend/services/nec_service.py _AWG_WIRE_AREA_SQ_IN
// ---------------------------------------------------------------------------
const AWG_WIRE_AREA_SQ_IN: Record<string, number> = {
  "14": 0.0097,
  "12": 0.0133,
  "10": 0.0211,
  "8": 0.0366,
  "6": 0.0507,
  "4": 0.0824,
  "3": 0.0973,
  "2": 0.1158,
  "1": 0.1562,
  "1/0": 0.1855,
  "2/0": 0.2223,
  "3/0": 0.266,
  "4/0": 0.3197,
  "250": 0.3904,
  "300": 0.4608,
  "350": 0.5281,
  "400": 0.5958,
  "500": 0.7297,
};

// ---------------------------------------------------------------------------
// NEC Chapter 9 Table 4 — Conduit internal cross-sectional areas (sq in)
// Copied verbatim from backend/services/nec_service.py _CONDUIT_AREA_SQ_IN
// ---------------------------------------------------------------------------
const CONDUIT_AREA_SQ_IN: Record<string, Record<string, number>> = {
  EMT: {
    "1/2": 0.304,
    "3/4": 0.533,
    "1": 0.864,
    "1-1/4": 1.496,
    "1-1/2": 2.036,
    "2": 3.356,
    "2-1/2": 5.858,
    "3": 8.846,
    "3-1/2": 11.545,
    "4": 14.753,
  },
  RMC: {
    "1/2": 0.314,
    "3/4": 0.549,
    "1": 0.887,
    "1-1/4": 1.526,
    "1-1/2": 2.071,
    "2": 3.408,
    "2-1/2": 5.452,
    "3": 8.688,
    "3-1/2": 11.663,
    "4": 14.854,
  },
  PVC40: {
    "1/2": 0.285,
    "3/4": 0.508,
    "1": 0.832,
    "1-1/4": 1.453,
    "1-1/2": 1.986,
    "2": 3.291,
    "2-1/2": 4.695,
    "3": 7.268,
    "3-1/2": 9.737,
    "4": 12.554,
  },
};

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

export interface ConduitFillInputs {
  /** Conduit trade size, e.g. "3/4" (required) */
  conduit_trade_size: string;
  /** Conduit type: "EMT", "RMC", or "PVC40" (default: "EMT") */
  conduit_type?: string;
  /** AWG gauge string (required) */
  wire_gauge: string;
  /** Number of conductors (required, ≥ 1) */
  num_conductors: number;
}

export interface ConduitFillResult {
  calc_type: "conduit_fill";
  /** Primary value — same as fill_pct */
  result_value: number;
  is_compliant: boolean;
  nec_article: string;
  nec_citation: string;
  fill_pct: number;
  max_fill_pct: number;
  total_fill_sq_in: number;
  conduit_area_sq_in: number;
  wire_gauge: string;
  wire_gauge_normalized: string;
  conduit_trade_size: string;
  conduit_type: string;
  num_conductors: number;
}

// ---------------------------------------------------------------------------
// calcConduitFill — mirrors nec_service.py _calc_conduit_fill() exactly
// ---------------------------------------------------------------------------

export function calcConduitFill(inputs: ConduitFillInputs): ConduitFillResult {
  const {
    conduit_trade_size,
    conduit_type = "EMT",
    wire_gauge,
    num_conductors,
  } = inputs;

  if (!conduit_trade_size)
    throw new Error("conduit_trade_size is required (e.g., '3/4')");
  if (!wire_gauge) throw new Error("wire_gauge is required");
  if (num_conductors < 1) throw new Error("num_conductors must be ≥ 1");

  const normalized = normalizeGauge(wire_gauge);
  const wireArea = AWG_WIRE_AREA_SQ_IN[normalized];
  if (wireArea == null) {
    throw new Error(
      `Unknown wire gauge: ${wire_gauge}. Use a standard AWG gauge.`,
    );
  }

  // Normalize conduit type key (uppercase); default to EMT if not recognized
  const conduitTypeKey =
    conduit_type.toUpperCase() in CONDUIT_AREA_SQ_IN
      ? conduit_type.toUpperCase()
      : "EMT";
  const conduitSizes = CONDUIT_AREA_SQ_IN[conduitTypeKey];
  const conduitArea = conduitSizes[conduit_trade_size];
  if (conduitArea == null) {
    const available = Object.keys(conduitSizes).join(", ");
    throw new Error(
      `Unknown conduit size: ${conduit_trade_size} for ${conduitTypeKey}. Available: ${available}`,
    );
  }

  // NEC Chapter 9 Table 1 fill limits
  let maxFillPct: number;
  if (num_conductors === 1) {
    maxFillPct = 53.0;
  } else if (num_conductors === 2) {
    maxFillPct = 31.0;
  } else {
    maxFillPct = 40.0;
  }

  const totalFill = wireArea * num_conductors;
  const fillPct = (totalFill / conduitArea) * 100;
  const isCompliant = fillPct <= maxFillPct;

  return {
    calc_type: "conduit_fill",
    result_value: round(fillPct, 4),
    is_compliant: isCompliant,
    nec_article: "NEC Chapter 9 Table 1",
    nec_citation: `NEC Chapter 9 Table 1 — Max fill ${maxFillPct.toFixed(0)}% for ${num_conductors} conductor(s)`,
    fill_pct: round(fillPct, 4),
    max_fill_pct: maxFillPct,
    total_fill_sq_in: round(totalFill, 6),
    conduit_area_sq_in: round(conduitArea, 6),
    wire_gauge,
    wire_gauge_normalized: normalized,
    conduit_trade_size,
    conduit_type: conduitTypeKey,
    num_conductors,
  };
}
