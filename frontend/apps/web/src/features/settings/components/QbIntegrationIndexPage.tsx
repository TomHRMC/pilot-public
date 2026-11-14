/**
 * QbIntegrationIndexPage — BETA-B4 / STEP 5
 *
 * Location: apps/web/src/features/settings/components/QbIntegrationIndexPage.tsx
 *
 * QuickBooks integration index: OAuth connect/disconnect + sub-page links.
 * Route: /settings/integrations/quickbooks
 */

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { RoleGate } from "@pilot/ui/role-gate";
import { useQbConnectionStatus } from "../hooks/useQbConnectionStatus";

function QbContent() {
  const { status, isLoading, isError, disconnect, isDisconnecting } =
    useQbConnectionStatus();
  const [showConfirm, setShowConfirm] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin h-6 w-6 rounded-full border-2 border-brand-600 border-t-transparent" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-fault-200 bg-fault-50 p-6 text-sm text-fault-700">
        Could not load QuickBooks connection status. Please refresh the page.
      </div>
    );
  }

  const handleConnect = async () => {
    // Fetch the OAuth URL and redirect
    const { apiClient } = await import("@pilot/shared-api");
    const res = await apiClient.get<{ auth_url: string }>(
      "/api/v1/integrations/quickbooks/connect",
    );
    window.location.href = res.data.auth_url;
  };

  return (
    <>
      {/* Disconnect confirm dialog */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-lg p-6 max-w-sm w-full shadow-xl">
            <h2 className="text-lg font-semibold text-neutral-900 mb-2">
              Disconnect QuickBooks?
            </h2>
            <p className="text-sm text-neutral-600 mb-4">
              This will stop syncing data between Pilot and QuickBooks. You can
              reconnect at any time.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  await disconnect();
                  setShowConfirm(false);
                }}
                disabled={isDisconnecting}
                className="flex-1 rounded-md bg-fault-600 px-4 py-2 text-sm font-medium text-white hover:bg-fault-700 disabled:opacity-50"
              >
                {isDisconnecting ? "Disconnecting…" : "Disconnect"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Connection Status Card */}
      <div className="rounded-md border border-neutral-200 p-5 mb-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span
                className={`inline-block h-2 w-2 rounded-full ${status?.connected ? "bg-success-500" : "bg-neutral-300"}`}
              />
              <p className="text-sm font-medium text-neutral-900">
                {status?.connected
                  ? `Connected to ${status.companyName ?? "QuickBooks"}`
                  : "Not connected"}
              </p>
            </div>
            {status?.connected && status.lastSyncAt && (
              <p className="text-xs text-neutral-500">
                Last synced {new Date(status.lastSyncAt).toLocaleString()}
              </p>
            )}
          </div>
          {status?.connected ? (
            <button
              onClick={() => setShowConfirm(true)}
              className="rounded-md border border-fault-300 px-3 py-1.5 text-sm font-medium text-fault-700 hover:bg-fault-50"
            >
              Disconnect
            </button>
          ) : (
            <button
              onClick={() => void handleConnect()}
              className="rounded-md bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
            >
              Connect QuickBooks
            </button>
          )}
        </div>
      </div>

      {/* Sub-page Links */}
      <div className="space-y-3">
        <Link
          href="/settings/integrations/quickbooks/auto-expiry"
          className="flex items-center justify-between p-4 rounded-md border border-neutral-200 hover:border-brand-400 hover:bg-brand-50 transition-colors group"
        >
          <div>
            <p className="text-sm font-medium text-neutral-900">
              Auto-expiry & sync settings
            </p>
            <p className="text-xs text-neutral-500 mt-0.5">
              Configure how QB conflicts are automatically resolved
            </p>
          </div>
          <span
            className="text-neutral-400 group-hover:text-brand-600"
            aria-hidden="true"
          >
            →
          </span>
        </Link>
        <Link
          href="/settings/integrations/quickbooks/conflicts"
          className="flex items-center justify-between p-4 rounded-md border border-neutral-200 hover:border-brand-400 hover:bg-brand-50 transition-colors group"
        >
          <div>
            <p className="text-sm font-medium text-neutral-900">
              View conflicts
            </p>
            <p className="text-xs text-neutral-500 mt-0.5">
              Review and resolve pending QuickBooks sync conflicts
            </p>
          </div>
          <span
            className="text-neutral-400 group-hover:text-brand-600"
            aria-hidden="true"
          >
            →
          </span>
        </Link>
      </div>
    </>
  );
}

export function QbIntegrationIndexPage() {
  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-semibold text-neutral-900 mb-6">
        QuickBooks Integration
      </h1>
      <RoleGate permission="settings.manage">
        <QbContent />
      </RoleGate>
    </div>
  );
}
