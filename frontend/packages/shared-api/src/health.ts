/**
 * Health API — migrated from index.ts
 *
 * Location: packages/shared-api/src/health.ts
 *
 * Provides checkApiHealth() for checking the Celery health endpoint.
 * Used by the dev-only health check page (apps/web/src/app/(dev)/health/).
 */

import { apiClient } from "./client";

export interface CeleryHealthResponse {
  status: string;
  workers_active: number;
  broker_connected: boolean;
  scheduled_tasks: number;
  timestamp: string;
}

/**
 * Fetches Celery health status from GET /api/v1/health/celery
 * Schema: operations['check_celery_health_api_v1_health_celery_get'] in api-schema.d.ts
 */
export async function checkApiHealth(): Promise<CeleryHealthResponse> {
  const response = await apiClient.get<CeleryHealthResponse>(
    "/api/v1/health/celery",
  );
  return response.data;
}
