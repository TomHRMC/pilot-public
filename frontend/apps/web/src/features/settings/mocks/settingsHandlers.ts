import { http, HttpResponse } from "msw";
/**
 * settingsHandlers.ts — FE-B11
 *
 * Location: apps/web/src/features/settings/mocks/settingsHandlers.ts
 *
 * MSW handlers for all settings endpoints (A52–A55).
 * Variants:
 *   - catalog: scope=system (default), scope=tenant (tenant-overrides scenario)
 *   - effective: by key, system scope, tenant scope, user scope
 *   - PUT /{key}: success, 409 conflict, pending-quotes (require_approval_for_tech_quotes)
 *   - DELETE /{key}/tenant-override: success, 404 no override
 *   - PUT /bulk: success, 422 validation error
 *   - PUT /{key}/user-override: success, 403 not allowed
 *   - DELETE /{key}/user-override: success, 404 no override
 */

import {
  ALL_SETTINGS_CATALOG_SYSTEM,
  ALL_SETTINGS_CATALOG_TENANT_OVERRIDES,
  makeEffectiveSettingSystem,
  makeEffectiveSettingTenant,
  makeTenantWriteSuccess,
  makeRevertSuccess,
  makeBulkWriteSuccess,
  type CatalogResponseRaw,
} from "./settingsFixtures";

const API_BASE = "/api/v1";

// ─── State: active catalog scenario (toggled in tests) ───────────────────────

let _useTenantOverrides = false;

/** Call in tests: `setSettingsScenario('tenant-overrides')` */
export function setSettingsScenario(
  scenario: "system-defaults" | "tenant-overrides",
) {
  _useTenantOverrides = scenario === "tenant-overrides";
}

/** Reset to system defaults (call in afterEach) */
export function resetSettingsScenario() {
  _useTenantOverrides = false;
}

// ─── GET /api/v1/settings/catalog ────────────────────────────────────────────

export const getCatalogHandler = http.get(
  `${API_BASE}/settings/catalog`,
  () => {
    const catalog = _useTenantOverrides
      ? ALL_SETTINGS_CATALOG_TENANT_OVERRIDES
      : ALL_SETTINGS_CATALOG_SYSTEM;

    const body: CatalogResponseRaw = { settings: catalog };
    return HttpResponse.json(body, { status: 200 });
  },
);

/** Tenant-overrides variant — register instead of default when needed */
export const getCatalogTenantOverridesHandler = http.get(
  `${API_BASE}/settings/catalog`,
  () => {
    return HttpResponse.json(
      { settings: ALL_SETTINGS_CATALOG_TENANT_OVERRIDES },
      { status: 200 },
    );
  },
);

// ─── GET /api/v1/settings/:key/effective ─────────────────────────────────────

export const getEffectiveSettingHandler = http.get(
  `${API_BASE}/settings/:key/effective`,
  ({ params }) => {
    const key = params.key as string;
    const catalog = _useTenantOverrides
      ? ALL_SETTINGS_CATALOG_TENANT_OVERRIDES
      : ALL_SETTINGS_CATALOG_SYSTEM;

    const entry = catalog.find((s) => s.key === key);
    if (!entry) {
      return HttpResponse.json(
        { detail: "Setting not found" },
        { status: 404 },
      );
    }

    const response =
      entry.current_scope === "tenant"
        ? makeEffectiveSettingTenant(key, entry.current_effective_value)
        : makeEffectiveSettingSystem(key, entry.current_effective_value);

    return HttpResponse.json(response, { status: 200 });
  },
);

// ─── PUT /api/v1/settings/:key ────────────────────────────────────────────────

export const putTenantSettingHandler = http.put(
  `${API_BASE}/settings/:key`,
  async ({ params, request }) => {
    const key = params.key as string;
    const body = (await request.json()) as {
      value: unknown;
      expected_updated_at?: string;
    };

    // 409 scenario: simulate staleness conflict
    if (body.expected_updated_at === "STALE_TIMESTAMP") {
      return HttpResponse.json(
        {
          detail: "This setting was updated by another session.",
          current_updated_at: new Date().toISOString(),
        },
        { status: 409 },
      );
    }

    // Pending quotes scenario
    if (key === "require_approval_for_tech_quotes" && body.value === false) {
      return HttpResponse.json(makeTenantWriteSuccess(key, body.value, 3), {
        status: 200,
      });
    }

    // Validation error scenario
    if (body.value === "INVALID_VALUE_TRIGGER_422") {
      return HttpResponse.json(
        { detail: "Value is not valid for this setting." },
        { status: 422 },
      );
    }

    // Write failure scenario
    if (body.value === "TRIGGER_WRITE_FAILURE") {
      return HttpResponse.json(
        { detail: "Internal server error." },
        { status: 500 },
      );
    }

    return HttpResponse.json(makeTenantWriteSuccess(key, body.value), {
      status: 200,
    });
  },
);

/** 409 conflict variant — always returns conflict */
export const putTenantSetting409Handler = http.put(
  `${API_BASE}/settings/:key`,
  () => {
    return HttpResponse.json(
      {
        detail: "This setting was updated by another session.",
        current_updated_at: new Date().toISOString(),
      },
      { status: 409 },
    );
  },
);

/** Write failure variant — always returns 500 */
export const putTenantSettingFailureHandler = http.put(
  `${API_BASE}/settings/:key`,
  () => {
    return HttpResponse.json(
      { detail: "Internal server error." },
      { status: 500 },
    );
  },
);

// ─── DELETE /api/v1/settings/:key/tenant-override ────────────────────────────

export const deleteTenantOverrideHandler = http.delete(
  `${API_BASE}/settings/:key/tenant-override`,
  ({ params }) => {
    const key = params.key as string;

    const catalog = _useTenantOverrides
      ? ALL_SETTINGS_CATALOG_TENANT_OVERRIDES
      : ALL_SETTINGS_CATALOG_SYSTEM;

    const entry = catalog.find((s) => s.key === key);

    if (!entry || entry.current_scope !== "tenant") {
      return HttpResponse.json(
        { detail: "No tenant override exists for this setting." },
        { status: 404 },
      );
    }

    const systemEntry = ALL_SETTINGS_CATALOG_SYSTEM.find((s) => s.key === key);
    return HttpResponse.json(
      makeRevertSuccess(key, systemEntry?.system_default ?? null),
      { status: 200 },
    );
  },
);

/** Revert success variant — always returns 200 with scope=system */
export const deleteTenantOverrideSuccessHandler = http.delete(
  `${API_BASE}/settings/:key/tenant-override`,
  ({ params }) => {
    const key = params.key as string;
    const systemEntry = ALL_SETTINGS_CATALOG_SYSTEM.find((s) => s.key === key);
    return HttpResponse.json(
      makeRevertSuccess(key, systemEntry?.system_default ?? null),
      { status: 200 },
    );
  },
);

/** 404 no override variant */
export const deleteTenantOverride404Handler = http.delete(
  `${API_BASE}/settings/:key/tenant-override`,
  () => {
    return HttpResponse.json(
      { detail: "No tenant override exists for this setting." },
      { status: 404 },
    );
  },
);

// ─── PUT /api/v1/settings/bulk ───────────────────────────────────────────────

export const putBulkSettingsHandler = http.put(
  `${API_BASE}/settings/bulk`,
  async ({ request }) => {
    const body = (await request.json()) as { values: Record<string, unknown> };

    // 422 validation error variant
    const hasInvalidValue = Object.values(body.values).includes(
      "TRIGGER_BULK_422",
    );
    if (hasInvalidValue) {
      return HttpResponse.json(
        { detail: "One or more values failed validation." },
        { status: 422 },
      );
    }

    return HttpResponse.json(makeBulkWriteSuccess(body.values), {
      status: 200,
    });
  },
);

/** Bulk write failure variant */
export const putBulkSettingsFailureHandler = http.put(
  `${API_BASE}/settings/bulk`,
  () => {
    return HttpResponse.json({ detail: "Bulk write failed." }, { status: 500 });
  },
);

// ─── PUT /api/v1/settings/:key/user-override ─────────────────────────────────

export const putUserOverrideHandler = http.put(
  `${API_BASE}/settings/:key/user-override`,
  async ({ params, request }) => {
    const key = params.key as string;
    const body = (await request.json()) as { value: unknown };

    const entry = ALL_SETTINGS_CATALOG_SYSTEM.find((s) => s.key === key);
    if (!entry?.allows_user_override) {
      return HttpResponse.json(
        { detail: "User override not allowed for this setting." },
        { status: 403 },
      );
    }

    return HttpResponse.json(
      {
        key,
        value: body.value,
        effective_value: body.value,
        scope: "user",
        updated_at: new Date().toISOString(),
      },
      { status: 200 },
    );
  },
);

/** 403 not allowed variant */
export const putUserOverride403Handler = http.put(
  `${API_BASE}/settings/:key/user-override`,
  () => {
    return HttpResponse.json(
      { detail: "User override not allowed for this setting." },
      { status: 403 },
    );
  },
);

// ─── DELETE /api/v1/settings/:key/user-override ──────────────────────────────

export const deleteUserOverrideHandler = http.delete(
  `${API_BASE}/settings/:key/user-override`,
  ({ params }) => {
    const key = params.key as string;
    const systemEntry = ALL_SETTINGS_CATALOG_SYSTEM.find((s) => s.key === key);

    return HttpResponse.json(
      {
        key,
        value: null,
        effective_value: systemEntry?.system_default ?? null,
        scope: "system",
        updated_at: new Date().toISOString(),
      },
      { status: 200 },
    );
  },
);

/** 404 no user override variant */
export const deleteUserOverride404Handler = http.delete(
  `${API_BASE}/settings/:key/user-override`,
  () => {
    return HttpResponse.json(
      { detail: "No user override exists for this setting." },
      { status: 404 },
    );
  },
);

// ─── Default handler set (all success paths) ─────────────────────────────────

export const settingsHandlers = [
  getCatalogHandler,
  getEffectiveSettingHandler,
  putTenantSettingHandler,
  deleteTenantOverrideHandler,
  putBulkSettingsHandler,
  putUserOverrideHandler,
  deleteUserOverrideHandler,
];
