/**
 * backgroundSyncHandlers — MOB-B8 Part B
 *
 * Location: apps/mobile/mocks/handlers/backgroundSyncHandlers.ts
 *
 * MSW handlers for:
 *   - GET /api/v1/settings/background-sync-policy
 *   - POST /api/v1/mobile/push-tokens
 *
 * Mobile handlers MUST use wildcard prefix because apiClient.baseURL is an
 * absolute LAN IP (e.g. http://192.168.1.50:8000). Relative paths silently
 * miss all requests. (Rule 18 in react-engineer-rules.md)
 *
 * Wildcard pattern: "star /api/v1/..." — matches any origin.
 */

import { http, HttpResponse } from "msw";

export const MOCK_SYNC_POLICY = {
  background_sync_enabled: true,
  background_sync_wifi_only: false,
  background_sync_battery_floor_pct: 20,
  background_sync_push_interval_minutes: 5,
};

export const MOCK_PUSH_TOKEN_RESPONSE = {
  id: "mock-token-id-001",
  device_id: "mock-device-id-001",
  registered_at: "2026-07-12T12:00:00Z",
  last_seen_at: "2026-07-12T12:00:00Z",
};

export const backgroundSyncHandlers = [
  // GET background-sync-policy (wildcard origin for mobile apiClient)
  http.get("*/api/v1/settings/background-sync-policy", () =>
    HttpResponse.json(MOCK_SYNC_POLICY),
  ),

  // POST push-tokens upsert (wildcard origin for mobile apiClient)
  http.post("*/api/v1/mobile/push-tokens", async () =>
    HttpResponse.json(MOCK_PUSH_TOKEN_RESPONSE, { status: 200 }),
  ),
];
