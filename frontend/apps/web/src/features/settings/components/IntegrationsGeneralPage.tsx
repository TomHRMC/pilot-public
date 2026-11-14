/**
 * IntegrationsGeneralPage — BETA-B4 / STEP 6
 *
 * Location: apps/web/src/features/settings/components/IntegrationsGeneralPage.tsx
 *
 * Integrations overview: shows all integration statuses + sync dashboard.
 * Route: /settings/integrations/general
 */

"use client";

import React from "react";
import Link from "next/link";
import { RoleGate } from "@pilot/ui/role-gate";
import { useIntegrationsDashboard } from "../hooks/useIntegrationsDashboard";
import type { IntegrationStatus } from "../hooks/useIntegrationsDashboard";

function IntegrationCard({ integration }: { integration: IntegrationStatus }) {
  return (
    <Link
      href={integration.settingsHref}
      className="flex items-center justify-between p-4 rounded-md border border-neutral-200 hover:border-brand-400 hover:bg-brand-50 transition-colors group"
    >
      <div>
        <div className="flex items-center gap-2 mb-0.5">
          <span
            className={`inline-block h-2 w-2 rounded-full ${integration.connected ? "bg-success-500" : "bg-neutral-300"}`}
            aria-hidden="true"
          />
          <p className="text-sm font-medium text-neutral-900">
            {integration.displayName}
          </p>
          <span
            className={`text-xs px-1.5 py-0.5 rounded font-medium ${
              integration.connected
                ? "bg-success-100 text-success-700"
                : "bg-neutral-100 text-neutral-500"
            }`}
          >
            {integration.connected ? "Connected" : "Not connected"}
          </span>
        </div>
        {integration.connected && integration.lastSyncAt ? (
          <p className="text-xs text-neutral-500 ml-4">
            Last synced {new Date(integration.lastSyncAt).toLocaleString()}
          </p>
        ) : (
          <p className="text-xs text-neutral-400 ml-4">
            {integration.connected ? "Sync pending" : "Not configured"}
          </p>
        )}
      </div>
      <span
        className="text-neutral-400 group-hover:text-brand-600 text-lg"
        aria-hidden="true"
      >
        →
      </span>
    </Link>
  );
}

function IntegrationsContent() {
  const { dashboard, isLoading, isError } = useIntegrationsDashboard();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin h-6 w-6 rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  if (isError || !dashboard) {
    return (
      <div className="rounded-lg border border-fault-200 bg-fault-50 p-6 text-sm text-fault-700">
        Could not load integrations. Please refresh the page.
      </div>
    );
  }

  const allDisconnected =
    !dashboard.quickbooks.connected &&
    !dashboard.calendar.connected &&
    !dashboard.sms.connected;

  const pendingCount = dashboard.syncDashboard?.pendingCount ?? 0;

  return (
    <>
      {/* Pending sync banner */}
      {pendingCount > 0 && (
        <div className="mb-6 rounded-md bg-alert-50 border border-alert-200 px-4 py-3 text-sm text-alert-800">
          <strong>
            {pendingCount} pending sync item{pendingCount !== 1 ? "s" : ""}
          </strong>{" "}
          — review in the integration settings below.
        </div>
      )}

      {allDisconnected ? (
        <div className="rounded-md border border-dashed border-neutral-300 p-8 text-center">
          <p className="text-sm font-medium text-neutral-700 mb-1">
            No integrations connected
          </p>
          <p className="text-xs text-neutral-500">
            Connect an integration to sync your data automatically.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <IntegrationCard integration={dashboard.quickbooks} />
          <IntegrationCard integration={dashboard.calendar} />
          <IntegrationCard integration={dashboard.sms} />
        </div>
      )}

      {/* Always show all cards so users can connect */}
      {allDisconnected && (
        <div className="mt-6 space-y-3">
          <IntegrationCard integration={dashboard.quickbooks} />
          <IntegrationCard integration={dashboard.calendar} />
          <IntegrationCard integration={dashboard.sms} />
        </div>
      )}
    </>
  );
}

export function IntegrationsGeneralPage() {
  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-semibold text-neutral-900 mb-2">
        Integrations
      </h1>
      <p className="text-sm text-neutral-500 mb-6">
        Connect external services to sync your data automatically.
      </p>
      <RoleGate permission="settings.manage">
        <IntegrationsContent />
      </RoleGate>
    </div>
  );
}
