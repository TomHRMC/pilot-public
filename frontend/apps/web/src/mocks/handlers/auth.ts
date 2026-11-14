/**
 * MSW handlers — auth domain (web)
 *
 * Location: apps/web/src/mocks/handlers/auth.ts
 *
 * FE-B2: Mock handler for GET /api/v1/auth/me.
 * Stands in for the FastAPI endpoint until BE-B14 lands.
 * Returns a mock PilotUser shape matching the CurrentUserApiResponse interface.
 */

import { http, HttpResponse } from "msw";
import type { CurrentUserApiResponse } from "@pilot/shared-api";

export const authHandlers = [
  http.get("/api/v1/auth/me", () =>
    HttpResponse.json<CurrentUserApiResponse>({
      user_id: "mock-user-001",
      tenant_id: "mock-tenant-001",
      email: "mockuser@pilot-dev.example.com",
      display_name: "Mock User",
      role: "owner",
    }),
  ),
];
