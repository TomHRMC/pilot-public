/**
 * MSW Handlers — NEC Calculator API Endpoints
 *
 * Location: apps/mobile/mocks/handlers/necHandlers.ts
 *
 * Fixtures for:
 *   POST /api/v1/nec/calculate
 *   GET  /api/v1/nec/calc-logs
 *
 * Per batch-mob-b4-design.md §C step 8.
 */

import { http, HttpResponse } from "msw";

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const voltageDropResultFixture = {
  log_id: "nec-log-fixture-001",
  calc_type: "voltage_drop",
  result: {
    calc_type: "voltage_drop",
    result_value: 3.9478,
    is_compliant: false,
    nec_article: "NEC 210.19(A)(1)",
    nec_citation:
      "NEC 210.19(A)(1) Informational Note 4 — Voltage drop ≤ 3% recommended",
    voltage_drop: 3.9478,
    voltage_drop_pct: 3.2898,
    wire_gauge: "12 AWG",
    wire_gauge_normalized: "12",
    amperage: 20,
    distance_feet: 100,
    voltage: 120,
    phase: 1,
  },
  nec_guide_version: "2023",
  nec_citation:
    "NEC 210.19(A)(1) Informational Note 4 — Voltage drop ≤ 3% recommended",
};

const savedCalcLogsFixture = [
  {
    id: "saved-log-001",
    calc_type: "voltage_drop",
    nec_guide_version: "2023",
    inputs_json: {
      amperage: 20,
      distance_feet: 100,
      wire_gauge: "12",
      voltage: 120,
      phase: 1,
    },
    result_json: {
      calc_type: "voltage_drop",
      result_value: 3.9478,
      is_compliant: false,
      nec_article: "NEC 210.19(A)(1)",
      nec_citation:
        "NEC 210.19(A)(1) Informational Note 4 — Voltage drop ≤ 3% recommended",
      voltage_drop: 3.9478,
      voltage_drop_pct: 3.2898,
    },
    is_offline_calc: false,
    client_capture_at: "2026-06-06T14:00:00Z",
    job_id: null,
  },
  {
    id: "saved-log-002",
    calc_type: "conduit_fill",
    nec_guide_version: "2023",
    inputs_json: {
      conduit_trade_size: "3/4",
      conduit_type: "EMT",
      wire_gauge: "12",
      num_conductors: 3,
    },
    result_json: {
      calc_type: "conduit_fill",
      result_value: 7.4878,
      is_compliant: true,
      nec_article: "NEC Chapter 9 Table 1",
      nec_citation: "NEC Chapter 9 Table 1 — Max fill 40% for 3 conductor(s)",
      fill_pct: 7.4878,
      max_fill_pct: 40,
    },
    is_offline_calc: true,
    client_capture_at: "2026-06-06T12:00:00Z",
    job_id: null,
  },
];

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

export const necHandlers = [
  // POST /api/v1/nec/calculate — return voltage drop result fixture
  http.post(`${API_BASE}/api/v1/nec/calculate`, async ({ request }) => {
    const body = (await request.json()) as {
      calc_type: string;
      inputs: Record<string, unknown>;
    };

    // Return appropriate fixture based on calc_type
    if (body.calc_type === "voltage_drop") {
      return HttpResponse.json(voltageDropResultFixture, { status: 201 });
    }

    if (body.calc_type === "conduit_fill") {
      return HttpResponse.json(
        {
          log_id: "nec-log-fixture-002",
          calc_type: "conduit_fill",
          result: {
            calc_type: "conduit_fill",
            result_value: 7.4878,
            is_compliant: true,
            nec_article: "NEC Chapter 9 Table 1",
            nec_citation:
              "NEC Chapter 9 Table 1 — Max fill 40% for 3 conductor(s)",
            fill_pct: 7.4878,
            max_fill_pct: 40,
            total_fill_sq_in: 0.0399,
            conduit_area_sq_in: 0.533,
            wire_gauge: body.inputs.wire_gauge ?? "12",
            conduit_trade_size: body.inputs.conduit_trade_size ?? "3/4",
            conduit_type: "EMT",
            num_conductors: body.inputs.num_conductors ?? 3,
          },
          nec_guide_version: "2023",
          nec_citation:
            "NEC Chapter 9 Table 1 — Max fill 40% for 3 conductor(s)",
        },
        { status: 201 },
      );
    }

    if (body.calc_type === "ampacity") {
      return HttpResponse.json(
        {
          log_id: "nec-log-fixture-003",
          calc_type: "ampacity",
          result: {
            calc_type: "ampacity",
            result_value: 25.0,
            is_compliant: true,
            nec_article: "NEC Table 310.12",
            nec_citation:
              "NEC Table 310.12 — Allowable Ampacities for Insulated Conductors (THHN/THWN-2, copper)",
            base_ampacity: 25.0,
            temp_correction_factor: 1.0,
            bundling_adjustment_factor: 1.0,
            adjusted_ampacity: 25.0,
            wire_gauge: body.inputs.wire_gauge ?? "12",
            wire_material: "copper",
            temp_rating_c: 75,
            conductor_count: 3,
            ambient_temp_c: 30,
          },
          nec_guide_version: "2023",
          nec_citation:
            "NEC Table 310.12 — Allowable Ampacities for Insulated Conductors (THHN/THWN-2, copper)",
        },
        { status: 201 },
      );
    }

    return HttpResponse.json(
      { detail: `Unknown calc_type: ${body.calc_type}` },
      { status: 422 },
    );
  }),

  // GET /api/v1/nec/calc-logs — return 2 saved calc fixtures
  http.get(`${API_BASE}/api/v1/nec/calc-logs`, () => {
    return HttpResponse.json(savedCalcLogsFixture, { status: 200 });
  }),
];
