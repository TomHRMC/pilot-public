/**
 * InvoiceSignoffCard — CE-1 Part C (Web)
 *
 * Location: apps/web/src/features/invoices/components/InvoiceSignoffCard.tsx
 *
 * Display card showing the customer's captured signature for an invoice.
 * Four states: populated, empty (no signature), loading (skeleton), error.
 *
 * Spec: batch-ce-1-web-ui-design-spec.md §2
 * - Populated: signature image + metadata grid (signer, signed_at, captured_by,
 *   conditional client_capture_at, conditional superseded history)
 * - Empty: composed <EmptyState> (no CTA — capture is mobile-only, §G-R3)
 * - Loading: skeleton (animate-pulse with reduced-motion fallback)
 * - Error: composed <ErrorState> with retry
 * - Image onError → refetch() to recover from expired presigned URL (§2.6)
 *
 * RULE: No hand-written useMemo/useCallback (React Compiler, §32)
 * RULE: Token-only styling (no hardcoded design values, §5)
 * RULE: apiClient via useInvoiceSignoff hook (never raw fetch, §2)
 */

"use client";

import { useState } from "react";
import { EmptyState, ErrorState } from "@pilot/ui/states";
import {
  PencilSquareIcon,
  InformationCircleIcon,
  ClockIcon,
  ArrowPathIcon,
} from "@heroicons/react/24/outline";
import { useInvoiceSignoff } from "../hooks/useInvoiceSignoff";

interface InvoiceSignoffCardProps {
  invoiceId: string;
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function InvoiceSignoffCard({ invoiceId }: InvoiceSignoffCardProps) {
  const { data, isLoading, isError, refetch } = useInvoiceSignoff(invoiceId);
  const [imgError, setImgError] = useState(false);

  // ── Loading state (skeleton) ──────────────────────────────────────────────
  if (isLoading) {
    return (
      <div
        className="mt-4 rounded-md border border-neutral-200 bg-white px-4 py-4"
        data-testid="signoff-card"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center">
            <PencilSquareIcon className="w-5 h-5 text-neutral-400 mr-2" />
            <h3 className="text-sm font-semibold text-neutral-700">
              Customer Sign-off
            </h3>
          </div>
        </div>
        <div
          className="h-40 w-full rounded-md bg-neutral-100 animate-pulse motion-reduce:animate-none"
          data-testid="signoff-skeleton-img"
        />
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2">
          <div className="h-4 w-48 rounded bg-neutral-100 animate-pulse motion-reduce:animate-none" />
          <div className="h-4 w-48 rounded bg-neutral-100 animate-pulse motion-reduce:animate-none" />
        </div>
      </div>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div
        className="mt-4 rounded-md border border-neutral-200 bg-white px-4 py-4"
        data-testid="signoff-card"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center">
            <PencilSquareIcon className="w-5 h-5 text-neutral-400 mr-2" />
            <h3 className="text-sm font-semibold text-neutral-700">
              Customer Sign-off
            </h3>
          </div>
        </div>
        <ErrorState
          type="server"
          title="Could not load signature"
          description="Check your connection and try again."
          onRetry={() => void refetch()}
        />
      </div>
    );
  }

  const signoff = data?.signoff ?? null;
  const supersededCount = data?.supersededCount ?? 0;

  // ── Empty state (no active signoff) ───────────────────────────────────────
  if (!signoff) {
    return (
      <div
        className="mt-4 rounded-md border border-neutral-200 bg-white px-4 py-4"
        data-testid="signoff-card"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center">
            <PencilSquareIcon className="w-5 h-5 text-neutral-400 mr-2" />
            <h3 className="text-sm font-semibold text-neutral-700">
              Customer Sign-off
            </h3>
          </div>
        </div>
        <EmptyState
          type="no-results"
          title="No signature captured"
          description="The customer's signature is captured from the mobile app at job sign-off. Once a technician completes sign-off in the field, the signature appears here."
        />
      </div>
    );
  }

  // ── Populated state ───────────────────────────────────────────────────────
  const showClientCaptureAt =
    signoff.client_capture_at !== null &&
    signoff.client_capture_at !== signoff.signed_at;

  // §2.7 — no useUser hook exists; ship UUID fallback (follow-up ticket noted)
  const capturedByDisplay = `User ${signoff.captured_by_user_id.slice(0, 8)}`;

  // Image-load error recovery: refetch to get a fresh presigned URL
  const showImgRefreshing = imgError;

  return (
    <div
      className="mt-4 rounded-md border border-neutral-200 bg-white px-4 py-4"
      data-testid="signoff-card"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center">
          <PencilSquareIcon className="w-5 h-5 text-neutral-400 mr-2" />
          <h3 className="text-sm font-semibold text-neutral-700">
            Customer Sign-off
          </h3>
        </div>
      </div>

      {/* Signature image */}
      {showImgRefreshing ? (
        <div
          className="flex flex-col items-center justify-center bg-neutral-100 h-40 rounded-md"
          data-testid="signoff-img-refreshing"
        >
          <ArrowPathIcon className="w-5 h-5 text-neutral-400 animate-spin motion-reduce:animate-none" />
          <p className="mt-1 text-xs text-neutral-500">Refreshing signature…</p>
        </div>
      ) : (
        // eslint-disable-next-line @next/next/no-img-element -- presigned S3 URL with onError refetch recovery (spec §2.6); next/image doesn't support the onError→refetch pattern needed for 1h TTL recovery
        <img
          src={signoff.signature_url}
          alt={`Customer signature: ${signoff.signed_by_name}`}
          className="block rounded-md border border-neutral-200 bg-neutral-50 max-h-40 w-auto object-contain"
          data-testid="signoff-signature-img"
          onError={() => {
            setImgError(true);
            void refetch();
          }}
          onLoad={() => setImgError(false)}
        />
      )}

      {/* Metadata grid */}
      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
        <div>
          <span className="text-neutral-500">Signed by</span>{" "}
          <span className="text-neutral-900 font-medium">
            {signoff.signed_by_name}
          </span>
        </div>
        <div>
          <span className="text-neutral-500">Signed at</span>{" "}
          <span className="text-neutral-900 font-medium">
            {formatDateTime(signoff.signed_at)}
          </span>
        </div>
        {showClientCaptureAt && (
          <div className="flex items-start gap-1">
            <span className="text-neutral-500">Captured on device</span>
            <span className="text-neutral-900 font-medium">
              {formatDateTime(signoff.client_capture_at!)}
            </span>
            <InformationCircleIcon
              className="w-4 h-4 text-neutral-400"
              title="Device clock at capture; may differ from server time when captured offline."
            />
          </div>
        )}
        <div className="flex items-start gap-1">
          <span className="text-neutral-500">Captured by</span>
          <span
            className="text-neutral-900 font-medium"
            title="Technician user ID — name resolution not yet wired."
          >
            {capturedByDisplay}
          </span>
          <InformationCircleIcon className="w-4 h-4 text-neutral-400" />
        </div>
      </div>

      {/* Superseded history line */}
      {supersededCount > 0 && (
        <div
          className="mt-3 text-xs text-neutral-500"
          data-testid="signoff-superseded-count"
        >
          <ClockIcon className="w-4 h-4 text-neutral-400 inline mr-1" />
          {supersededCount} prior signature
          {supersededCount > 1 ? "s" : ""} replaced.
        </div>
      )}
    </div>
  );
}
