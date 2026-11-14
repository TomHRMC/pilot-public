"use client";

/**
 * Dev health check page
 *
 * Location: apps/web/src/app/(dev)/health/page.tsx
 *
 * Preserved from the original Hello World page.
 * Accessible at /_dev/health when NEXT_PUBLIC_SHOW_DEV_ROUTES=true.
 * Verifies FastAPI + Celery backend connectivity during local development.
 *
 * This page is env-gated — link to it is hidden in production.
 * The route itself still exists but is not advertised.
 */

import { useEffect, useState } from "react";
import { checkApiHealth } from "@pilot/shared-api";
import type { CeleryHealthResponse } from "@pilot/shared-api";

export default function DevHealthPage() {
  const [healthData, setHealthData] = useState<CeleryHealthResponse | null>(
    null,
  );
  const [apiError, setApiError] = useState<string | null>(null);
  const [docsReachable, setDocsReachable] = useState<boolean>(false);

  useEffect(() => {
    checkApiHealth()
      .then((data) => setHealthData(data))
      .catch(() =>
        setApiError(
          "❌ Error: Could not reach the FastAPI backend. Check CORS and server status.",
        ),
      );

    fetch("http://127.0.0.1:8000/docs")
      .then((res) => {
        if (res.ok) setDocsReachable(true);
      })
      .catch(() => setDocsReachable(false));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-6 bg-neutral-50 text-neutral-900">
      <div className="max-w-xl w-full bg-white p-8 rounded-lg shadow border border-neutral-200">
        <h1 className="text-h1 font-medium mb-6 text-center">
          Dev Health Check
        </h1>

        <p className="text-caption text-neutral-600 mb-6 text-center">
          Route: <code className="font-mono">/_dev/health</code> — visible only
          when{" "}
          <code className="font-mono">NEXT_PUBLIC_SHOW_DEV_ROUTES=true</code>
        </p>

        <div className="space-y-4">
          <div className="p-5 rounded-lg bg-neutral-50 border border-neutral-200">
            <h2 className="text-h2 font-medium mb-3 border-b pb-2">
              FastAPI &amp; Celery Status
            </h2>

            {apiError && (
              <p className="text-fault-600 font-medium">{apiError}</p>
            )}

            {healthData && (
              <ul className="space-y-2 text-body font-mono">
                <li>
                  <span className="text-neutral-600">Status:</span>{" "}
                  <span
                    className={
                      healthData.status === "healthy"
                        ? "text-margin-600 font-medium"
                        : "text-alert-600"
                    }
                  >
                    {healthData.status.toUpperCase()}
                  </span>
                </li>
                <li>
                  <span className="text-neutral-600">Broker Connected:</span>{" "}
                  {healthData.broker_connected ? "✅ True" : "❌ False"}
                </li>
                <li>
                  <span className="text-neutral-600">Active Workers:</span>{" "}
                  {healthData.workers_active}
                </li>
                <li>
                  <span className="text-neutral-600">Scheduled Tasks:</span>{" "}
                  {healthData.scheduled_tasks}
                </li>
                <li>
                  <span className="text-neutral-600">Server Time:</span>{" "}
                  {new Date(healthData.timestamp).toLocaleString()}
                </li>
              </ul>
            )}

            {!healthData && !apiError && (
              <p className="text-neutral-600 animate-pulse">
                Pinging /api/v1/health/celery...
              </p>
            )}
          </div>

          <div className="p-5 rounded-lg bg-neutral-50 border border-neutral-200">
            <h2 className="text-h2 font-medium mb-2">OpenAPI Documentation</h2>
            {docsReachable ? (
              <p>
                ✅ Docs are online!{" "}
                <a
                  href="http://127.0.0.1:8000/docs"
                  target="_blank"
                  rel="noreferrer"
                  className="text-brand-600 hover:underline font-medium"
                >
                  View Swagger UI &rarr;
                </a>
              </p>
            ) : (
              <p className="text-fault-600 font-medium">
                ❌ Could not ping /docs.
              </p>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
