/**
 * Notification Preference MSW Handlers — FE-B12
 *
 * Location: apps/web/src/mocks/handlers/notificationPreferenceHandlers.ts
 *
 * Covers BE-B10 / A56–A58:
 *  - GET  /api/v1/notifications/categories
 *  - GET  /api/v1/notifications/preferences
 *  - PUT  /api/v1/notifications/preferences/{category_id}/{channel}
 *  - DELETE /api/v1/notifications/preferences/{category_id}/{channel}
 *  - PUT  /api/v1/notifications/tenant-policy/{category_id}/{channel}
 *  - DELETE /api/v1/notifications/tenant-policy/{category_id}/{channel}
 *  - POST /api/v1/notifications/preferences/mute-all-push-non-critical
 *  - POST /api/v1/notifications/preferences/mute-all-email
 *  - POST /api/v1/notifications/preferences/reset-to-tenant-defaults
 *  - GET  /api/v1/notifications/in-app/recent
 *  - POST /api/v1/notifications/in-app/mark-read
 */

import { http, HttpResponse } from "msw";
import {
  NOTIFICATION_CATEGORIES,
  NOTIFICATION_PREFERENCES,
  RECENT_NOTIFICATIONS,
  makePrefWriteSuccess,
} from "../../features/notification-preferences/mocks/notificationFixtures";

const API = "/api/v1/notifications";

export const notificationPreferenceHandlers = [
  // GET categories
  http.get(`${API}/categories`, () => {
    return HttpResponse.json(NOTIFICATION_CATEGORIES);
  }),

  // GET preferences matrix
  http.get(`${API}/preferences`, () => {
    return HttpResponse.json({
      user_id: "user-abc-123",
      preferences: NOTIFICATION_PREFERENCES,
    });
  }),

  // PUT preference cell
  http.put(
    `${API}/preferences/:categoryId/:channel`,
    async ({ params, request }) => {
      const { categoryId, channel } = params as {
        categoryId: string;
        channel: string;
      };
      const body = (await request.json()) as { enabled: boolean };

      // Check if it's a forced-minimum cell (system_alerts, customer_activity push)
      const forcedMinimumCells = [
        "system_alerts:push",
        "system_alerts:email",
        "system_alerts:in_app",
        "customer_activity:push",
      ];
      const cellKey = `${categoryId}:${channel}`;
      if (forcedMinimumCells.includes(cellKey) && !body.enabled) {
        return HttpResponse.json(
          {
            detail: `Push for ${categoryId} can't be turned off for this user context.`,
          },
          { status: 403 },
        );
      }

      return HttpResponse.json(
        makePrefWriteSuccess(
          categoryId,
          channel as "push" | "email" | "in_app",
          body.enabled,
        ),
      );
    },
  ),

  // DELETE preference cell (revert to tenant default)
  http.delete(`${API}/preferences/:categoryId/:channel`, ({ params }) => {
    const { categoryId } = params;
    void categoryId;
    return HttpResponse.json({
      cleared: true,
      reverted_to_scope: "tenant",
    });
  }),

  // PUT tenant-policy cell (owner only)
  http.put(
    `${API}/tenant-policy/:categoryId/:channel`,
    async ({ params, request }) => {
      const { categoryId, channel } = params as {
        categoryId: string;
        channel: string;
      };
      const body = (await request.json()) as { enabled: boolean };
      return HttpResponse.json({
        category_id: categoryId,
        channel,
        enabled: body.enabled,
        scope: "tenant",
      });
    },
  ),

  // DELETE tenant-policy cell
  http.delete(`${API}/tenant-policy/:categoryId/:channel`, () => {
    return HttpResponse.json({
      cleared: true,
      reverted_to_scope: "system",
    });
  }),

  // POST mute-all-push-non-critical
  http.post(`${API}/preferences/mute-all-push-non-critical`, () => {
    return HttpResponse.json({ muted_count: 6 });
  }),

  // POST mute-all-email
  http.post(`${API}/preferences/mute-all-email`, () => {
    return HttpResponse.json({ muted_count: 8 });
  }),

  // POST reset-to-tenant-defaults
  http.post(`${API}/preferences/reset-to-tenant-defaults`, () => {
    return HttpResponse.json({ cleared_count: 5 });
  }),

  // GET recent in-app notifications (last 50)
  http.get(`${API}/in-app/recent`, () => {
    return HttpResponse.json(RECENT_NOTIFICATIONS);
  }),

  // POST mark-read
  http.post(`${API}/in-app/mark-read`, async ({ request }) => {
    const body = (await request.json()) as { notification_ids?: string[] };
    const count = body.notification_ids?.length ?? RECENT_NOTIFICATIONS.length;
    return HttpResponse.json({ marked_count: count });
  }),
];
