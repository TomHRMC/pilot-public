/**
 * Shared test fixtures for saved NEC calc log tests (MOB-B4)
 *
 * Location: apps/mobile/mocks/fixtures/necCalcLogs.ts
 * (kept outside __tests__/ so Jest doesn't pick it up as a test suite)
 */

import type { SavedNecCalcLog } from "../../features/nec-calcs/hooks/useNecCalcLogs";

export const savedCalcLogsFixture: SavedNecCalcLog[] = [
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
      result_value: 7.902,
      is_compliant: false,
      nec_article: "NEC 210.19(A)(1)",
      nec_citation:
        "NEC 210.19(A)(1) Informational Note 4 — Voltage drop ≤ 3% recommended",
      voltage_drop: 7.902,
      voltage_drop_pct: 6.585,
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
