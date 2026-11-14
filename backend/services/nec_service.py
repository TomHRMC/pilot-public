"""
NEC 2023 Calculation Service — MOB-B0

Pure calculation functions for NEC electrical code compliance checks.
No database, no Ollama, no session context. Pure physics + NEC table lookups.

Used by:
  - POST /api/v1/nec/calculate (REST endpoint — MOB-B0)
  - services/voice_action_router.py calculate_nec_voltage_drop handler (voice pipeline)
  - services/voice_action_router.py calculate_conduit_fill handler (voice pipeline)

NEC 2023 references:
  - Voltage Drop: NEC 210.19(A)(1) Informational Note 4
  - Conduit Fill: NEC Chapter 9, Table 1 + Table 5
  - Ampacity: NEC Table 310.12 (THHN/THWN-2, 60°C/75°C/90°C copper/aluminum)

NEC® and National Electrical Code® are registered trademarks of the National Fire
Protection Association (NFPA). Values below are a minimal subset of reference data
cited for calculation purposes only; consult NFPA 70 (2023) for the authoritative text.
"""

import math
import re
from dataclasses import dataclass
from dataclasses import field as dc_field

# ---------------------------------------------------------------------------
# NEC Chapter 9 Table 8 — AWG circular mils (CM) lookup
# Used in voltage drop formula: V_D = (2 × K × I × D) / CM
# K = 12.9 for copper (DC constant)
# ---------------------------------------------------------------------------
_AWG_CIRCULAR_MILS: dict[str, float] = {
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
}

# ---------------------------------------------------------------------------
# NEC Chapter 9 Table 5 — THHN/THWN-2 conductor outer area (sq in)
# ---------------------------------------------------------------------------
_AWG_WIRE_AREA_SQ_IN: dict[str, float] = {
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
    "3/0": 0.2660,
    "4/0": 0.3197,
    "250": 0.3904,
    "300": 0.4608,
    "350": 0.5281,
    "400": 0.5958,
    "500": 0.7297,
}

# ---------------------------------------------------------------------------
# NEC Chapter 9 Table 4 — Conduit internal cross-sectional areas (sq in)
# ---------------------------------------------------------------------------
_CONDUIT_AREA_SQ_IN: dict[str, dict[str, float]] = {
    "EMT": {
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
    "RMC": {
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
    "PVC40": {
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
}

# ---------------------------------------------------------------------------
# NEC Table 310.12 — Copper conductor ampacity at 75°C (most common residential/commercial)
# Key: AWG gauge string → base ampacity at 75°C, 30°C ambient, 3 or fewer conductors
# ---------------------------------------------------------------------------
_COPPER_AMPACITY_75C: dict[str, float] = {
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
}

_COPPER_AMPACITY_90C: dict[str, float] = {
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
}

# ---------------------------------------------------------------------------
# NEC Table 310.15(C)(1) — Bundling adjustment factors
# Applied when more than 3 current-carrying conductors are bundled together
# ---------------------------------------------------------------------------
_BUNDLING_ADJUSTMENT_FACTORS: list[tuple[range, float]] = [
    (range(1, 4), 1.00),  # 1–3 conductors: no derating
    (range(4, 7), 0.80),  # 4–6 conductors: 80%
    (range(7, 10), 0.70),  # 7–9 conductors: 70%
    (range(10, 21), 0.50),  # 10–20 conductors: 50%
    (range(21, 31), 0.45),  # 21–30 conductors: 45%
    (range(31, 41), 0.40),  # 31–40 conductors: 40%
    (range(41, 10000), 0.35),  # 41+ conductors: 35%
]


def _normalize_gauge(wire_gauge: str) -> str:
    """Normalize wire gauge input to match lookup table keys.

    Handles inputs like "12 AWG", "12awg", "12 gauge", "#12", "12".
    """
    gauge = wire_gauge.strip().upper()
    gauge = re.sub(r"\s*(AWG|GAUGE|GA\.?|#)", "", gauge).strip()
    return gauge


def _get_bundling_factor(conductor_count: int) -> float:
    """Return NEC Table 310.15(C)(1) bundling adjustment factor."""
    for rng, factor in _BUNDLING_ADJUSTMENT_FACTORS:
        if conductor_count in rng:
            return factor
    return 0.35  # fallback for very large bundles


# ---------------------------------------------------------------------------
# NecCalcResult — returned by all calculate() functions
# ---------------------------------------------------------------------------


@dataclass
class NecCalcResult:
    """Structured NEC calculation result with NEC citation."""

    calc_type: str
    result_value: (
        float  # Primary calculated value (voltage_drop, fill_pct, adjusted_ampacity)
    )
    is_compliant: bool  # Pass/fail against NEC limit
    nec_article: str  # e.g., "NEC 210.19(A)(1)"
    nec_citation: str  # Full citation text
    details: dict = dc_field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage and API response."""
        return {
            "calc_type": self.calc_type,
            "result_value": self.result_value,
            "is_compliant": self.is_compliant,
            "nec_article": self.nec_article,
            "nec_citation": self.nec_citation,
            **self.details,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def calculate(calc_type: str, inputs: dict) -> NecCalcResult:
    """Route to the appropriate NEC 2023 calculation function.

    Args:
        calc_type: One of 'voltage_drop', 'conduit_fill', 'ampacity'
        inputs: Calculation inputs dict (validated by caller schema or voice handler)

    Returns:
        NecCalcResult with result values and NEC citation

    Raises:
        ValueError: If calc_type is unsupported or inputs are invalid
    """
    if calc_type == "voltage_drop":
        return _calc_voltage_drop(inputs)
    elif calc_type == "conduit_fill":
        return _calc_conduit_fill(inputs)
    elif calc_type == "ampacity":
        return _calc_ampacity(inputs)
    else:
        raise ValueError(
            f"Unsupported calc_type: {calc_type!r}. "
            "Valid values: 'voltage_drop', 'conduit_fill', 'ampacity'"
        )


# ---------------------------------------------------------------------------
# Voltage Drop — NEC 210.19(A)(1) Informational Note 4
# ---------------------------------------------------------------------------


def _calc_voltage_drop(inputs: dict) -> NecCalcResult:
    """NEC single/three-phase voltage drop calculation.

    Single-phase formula:  V_D = (2 × K × I × D) / CM
    Three-phase formula:   V_D = (1.732 × K × I × D) / CM
    K = 12.9 (copper DC constant), I = amperage, D = one-way distance, CM = circular mils.

    Compliance: ≤ 3% recommended (NEC 210.19 informational note).

    Inputs dict keys:
        amperage (float): Load current in amps (required, > 0)
        distance_feet (float): One-way run length in feet (required, > 0)
        wire_gauge (str): AWG gauge string, e.g. "12 AWG" or "12" (required)
        voltage (float): Supply voltage (default: 120.0)
        phase (int): 1 or 3 (default: 1)

    Raises:
        ValueError: On invalid inputs or unsupported gauge
    """
    K_COPPER = 12.9

    # Parse inputs
    try:
        amperage = float(inputs.get("amperage", 0))
        distance_feet = float(inputs.get("distance_feet") or inputs.get("distance", 0))
        wire_gauge_raw = str(inputs.get("wire_gauge", inputs.get("wire", ""))).strip()
        voltage = float(inputs.get("voltage", 120.0))
        phase = int(inputs.get("phase", 1))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid voltage drop inputs: {e}") from e

    if amperage <= 0:
        raise ValueError("amperage must be > 0")
    if distance_feet <= 0:
        raise ValueError("distance_feet must be > 0")
    if not wire_gauge_raw:
        raise ValueError("wire_gauge is required")

    normalized = _normalize_gauge(wire_gauge_raw)
    circular_mils = _AWG_CIRCULAR_MILS.get(normalized)
    if circular_mils is None:
        available = ", ".join(
            sorted(
                _AWG_CIRCULAR_MILS.keys(),
                key=lambda x: (
                    float(x.replace("/", "."))
                    if "/" in x
                    else float(x)
                    if x.isdigit()
                    else 1000
                ),
            )
        )
        raise ValueError(
            f"Unknown wire gauge: {wire_gauge_raw!r}. Supported gauges: {available}"
        )

    multiplier = 1.732 if phase == 3 else 2.0
    voltage_drop = (multiplier * K_COPPER * amperage * distance_feet) / circular_mils
    voltage_drop_pct = (voltage_drop / voltage) * 100
    is_compliant = voltage_drop_pct <= 3.0

    return NecCalcResult(
        calc_type="voltage_drop",
        result_value=round(voltage_drop, 4),
        is_compliant=is_compliant,
        nec_article="NEC 210.19(A)(1)",
        nec_citation="NEC 210.19(A)(1) Informational Note 4 — Voltage drop ≤ 3% recommended",
        details={
            "voltage_drop": round(voltage_drop, 4),
            "voltage_drop_pct": round(voltage_drop_pct, 4),
            "wire_gauge": wire_gauge_raw,
            "wire_gauge_normalized": normalized,
            "amperage": amperage,
            "distance_feet": distance_feet,
            "voltage": voltage,
            "phase": phase,
        },
    )


# ---------------------------------------------------------------------------
# Conduit Fill — NEC Chapter 9 Table 1 + Table 5
# ---------------------------------------------------------------------------


def _calc_conduit_fill(inputs: dict) -> NecCalcResult:
    """NEC conduit fill calculation.

    NEC Chapter 9 Table 1 max fill rules:
        1 conductor  → 53% max
        2 conductors → 31% max
        3+ conductors → 40% max

    Inputs dict keys:
        conduit_trade_size (str): e.g., "3/4" (required)
        conduit_type (str): "EMT", "RMC", or "PVC40" (default: "EMT")
        wire_gauge (str): AWG gauge string (required)
        num_conductors (int): Number of conductors (required, ≥ 1)

    Raises:
        ValueError: On invalid inputs or unsupported conduit/gauge
    """
    try:
        conduit_trade_size = str(
            inputs.get("conduit_trade_size", inputs.get("conduit_size", ""))
        ).strip()
        conduit_type = str(inputs.get("conduit_type", "EMT")).strip().upper()
        wire_gauge_raw = str(inputs.get("wire_gauge", inputs.get("wire", ""))).strip()
        num_conductors = int(inputs.get("num_conductors", inputs.get("conductors", 0)))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid conduit fill inputs: {e}") from e

    if not conduit_trade_size:
        raise ValueError("conduit_trade_size is required (e.g., '3/4')")
    if not wire_gauge_raw:
        raise ValueError("wire_gauge is required")
    if num_conductors < 1:
        raise ValueError("num_conductors must be ≥ 1")

    normalized = _normalize_gauge(wire_gauge_raw)
    wire_area = _AWG_WIRE_AREA_SQ_IN.get(normalized)
    if wire_area is None:
        raise ValueError(
            f"Unknown wire gauge: {wire_gauge_raw!r}. Use a standard AWG gauge."
        )

    conduit_type_key = conduit_type if conduit_type in _CONDUIT_AREA_SQ_IN else "EMT"
    conduit_sizes = _CONDUIT_AREA_SQ_IN[conduit_type_key]
    conduit_area = conduit_sizes.get(conduit_trade_size)
    if conduit_area is None:
        available = ", ".join(sorted(conduit_sizes.keys()))
        raise ValueError(
            f"Unknown conduit size: {conduit_trade_size!r} for {conduit_type_key}. "
            f"Available: {available}"
        )

    # NEC Chapter 9 Table 1 fill limits
    if num_conductors == 1:
        max_fill_pct = 53.0
    elif num_conductors == 2:
        max_fill_pct = 31.0
    else:
        max_fill_pct = 40.0

    total_fill = wire_area * num_conductors
    fill_pct = (total_fill / conduit_area) * 100
    is_compliant = fill_pct <= max_fill_pct

    return NecCalcResult(
        calc_type="conduit_fill",
        result_value=round(fill_pct, 4),
        is_compliant=is_compliant,
        nec_article="NEC Chapter 9 Table 1",
        nec_citation=(
            f"NEC Chapter 9 Table 1 — Max fill {max_fill_pct:.0f}% "
            f"for {num_conductors} conductor(s)"
        ),
        details={
            "fill_pct": round(fill_pct, 4),
            "max_fill_pct": max_fill_pct,
            "total_fill_sq_in": round(total_fill, 6),
            "conduit_area_sq_in": round(conduit_area, 6),
            "wire_gauge": wire_gauge_raw,
            "wire_gauge_normalized": normalized,
            "conduit_trade_size": conduit_trade_size,
            "conduit_type": conduit_type_key,
            "num_conductors": num_conductors,
        },
    )


# ---------------------------------------------------------------------------
# Ampacity — NEC Table 310.12 (copper THHN/THWN-2)
# ---------------------------------------------------------------------------


def _calc_ampacity(inputs: dict) -> NecCalcResult:
    """NEC ampacity calculation with temperature correction and bundling derating.

    Base ampacity from NEC Table 310.12 (copper, 75°C or 90°C).
    Temperature correction: NEC Table 310.15(B)(1).
    Bundling adjustment: NEC Table 310.15(C)(1).

    Inputs dict keys:
        wire_material (str): "copper" or "aluminum" (default: "copper")
        wire_gauge (str): AWG gauge string (required)
        temp_rating_c (int): Conductor temperature rating: 60, 75, or 90 (default: 75)
        conductor_count (int): Number of current-carrying conductors in bundle (default: 3)
        ambient_temp_c (float): Ambient temperature in °C (default: 30.0)

    Raises:
        ValueError: On invalid inputs or unsupported gauge
    """
    try:
        wire_material = str(inputs.get("wire_material", "copper")).lower().strip()
        wire_gauge_raw = str(inputs.get("wire_gauge", inputs.get("wire", ""))).strip()
        temp_rating_c = int(inputs.get("temp_rating_c", 75))
        conductor_count = int(
            inputs.get("conductor_count", inputs.get("num_conductors", 3))
        )
        ambient_temp_c = float(inputs.get("ambient_temp_c", 30.0))
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid ampacity inputs: {e}") from e

    if not wire_gauge_raw:
        raise ValueError("wire_gauge is required")
    if conductor_count < 1:
        raise ValueError("conductor_count must be ≥ 1")

    normalized = _normalize_gauge(wire_gauge_raw)

    # Select base ampacity table — copper only for MVP
    # Aluminum would require a separate table; return error for now
    if wire_material not in ("copper",):
        raise ValueError(
            f"Unsupported wire_material: {wire_material!r}. "
            "Supported: 'copper'. Aluminum support is pending."
        )

    if temp_rating_c == 90:
        ampacity_table = _COPPER_AMPACITY_90C
        t_max = 90.0
    else:
        # Default to 75°C for both 60°C and 75°C rated conductors
        # (75°C is the conservative choice for 60°C rated)
        ampacity_table = _COPPER_AMPACITY_75C
        t_max = 75.0 if temp_rating_c == 75 else 60.0

    base_ampacity = ampacity_table.get(normalized)
    if base_ampacity is None:
        available = ", ".join(
            sorted(
                ampacity_table.keys(),
                key=lambda x: (
                    float(x.replace("/", "."))
                    if "/" in x
                    else float(x)
                    if x.isdigit()
                    else 1000
                ),
            )
        )
        raise ValueError(
            f"Unknown wire gauge: {wire_gauge_raw!r}. Supported gauges: {available}"
        )

    # Temperature correction factor — NEC Table 310.15(B)(1)
    # CF = sqrt((T_max - T_ambient) / (T_max - 30))
    if ambient_temp_c >= t_max:
        raise ValueError(
            f"ambient_temp_c ({ambient_temp_c}°C) must be less than "
            f"conductor rating ({t_max:.0f}°C)"
        )
    temp_correction_factor = math.sqrt((t_max - ambient_temp_c) / (t_max - 30.0))

    # Bundling adjustment — NEC Table 310.15(C)(1)
    bundling_adjustment_factor = _get_bundling_factor(conductor_count)

    adjusted_ampacity = (
        base_ampacity * temp_correction_factor * bundling_adjustment_factor
    )

    # Compliance: adjusted ampacity must be > 0 (always true if inputs are valid)
    is_compliant = adjusted_ampacity > 0

    return NecCalcResult(
        calc_type="ampacity",
        result_value=round(adjusted_ampacity, 2),
        is_compliant=is_compliant,
        nec_article="NEC Table 310.12",
        nec_citation=(
            "NEC Table 310.12 — Allowable Ampacities for Insulated Conductors "
            "(THHN/THWN-2, copper)"
        ),
        details={
            "base_ampacity": base_ampacity,
            "temp_correction_factor": round(temp_correction_factor, 4),
            "bundling_adjustment_factor": bundling_adjustment_factor,
            "adjusted_ampacity": round(adjusted_ampacity, 2),
            "wire_gauge": wire_gauge_raw,
            "wire_gauge_normalized": normalized,
            "wire_material": wire_material,
            "temp_rating_c": temp_rating_c,
            "conductor_count": conductor_count,
            "ambient_temp_c": ambient_temp_c,
        },
    )
