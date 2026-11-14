/**
 * DataExportSection — FE-B12
 *
 * Location: apps/web/src/features/account-settings/components/DataExportSection.tsx
 *
 * RULE: TanStack Query polling (refetchInterval=10000) while status is pending/processing.
 *       NOT useOptimisticMutation — data export is a purely online async task.
 *
 * Design doc Section H token audit:
 * - pending/processing: alert-100 bg, alert-700 text
 * - ready: success-50 bg, success-700 text
 * - Download CTA: brand-500 bg, white text
 * - expired: neutral-100 bg, neutral-500 text
 * - failed: error-50 bg, error-700 text
 */

"use client";

import React from "react";
import { useDataExport } from "../hooks/useDataExport";
import type { DataExportStatusResponse, DataExportStatus } from "../types";

// ─── Status Pill ──────────────────────────────────────────────────────────────

function StatusPill({ status }: { status: DataExportStatus }) {
  const styles: Record<DataExportStatus, string> = {
    pending: "bg-alert-100 text-alert-700",
    processing: "bg-alert-100 text-alert-700",
    ready: "bg-success-50 text-success-700",
    expired: "bg-neutral-100 text-neutral-500",
    failed: "bg-error-50 text-error-700",
  };
  const labels: Record<DataExportStatus, string> = {
    pending: "Queued…",
    processing: "Processing…",
    ready: "Ready",
    expired: "Expired",
    failed: "Failed",
  };

  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${styles[status]}`}
      data-testid={`export-status-pill-${status}`}
    >
      {labels[status]}
    </span>
  );
}

// ─── Export Status Row ────────────────────────────────────────────────────────

function ExportStatusRow({
  exportRecord,
}: {
  exportRecord: DataExportStatusResponse;
}) {
  const requested = new Date(exportRecord.requested_at).toLocaleDateString();
  const expiresAt = exportRecord.expires_at
    ? new Date(exportRecord.expires_at).toLocaleDateString()
    : null;

  return (
    <div
      className="flex items-center justify-between gap-4 py-3 border-b border-neutral-100 last:border-b-0"
      data-testid={`export-row-${exportRecord.export_id}`}
    >
      <div>
        <p className="text-sm text-neutral-800">Requested {requested}</p>
        {expiresAt && exportRecord.status === "ready" && (
          <p className="text-xs text-neutral-400">Link expires {expiresAt}</p>
        )}
        {exportRecord.status === "expired" && (
          <p className="text-xs text-neutral-500">Link expired</p>
        )}
        {exportRecord.failure_reason && (
          <p className="text-xs text-error-600">
            {exportRecord.failure_reason}
          </p>
        )}
      </div>

      <div className="flex items-center gap-3">
        <StatusPill status={exportRecord.status} />
        {exportRecord.status === "ready" && exportRecord.signed_url && (
          <a
            href={exportRecord.signed_url}
            download
            className="rounded-md bg-brand-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-1"
            data-testid={`download-export-${exportRecord.export_id}`}
          >
            Download
          </a>
        )}
      </div>
    </div>
  );
}

// ─── Active Export Status ─────────────────────────────────────────────────────

function ActiveExportStatus({
  status,
  signedUrl,
  expiresAt,
  failureReason,
  onRetry,
}: {
  status: DataExportStatus | "idle";
  signedUrl: string | null;
  expiresAt: string | null;
  failureReason: string | null;
  onRetry: () => void;
}) {
  if (status === "idle") return null;

  return (
    <div
      className="rounded-lg border border-neutral-200 p-4"
      data-testid="active-export-status"
    >
      <div className="flex items-center gap-3">
        {(status === "pending" || status === "processing") && (
          <>
            <div className="animate-spin h-4 w-4 rounded-full border-2 border-alert-500 border-t-transparent" />
            <div>
              <p className="text-sm font-medium text-neutral-800">
                {status === "pending"
                  ? "Export queued…"
                  : "Building your export (~5–15 min)…"}
              </p>
              <p className="text-xs text-neutral-400">
                We&apos;ll update this when your export is ready.
              </p>
            </div>
          </>
        )}

        {status === "ready" && signedUrl && (
          <>
            <div className="flex-1">
              <p className="text-sm font-medium text-success-700">
                Your export is ready!
              </p>
              {expiresAt && (
                <p className="text-xs text-neutral-400">
                  Link expires {new Date(expiresAt).toLocaleDateString()}
                </p>
              )}
            </div>
            <a
              href={signedUrl}
              download
              className="rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-600 focus:ring-offset-1"
              data-testid="active-download-link"
            >
              Download
            </a>
          </>
        )}

        {status === "failed" && (
          <>
            <div className="flex-1">
              <p className="text-sm font-medium text-error-700">
                Export failed
              </p>
              {failureReason && (
                <p className="text-xs text-neutral-500">{failureReason}</p>
              )}
            </div>
            <button
              type="button"
              onClick={onRetry}
              className="text-sm text-brand-600 hover:text-brand-800 focus:outline-none focus:underline"
            >
              Try again
            </button>
          </>
        )}

        {status === "expired" && (
          <p className="text-sm text-neutral-500">
            Your previous export link has expired.
          </p>
        )}
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function DataExportSection() {
  const {
    activeExportId,
    activeExportStatus,
    currentStatus,
    recentExports,
    isRequesting,
    requestError,
    requestExport,
  } = useDataExport();

  return (
    <div className="flex flex-col gap-6" data-testid="data-export-section">
      <div>
        <h2 className="text-base font-semibold text-neutral-900">
          Export your data
        </h2>
        <p className="mt-1 text-sm text-neutral-500">
          Download a copy of all your Pilot data in JSON format.
        </p>
      </div>

      {/* Request error */}
      {requestError && (
        <div
          role="alert"
          className="rounded-md border border-fault-200 bg-fault-50 p-3 text-sm text-fault-700"
        >
          {requestError instanceof Error
            ? requestError.message
            : "Failed to request export."}
        </div>
      )}

      {/* Active export status */}
      {activeExportId && (
        <ActiveExportStatus
          status={currentStatus}
          signedUrl={activeExportStatus?.signed_url ?? null}
          expiresAt={activeExportStatus?.expires_at ?? null}
          failureReason={activeExportStatus?.failure_reason ?? null}
          onRetry={requestExport}
        />
      )}

      {/* Request export button (only when no active export in progress) */}
      {currentStatus === "idle" && (
        <button
          type="button"
          onClick={requestExport}
          disabled={isRequesting}
          className="self-start rounded-lg border border-neutral-200 bg-white px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-1 disabled:opacity-50"
          data-testid="request-export-btn"
        >
          {isRequesting ? "Requesting…" : "Request export"}
        </button>
      )}

      {/* Recent exports */}
      {recentExports.length > 0 && (
        <div>
          <h3 className="mb-2 text-sm font-medium text-neutral-700">
            Previous exports
          </h3>
          <div className="rounded-lg border border-neutral-200 overflow-hidden">
            {recentExports.map((exp) => (
              <ExportStatusRow key={exp.export_id} exportRecord={exp} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
