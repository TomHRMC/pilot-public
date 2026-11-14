/**
 * Onboarding MSW Handlers — FE-B13
 *
 * Location: apps/web/src/mocks/handlers/onboardingHandlers.ts
 *
 * Covers BE-B14 / A77–A78:
 *  - GET  /api/v1/tenants/:tenantId/onboarding/checklist
 *  - PUT  /api/v1/tenants/:tenantId/onboarding/checklist/skip/:item
 *  - PUT  /api/v1/tenants/:tenantId/onboarding/checklist/hidden
 *  - PUT  /api/v1/tenants/:tenantId/onboarding/checklist/dismissed
 *  - GET  /api/v1/users/me/devices/:deviceId/push-permission
 *  - PUT  /api/v1/users/me/devices/:deviceId/push-permission
 */

import { http, HttpResponse } from "msw";
import {
  CHECKLIST_INITIAL,
  PUSH_PERMISSION_NOT_ASKED,
} from "../../features/onboarding/mocks/onboardingFixtures";

const TENANTS_API = "/api/v1/tenants";
const USERS_API = "/api/v1/users";

// Mutable checklist state — shared across handlers in a test session
type ChecklistState = typeof CHECKLIST_INITIAL & { [key: string]: unknown };
let checklistState: ChecklistState = { ...CHECKLIST_INITIAL };

// Explicit interface avoids the `null`-only inference from the fixture literal
interface PushPermissionState {
  device_id: string;
  permission_state:
    | "not_asked"
    | "granted"
    | "denied_by_user_choice"
    | "denied_by_os"
    | "revoked_in_settings";
  last_state_change_at: string;
  dismissable_banner_dismissed_at: string | null;
  banner_should_appear: boolean;
}

const pushPermissionStateByDevice = new Map<string, PushPermissionState>();

export const onboardingHandlers = [
  // ─── Onboarding Checklist GET ─────────────────────────────────────────────

  http.get(`${TENANTS_API}/:tenantId/onboarding/checklist`, ({ params }) => {
    const { tenantId } = params as { tenantId: string };

    // Dismissed checklist returns dismissed state
    if (tenantId === "tenant-checklist-dismissed") {
      return HttpResponse.json({
        ...checklistState,
        checklist_dismissed_permanently: true,
      });
    }

    return HttpResponse.json(checklistState);
  }),

  // ─── Checklist Skip Item ──────────────────────────────────────────────────

  http.put(
    `${TENANTS_API}/:tenantId/onboarding/checklist/skip/:item`,
    ({ params }) => {
      const { item } = params as { item: string };

      // Only skippable items are quickbooks, calendar, team
      const skippableItems = ["quickbooks", "calendar", "team"];
      if (!skippableItems.includes(item)) {
        return HttpResponse.json(
          {
            detail: "This item can't be skipped.",
            code: "item_not_skippable",
          },
          { status: 422 },
        );
      }

      const skippedKey = `${item}_skipped` as keyof ChecklistState;
      checklistState = { ...checklistState, [skippedKey]: true };
      return HttpResponse.json(checklistState);
    },
  ),

  // ─── Checklist Hidden ─────────────────────────────────────────────────────

  http.put(
    `${TENANTS_API}/:tenantId/onboarding/checklist/hidden`,
    async ({ request }) => {
      const body = (await request.json()) as { hidden: boolean };
      checklistState = { ...checklistState, checklist_hidden: body.hidden };
      return HttpResponse.json({ checklist_hidden: body.hidden });
    },
  ),

  // ─── Checklist Dismissed (Permanent) ─────────────────────────────────────

  http.put(`${TENANTS_API}/:tenantId/onboarding/checklist/dismissed`, () => {
    checklistState = {
      ...checklistState,
      checklist_dismissed_permanently: true,
    };
    return HttpResponse.json({ checklist_dismissed_permanently: true });
  }),

  // ─── Push Permission GET ──────────────────────────────────────────────────

  http.get(
    `${USERS_API}/me/devices/:deviceId/push-permission`,
    ({ params }) => {
      const { deviceId } = params as { deviceId: string };

      const state = pushPermissionStateByDevice.get(deviceId);
      if (!state) {
        // First access: return not_asked
        const initial: PushPermissionState = {
          ...PUSH_PERMISSION_NOT_ASKED,
          device_id: deviceId,
          permission_state: "not_asked",
        };
        pushPermissionStateByDevice.set(deviceId, initial);
        return HttpResponse.json(initial);
      }

      return HttpResponse.json(state);
    },
  ),

  // ─── Push Permission PUT ──────────────────────────────────────────────────

  http.put(
    `${USERS_API}/me/devices/:deviceId/push-permission`,
    async ({ params, request }) => {
      const { deviceId } = params as { deviceId: string };
      const body = (await request.json()) as {
        permission_state: string;
        dismissable_banner_dismissed_at?: string;
      };

      const existing = pushPermissionStateByDevice.get(deviceId) ?? {
        ...PUSH_PERMISSION_NOT_ASKED,
        device_id: deviceId,
      };

      const updated: PushPermissionState = {
        ...existing,
        device_id: deviceId,
        permission_state:
          body.permission_state as PushPermissionState["permission_state"],
        last_state_change_at: new Date().toISOString(),
        dismissable_banner_dismissed_at:
          body.dismissable_banner_dismissed_at ??
          existing.dismissable_banner_dismissed_at,
        // Compute banner_should_appear: show for denied_by_os or revoked_in_settings
        banner_should_appear:
          body.permission_state === "denied_by_os" ||
          body.permission_state === "revoked_in_settings",
      };

      pushPermissionStateByDevice.set(deviceId, updated);
      return HttpResponse.json(updated);
    },
  ),
];

/**
 * Test utility: reset all mutable onboarding handler state.
 * Call in beforeEach to ensure test isolation.
 */
export function resetOnboardingHandlerState() {
  checklistState = { ...CHECKLIST_INITIAL };
  pushPermissionStateByDevice.clear();
}
