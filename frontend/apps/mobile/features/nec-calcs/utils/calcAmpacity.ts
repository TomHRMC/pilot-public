/**
 * NEC Table 310.12 Ampacity Calculator — Offline TypeScript Engine
 *
 * Location: apps/mobile/features/nec-calcs/utils/calcAmpacity.ts
 *
 * MIRRORS backend/services/nec_service.py _calc_ampacity() exactly.
 * Same input keys, same formula, same ampacity/bundling lookup tables.
 *
 * Note: Aluminum is not supported for MVP (same as backend).
 *
 * Per batch-mob-b4-design.md §F.3.
 */

// ---------------------------------------------------------------------------
// NEC Table 310.12 — Copper conductor ampacity at 75°C
// Copied verbatim from backend/services/nec_service.py _COPPER_AMPACITY_75C
// ---------------------------------------------------------------------------
const COPPER_AMPACITY_75C: Record<string, number> = {
  "14": 20.0,
  "12": 25.0,
  "10": 35.0,
  "8": 50.0,
  "6": 65.0,
  "4": 85.0,
  "3": 100.0,
  "2": 115.0,
  "1": 130.0,
  "1/0": 150.0,
  "2/0": 175.0,
  "3/0": 200.0,
  "4/0": 230.0,
  "250": 255.0,
  "300": 285.0,
  "350": 310.0,
  "400": 335.0,
  "500": 380.0,
};

// ---------------------------------------------------------------------------
// NEC Table 310.12 — Copper conductor ampacity at 90°C
// Copied verbatim from backend/services/nec_service.py _COPPER_AMPACITY_90C
// ---------------------------------------------------------------------------
const COPPER_AMPACITY_90C: Record<string, number> = {
  "14": 25.0,
  "12": 30.0,
  "10": 40.0,
  "8": 55.0,
  "6": 75.0,
  "4": 95.0,
  "3": 110.0,
  "2": 130.0,
  "1": 150.0,
  "1/0": 170.0,
  "2/0": 195.0,
  "3/0": 225.0,
  "4/0": 260.0,
  "250": 290.0,
  "300": 320.0,
  "350": 350.0,
  "400": 380.0,
  "500": 430.0,
};

// ---------------------------------------------------------------------------
// NEC Table 310.15(C)(1) — Bundling adjustment factors
// Copied verbatim from backend/services/nec_service.py _BUNDLING_ADJUSTMENT_FACTORS
// ---------------------------------------------------------------------------
// [minCount (inclusive), maxCount (exclusive), factor]
const BUNDLING_ADJUSTMENT_FACTORS: Array<[number, number, number]> = [
  [1, 4, 1.0], // 1–3 conductors: no derating
  [4, 7, 0.8], // 4–6 conductors: 80%
  [7, 10, 0.7], // 7–9 conductors: 70%
  [10, 21, 0.5], // 10–20 conductors: 50%
  [21, 31, 0.45], // 21–30 conductors: 45%
  [31, 41, 0.4], // 31–40 conductors: 40%
  [41, Infinity, 0.35], // 41+ conductors: 35%
];

/** Normalize gauge string — mirrors nec_service.py _normalize_gauge() */
function normalizeGauge(wireGauge: string): string {
  return wireGauge
    .trim()
    .toUpperCase()
    .replace(/\s*(AWG|GAUGE|GA\.?|#)/g, "")
    .trim();
}

/** Return NEC Table 310.15(C)(1) bundling adjustment factor */
function getBundlingFactor(conductorCount: number): number {
  for (const [min, max, factor] of BUNDLING_ADJUSTMENT_FACTORS) {
    if (conductorCount >= min && conductorCount < max) {
      return factor;
    }
  }
  return 0.35; // fallback for very large bundles
}

function round(val: number, decimals: number): number {
  return Math.round(val * Math.pow(10, decimals)) / Math.pow(10, decimals);
}

// ---------------------------------------------------------------------------
// Public interfaces
// ---------------------------------------------------------------------------

export interface AmpacityInputs {
  /** "copper" (required for MVP — aluminum not supported) */
  wire_material?: string;
  /** AWG gauge string (required) */
  wire_gauge: string;
  /** Conductor temperature rating: 60, 75, or 90 (default: 75) */
  temp_rating_c?: number;
  /** Number of current-carrying conductors in bundle (default: 3) */
  conductor_count?: number;
  /** Ambient temperature in °C (default: 30.0) */
  ambient_temp_c?: number;
}

export interface AmpacityResult {
  calc_type: "ampacity";
  /** Primary value — same as adjusted_ampacity */
  result_value: number;
  is_compliant: boolean;
  nec_article: string;
  nec_citation: string;
  base_ampacity: number;
  temp_correction_factor: number;
  bundling_adjustment_factor: number;
  adjusted_ampacity: number;
  wire_gauge: string;
  wire_gauge_normalized: string;
  wire_material: string;
  temp_rating_c: number;
  conductor_count: number;
  ambient_temp_c: number;
}

// ---------------------------------------------------------------------------
// calcAmpacity — mirrors nec_service.py _calc_ampacity() exactly
// ---------------------------------------------------------------------------

export function calcAmpacity(inputs: AmpacityInputs): AmpacityResult {
  const {
    wire_material = "copper",
    wire_gauge,
    temp_rating_c = 75,
    conductor_count = 3,
    ambient_temp_c = 30.0,
  } = inputs;

  if (!wire_gauge) throw new Error("wire_gauge is required");
  if (conductor_count < 1) throw new Error("conductor_count must be ≥ 1");

  // Aluminum not supported for MVP — same as backend
  if (wire_material.toLowerCase() !== "copper") {
    throw new Error(
      `Unsupported wire_material: ${wire_material}. Supported: 'copper'. Aluminum support is pending.`,
    );
  }

  const normalized = normalizeGauge(wire_gauge);

  // Select base ampacity table — mirrors backend logic exactly
  let ampacityTable: Record<string, number>;
  let tMax: number;
  if (temp_rating_c === 90) {
    ampacityTable = COPPER_AMPACITY_90C;
    tMax = 90.0;
  } else {
    // Default to 75°C for both 60°C and 75°C rated conductors
    ampacityTable = COPPER_AMPACITY_75C;
    tMax = temp_rating_c === 75 ? 75.0 : 60.0;
  }

  const baseAmpacity = ampacityTable[normalized];
  if (baseAmpacity == null) {
    throw new Error(
      `Unknown wire gauge: ${wire_gauge}. Use a standard AWG gauge.`,
    );
  }

  if (ambient_temp_c >= tMax) {
    throw new Error(
      `ambient_temp_c (${ambient_temp_c}°C) must be less than conductor rating (${tMax.toFixed(0)}°C)`,
    );
  }

  // Temperature correction factor — NEC Table 310.15(B)(1)
  // CF = sqrt((T_max - T_ambient) / (T_max - 30))
  const tempCorrectionFactor = Math.sqrt(
    (tMax - ambient_temp_c) / (tMax - 30.0),
  );

  // Bundling adjustment — NEC Table 310.15(C)(1)
  const bundlingAdjustmentFactor = getBundlingFactor(conductor_count);

  const adjustedAmpacity =
    baseAmpacity * tempCorrectionFactor * bundlingAdjustmentFactor;

  // Compliance: adjusted ampacity > 0 (always true with valid inputs)
  const isCompliant = adjustedAmpacity > 0;

  return {
    calc_type: "ampacity",
    result_value: round(adjustedAmpacity, 2),
    is_compliant: isCompliant,
    nec_article: "NEC Table 310.12",
    nec_citation:
      "NEC Table 310.12 — Allowable Ampacities for Insulated Conductors (THHN/THWN-2, copper)",
    base_ampacity: baseAmpacity,
    temp_correction_factor: round(tempCorrectionFactor, 4),
    bundling_adjustment_factor: bundlingAdjustmentFactor,
    adjusted_ampacity: round(adjustedAmpacity, 2),
    wire_gauge,
    wire_gauge_normalized: normalized,
    wire_material: wire_material.toLowerCase(),
    temp_rating_c,
    conductor_count,
    ambient_temp_c,
  };
}
