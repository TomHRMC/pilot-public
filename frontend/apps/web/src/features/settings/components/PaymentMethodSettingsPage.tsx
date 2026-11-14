/**
 * PaymentMethodSettingsPage — UI-FIX-2F
 *
 * Location: apps/web/src/features/settings/components/PaymentMethodSettingsPage.tsx
 *
 * Route: /settings/billing/payment-method
 * RBAC: settings.tenant.write — owner and operator only
 *
 * Three connection states:
 *   1. Loading — skeleton inside status card
 *   2. Disconnected — Connect Stripe Account CTA
 *   3. Incomplete onboarding — Resume Setup CTA (connected=true, charges_enabled=false)
 *   4. Connected — account name + Disconnect button
 *
 * URL param banners (one-time, cleaned from URL after display):
 *   ?connected=true  → success banner
 *   ?retry=true      → info/retry banner
 *   ?error=connect_failed → error banner
 */

"use client";

import React, { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { RoleGate } from "@pilot/ui/role-gate";
import {
  LinkIcon,
  ArrowRightIcon,
  XCircleIcon,
  InformationCircleIcon,
  CheckIcon,
  DocumentTextIcon,
  XMarkIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";
import { CheckCircleIcon as CheckCircleSolid } from "@heroicons/react/24/solid";
import { CheckIcon as CheckSolid } from "@heroicons/react/24/solid";
import { ExclamationCircleIcon as ExclamationCircleSolid } from "@heroicons/react/24/solid";
import { useStripeConnectStatus } from "../hooks/useStripeConnectStatus";
import { useStripeConnectOnboard } from "../hooks/useStripeConnectOnboard";
import { useStripeConnectDisconnect } from "../hooks/useStripeConnectDisconnect";
import { BillingContactForm } from "./BillingContactForm";
import { SettingsBreadcrumb } from "./SettingsBreadcrumb";

// ── Skeleton loading state for the status card ───────────────────────────────

function StatusCardSkeleton() {
  return (
    <div className="bg-white border border-neutral-200 rounded-lg p-6 shadow-sm animate-pulse">
      <div className="h-5 w-40 bg-neutral-200 rounded" />
      <div className="mt-4 h-4 w-48 bg-neutral-200 rounded" />
      <div className="mt-2 h-4 w-full bg-neutral-200 rounded" />
      <div className="mt-1 h-4 w-3/4 bg-neutral-200 rounded" />
      <div className="mt-5 h-10 w-full bg-neutral-200 rounded-md" />
      <div className="mt-4 h-12 bg-neutral-100 rounded-md" />
    </div>
  );
}

// ── Disconnect confirmation modal ─────────────────────────────────────────────

interface DisconnectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isDisconnecting: boolean;
}

function DisconnectModal({
  isOpen,
  onClose,
  onConfirm,
  isDisconnecting,
}: DisconnectModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-neutral-900/50 z-50 flex items-start justify-center">
      <div
        className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 mt-16 p-6 relative"
        style={{ transform: "scale(1)" }}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          disabled={isDisconnecting}
          aria-label="Close"
          className="absolute top-4 right-4 p-1 rounded hover:text-neutral-600 text-neutral-400 disabled:opacity-50"
        >
          <XMarkIcon className="w-5 h-5" />
        </button>

        {/* Title */}
        <h2 className="text-lg font-semibold text-neutral-900">
          Disconnect Stripe?
        </h2>
        <div className="border-t border-neutral-200 mt-4 mb-4" />

        {/* Body */}
        <p className="text-sm text-neutral-700 mb-3">
          Disconnecting your Stripe account will:
        </p>
        <ul className="space-y-2">
          <li className="flex items-start">
            <ExclamationTriangleIcon className="w-4 h-4 text-fault-500 mr-2 mt-0.5 shrink-0" />
            <span className="text-sm text-neutral-700">
              Prevent new card payments on invoice payment pages
            </span>
          </li>
          <li className="flex items-start">
            <ExclamationTriangleIcon className="w-4 h-4 text-fault-500 mr-2 mt-0.5 shrink-0" />
            <span className="text-sm text-neutral-700">
              Customers will see manual payment instructions instead of a
              payment form
            </span>
          </li>
          <li className="flex items-start">
            <CheckIcon className="w-4 h-4 text-margin-600 mr-2 mt-0.5 shrink-0" />
            <span className="text-sm text-neutral-700">
              Existing recorded payments are not affected
            </span>
          </li>
        </ul>

        {/* Footer */}
        <div className="border-t border-neutral-200 mt-6 pt-4 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={isDisconnecting}
            className="border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={isDisconnecting}
            className="rounded-md bg-fault-600 px-4 py-2 text-sm font-medium text-white hover:bg-fault-700 focus:outline-none focus:ring-2 focus:ring-fault-500 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed inline-flex items-center"
          >
            {isDisconnecting ? (
              <>
                <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Disconnecting...
              </>
            ) : (
              "Disconnect Stripe"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Connection status card ────────────────────────────────────────────────────

interface StatusCardProps {
  connected: boolean;
  chargesEnabled: boolean;
  payoutsEnabled: boolean;
  accountName: string | null;
  accountId: string | null;
  onConnect: () => void;
  isConnecting: boolean;
  connectError: string | null;
  onDisconnect: () => void;
}

function StatusCard({
  connected,
  chargesEnabled,
  payoutsEnabled,
  accountName,
  accountId,
  onConnect,
  isConnecting,
  connectError,
  onDisconnect,
}: StatusCardProps) {
  // Determine display name for connected state
  const displayName =
    accountName ??
    (accountId
      ? `Stripe account (acct_…${accountId.slice(-6)})`
      : "Stripe account");

  if (!connected) {
    // Disconnected state
    return (
      <div className="bg-white border border-neutral-200 rounded-lg p-6 shadow-sm">
        <div className="flex items-center">
          <LinkIcon className="w-5 h-5 text-neutral-400 mr-2" />
          <h2 className="text-base font-medium text-neutral-900">
            Stripe Account
          </h2>
        </div>

        <p className="text-sm font-medium text-neutral-900 mt-4">
          No Stripe account connected
        </p>
        <p className="text-sm text-neutral-600 mt-1">
          Connect your Stripe account to accept card payments from your
          customers directly on invoice payment pages.
        </p>

        <button
          onClick={onConnect}
          disabled={isConnecting}
          className="mt-5 w-full inline-flex items-center justify-center rounded-md bg-brand-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-wait"
        >
          {isConnecting ? (
            <>
              <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Connecting...
            </>
          ) : (
            <>
              Connect Stripe Account
              <ArrowRightIcon className="w-4 h-4 ml-2" />
            </>
          )}
        </button>

        {connectError && (
          <p className="text-xs text-fault-600 mt-2">{connectError}</p>
        )}

        <div className="mt-4 rounded-md bg-neutral-50 border border-neutral-200 px-4 py-3 flex items-start">
          <InformationCircleIcon className="w-4 h-4 text-neutral-500 mr-2 mt-0.5 shrink-0" />
          <p className="text-xs text-neutral-600">
            You&apos;ll be redirected to Stripe&apos;s website to complete the
            connection. You&apos;ll return to Pilot after.
          </p>
        </div>
      </div>
    );
  }

  if (connected && !chargesEnabled) {
    // Incomplete onboarding state
    return (
      <div className="bg-white border border-neutral-200 rounded-lg p-6 shadow-sm">
        <div className="flex items-center">
          <LinkIcon className="w-5 h-5 text-neutral-400 mr-2" />
          <h2 className="text-base font-medium text-neutral-900">
            Stripe Account
          </h2>
          <span className="ml-2 inline-flex items-center rounded-full bg-alert-100 px-2.5 py-0.5 text-xs font-medium text-alert-700">
            Setup Incomplete
          </span>
        </div>

        <p className="text-sm font-medium text-neutral-900 mt-4">
          {displayName}
        </p>
        <p className="text-sm text-neutral-600 mt-1">
          Your Stripe account is connected but not fully set up. Complete the
          setup to start accepting card payments.
        </p>

        <button
          onClick={onConnect}
          disabled={isConnecting}
          className="mt-5 w-full inline-flex items-center justify-center rounded-md bg-brand-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2 disabled:opacity-60 disabled:cursor-wait"
        >
          {isConnecting ? (
            <>
              <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              Connecting...
            </>
          ) : (
            <>
              Resume Setup
              <ArrowRightIcon className="w-4 h-4 ml-2" />
            </>
          )}
        </button>

        {connectError && (
          <p className="text-xs text-fault-600 mt-2">{connectError}</p>
        )}

        <div className="mt-4 rounded-md bg-neutral-50 border border-neutral-200 px-4 py-3 flex items-start">
          <InformationCircleIcon className="w-4 h-4 text-neutral-500 mr-2 mt-0.5 shrink-0" />
          <p className="text-xs text-neutral-600">
            You&apos;ll be redirected to Stripe&apos;s website to complete the
            setup. You&apos;ll return to Pilot after.
          </p>
        </div>
      </div>
    );
  }

  // Fully connected state
  return (
    <div className="bg-white border border-neutral-200 rounded-lg p-6 shadow-sm">
      <div className="flex items-center">
        <CheckCircleSolid className="w-5 h-5 text-margin-600 mr-2" />
        <h2 className="text-base font-medium text-neutral-900">
          Stripe Account
        </h2>
        <span className="ml-2 inline-flex items-center rounded-full bg-margin-100 px-2.5 py-0.5 text-xs font-medium text-margin-700">
          Connected
        </span>
      </div>

      <p className="text-sm font-medium text-neutral-900 mt-4">{displayName}</p>
      <p className="text-sm text-neutral-600 mt-1">
        Customers can now pay by card on invoice payment pages.
      </p>

      {/* STRIPE-CONNECT-1-C B3: payouts-disabled warning chip (connected but payouts off) */}
      {connected && chargesEnabled && !payoutsEnabled && (
        <div
          className="mt-4 rounded-md bg-alert-50 border border-alert-200 px-4 py-3 flex items-start"
          data-testid="payouts-disabled-warning"
        >
          <ExclamationTriangleIcon className="w-4 h-4 text-alert-600 mr-2 mt-0.5 shrink-0" />
          <p className="text-xs text-alert-700">
            Connected — but payouts are disabled by Stripe. Contact Stripe
            support.
          </p>
        </div>
      )}

      <button
        onClick={onDisconnect}
        className="mt-5 inline-flex items-center rounded-md border border-fault-300 bg-white px-4 py-2 text-sm font-medium text-fault-700 shadow-sm hover:bg-fault-50 focus:outline-none focus:ring-2 focus:ring-fault-500 focus:ring-offset-2"
      >
        <XCircleIcon className="w-4 h-4 mr-1.5 text-fault-600" />
        Disconnect
      </button>
    </div>
  );
}

// ── Manual payment info section ───────────────────────────────────────────────

function ManualPaymentSection() {
  return (
    <div className="border-t border-neutral-200 mt-6 pt-6">
      <h3 className="text-base font-medium text-neutral-900 mb-3">
        Manual Payment Options
      </h3>
      <p className="text-sm text-neutral-600 mb-4">
        Even without Stripe, your customers can pay by:
      </p>
      <ul className="space-y-2">
        {[
          "Check — mail to your business address",
          "Cash — in person at time of service",
          "Zelle / Venmo — your contact details on the invoice",
          "Wire transfer — for commercial clients",
        ].map((item) => (
          <li key={item} className="flex items-start">
            <CheckSolid className="w-4 h-4 text-margin-600 mr-2 mt-0.5 shrink-0" />
            <span className="text-sm text-neutral-700">{item}</span>
          </li>
        ))}
      </ul>
      <div className="mt-4 rounded-md bg-neutral-50 border border-neutral-200 px-4 py-3 flex items-start">
        <DocumentTextIcon className="w-4 h-4 text-neutral-500 mr-2 mt-0.5 shrink-0" />
        <p className="text-xs text-neutral-600">
          When a payment is received, record it in Pilot from the invoice detail
          page → &quot;Record Payment&quot;.
        </p>
      </div>

      {/* STRIPE-CONNECT-1-C B5: billing-contact form (phone + email) */}
      <BillingContactForm />
    </div>
  );
}

// ── Banner component ──────────────────────────────────────────────────────────

type BannerType = "success" | "error" | "retry" | null;

interface BannerProps {
  type: BannerType;
  onDismiss: () => void;
}

function Banner({ type, onDismiss }: BannerProps) {
  if (!type) return null;

  const config = {
    success: {
      containerClass:
        "bg-margin-50 border border-margin-200 text-margin-800 rounded-md px-4 py-3 mb-6 flex items-start",
      icon: (
        <CheckCircleSolid className="w-5 h-5 text-margin-600 mr-3 shrink-0" />
      ),
      message:
        "Your Stripe account has been connected. Customers can now pay by card on invoice payment pages.",
    },
    error: {
      containerClass:
        "bg-fault-50 border border-fault-200 text-fault-800 rounded-md px-4 py-3 mb-6 flex items-start",
      icon: (
        <ExclamationCircleSolid className="w-5 h-5 text-fault-600 mr-3 shrink-0" />
      ),
      message: (
        <>
          Could not connect your Stripe account. Please try again or contact{" "}
          <a href="mailto:support@pilotfortrades.com" className="underline">
            support@pilotfortrades.com
          </a>{" "}
          if the issue continues.
        </>
      ),
    },
    retry: {
      containerClass:
        "bg-brand-50 border border-brand-200 text-brand-800 rounded-md px-4 py-3 mb-6 flex items-start",
      icon: (
        <InformationCircleIcon className="w-5 h-5 text-brand-600 mr-3 shrink-0" />
      ),
      message:
        "Your previous session expired. Click 'Connect Stripe Account' to try again.",
    },
  };

  const { containerClass, icon, message } = config[type];

  return (
    <div className={containerClass} role="alert">
      {icon}
      <span className="text-sm flex-1">{message}</span>
      <button
        onClick={onDismiss}
        aria-label="Dismiss"
        className="ml-3 shrink-0 hover:opacity-70"
      >
        <XMarkIcon className="w-4 h-4" />
      </button>
    </div>
  );
}

// ── Main page component ───────────────────────────────────────────────────────

function getBannerFromParams(searchParams: URLSearchParams): BannerType {
  if (searchParams.get("connected") === "true") return "success";
  if (searchParams.get("retry") === "true") return "retry";
  if (searchParams.get("error") === "connect_failed") return "error";
  return null;
}

function PaymentMethodContent() {
  const searchParams = useSearchParams();
  const [banner, setBanner] = useState<BannerType>(() =>
    getBannerFromParams(
      new URLSearchParams(
        typeof window !== "undefined" ? window.location.search : "",
      ),
    ),
  );
  const [showDisconnectModal, setShowDisconnectModal] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  const { data, isLoading, isError } = useStripeConnectStatus();
  const onboardMutation = useStripeConnectOnboard();
  const disconnectMutation = useStripeConnectDisconnect();

  // Clean URL params on mount so refresh doesn't re-show banners
  useEffect(() => {
    const hasParam =
      searchParams.get("connected") !== null ||
      searchParams.get("retry") !== null ||
      searchParams.get("error") !== null;
    if (hasParam) {
      window.history.replaceState({}, "", "/settings/billing/payment-method");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-dismiss success banner after 8 seconds
  useEffect(() => {
    if (banner === "success") {
      const timer = setTimeout(() => setBanner(null), 8000);
      return () => clearTimeout(timer);
    }
  }, [banner]);

  const handleConnect = () => {
    setConnectError(null);
    onboardMutation.mutate(undefined, {
      onSuccess: (result) => {
        window.location.href = result.account_link_url;
      },
      onError: () => {
        setConnectError(
          "Could not initiate Stripe connection. Please try again.",
        );
      },
    });
  };

  const handleDisconnectConfirm = () => {
    disconnectMutation.mutate(undefined, {
      onSuccess: () => {
        setShowDisconnectModal(false);
        setBanner("success");
      },
    });
  };

  return (
    <div className="px-6 py-6 max-w-2xl">
      {/* URL-param banners */}
      <Banner type={banner} onDismiss={() => setBanner(null)} />

      {/* Breadcrumb — PLP-FIX-5 (Issue 8) */}
      <SettingsBreadcrumb
        trail={[
          { label: "Settings", href: "/settings" },
          { label: "Payment Method" },
        ]}
      />

      {/* Page header */}
      <h1 className="text-2xl font-semibold text-neutral-900">
        Payment Method
      </h1>
      <p className="text-sm text-neutral-500 mt-1">
        Manage how your customers can pay their invoices.
      </p>

      {/* Connection status card */}
      <RoleGate permission="settings.tenant.write">
        <div className="mt-6">
          {isLoading ? (
            <StatusCardSkeleton />
          ) : isError ? (
            <div className="bg-white border border-neutral-200 rounded-lg p-6 shadow-sm">
              <p className="text-sm text-fault-700">
                Unable to load payment status. Refresh the page.
              </p>
            </div>
          ) : data ? (
            <StatusCard
              connected={data.connected}
              chargesEnabled={data.charges_enabled}
              payoutsEnabled={data.payouts_enabled}
              accountName={data.account_name ?? null}
              accountId={data.account_id ?? null}
              onConnect={handleConnect}
              isConnecting={onboardMutation.isPending}
              connectError={connectError}
              onDisconnect={() => setShowDisconnectModal(true)}
            />
          ) : null}
        </div>
      </RoleGate>

      {/* Manual payment info — always visible */}
      <ManualPaymentSection />

      {/* Disconnect confirmation modal */}
      <DisconnectModal
        isOpen={showDisconnectModal}
        onClose={() => setShowDisconnectModal(false)}
        onConfirm={handleDisconnectConfirm}
        isDisconnecting={disconnectMutation.isPending}
      />
    </div>
  );
}

export function PaymentMethodSettingsPage() {
  return <PaymentMethodContent />;
}
