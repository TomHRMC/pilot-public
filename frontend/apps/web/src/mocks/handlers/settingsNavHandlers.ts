/**
 * settingsNavHandlers — FE-UI-NAV-S1
 *
 * Location: apps/web/src/mocks/handlers/settingsNavHandlers.ts
 *
 * MSW stubs for:
 *   BE-01: POST /api/v1/users/me/avatar/presigned-url (exists in backend)
 *   BE-02: DELETE /api/v1/users/me/avatar (stub — BE-UI-NAV-S1 companion)
 *   BE-03: GET /api/v1/notifications/tenant-policy (exists in backend)
 *   BE-04: DELETE /api/v1/notifications/tenant-policy (exists in backend)
 *   BE-05: PUT /api/v1/notifications/tenant-policy/{category_id}/{channel}
 *
 * NOTE: avatar presigned-url and tenant-policy endpoints now exist in the
 * backend (confirmed via openapi_schema_map.md after pnpm sync-api-types).
 * These MSW handlers provide test-environment coverage while the backend
 * batch BE-UI-NAV-S1 is pending.
 */

import { http, HttpResponse } from "msw";

export const settingsNavHandlers = [
  // BE-01: Avatar presigned upload URL
  http.post("/api/v1/users/me/avatar/presigned-url", () =>
    HttpResponse.json(
      {
        upload_url: "https://mock-s3.example.com/presigned-put-url",
        s3_key: "avatars/mock-tenant/mock-user/avatar.jpg",
      },
      { status: 201 },
    ),
  ),

  // BE-02: Avatar delete (companion — not yet in openapi_schema_map)
  http.delete("/api/v1/users/me/avatar", () =>
    HttpResponse.json({ success: true }),
  ),

  // BE-03: Tenant notification policy GET
  http.get("/api/v1/notifications/tenant-policy", () =>
    HttpResponse.json({
      policies: [
        { category_id: "job_activity", channel: "email", enabled: true },
        { category_id: "job_activity", channel: "sms", enabled: false },
        { category_id: "quote_status", channel: "email", enabled: true },
        { category_id: "quote_status", channel: "push", enabled: true },
      ],
    }),
  ),

  // BE-04: Tenant notification policy bulk reset (DELETE)
  http.delete("/api/v1/notifications/tenant-policy", () =>
    HttpResponse.json({ deleted_count: 4 }),
  ),

  // BE-05: Tenant notification policy single cell write
  http.put("/api/v1/notifications/tenant-policy/:category_id/:channel", () =>
    HttpResponse.json({ success: true }),
  ),

  // BE-06: Tenant notification policy single cell delete
  http.delete("/api/v1/notifications/tenant-policy/:category_id/:channel", () =>
    HttpResponse.json({ success: true }),
  ),
];
