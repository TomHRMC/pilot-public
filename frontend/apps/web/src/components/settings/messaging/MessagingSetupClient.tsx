"use client";

/**
 * MessagingSetupClient — C-B9
 *
 * Location: apps/web/src/components/settings/messaging/MessagingSetupClient.tsx
 *
 * Main orchestrator component. Manages state-driven panel switching based on
 * the provisioning status. Polls GET /messaging/status. Handles Stripe
 * Checkout return query params.
 *
 * UI spec §4.1 + §3 (state-driven panel switching logic).
 * RULE 5: zero hex codes. RULE 11: no hand-memo. RULE 14: client-side data.
 */

import React, { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  RoleGate,
  LoadingState,
  ErrorState,
  NotificationQueueProvider,
  useNotificationQueue,
} from "@pilot/ui";
import { CheckCircleIcon } from "@heroicons/react/24/solid";
import { useProvisioningStatus } from "@/features/messaging/hooks/useProvisioningStatus";
import { use10DlcProfile } from "@/features/sms-compliance/hooks/use10DlcProfile";
import {
  type MessagingStatus,
  type EntityType,
  getErrorVariant,
  formatPhoneNumber,
} from "@/features/messaging/types";
import { EntityTypeSelector } from "./EntityTypeSelector";
import { BrandRegistrationForm } from "./BrandRegistrationForm";
import { CarrierQuoteDisplay } from "./CarrierQuoteDisplay";
import { CheckoutRedirectButton } from "./CheckoutRedirectButton";
import { OtpEntryPanel } from "./OtpEntryPanel";
import { ProvisioningStatusIndicator } from "./ProvisioningStatusIndicator";
import { ProvisioningErrorPanel } from "./ProvisioningErrorPanel";
import { PhoneNumberSelector } from "./PhoneNumberSelector";

function MessagingSetupContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { addNotification } = useNotificationQueue();

  const {
    data: statusData,
    isPending,
    isError,
    refetch,
  } = useProvisioningStatus();
  const { data: profile } = use10DlcProfile();

  const [entityType, setEntityType] = useState<EntityType | null>(null);

  // Handle Stripe Checkout return query params
  useEffect(() => {
    const checkoutStatus = searchParams.get("status");
    if (checkoutStatus === "paid") {
      addNotification({
        id: `stripe-paid-${Date.now()}`,
        severity: "success",
        title: "Payment received — provisioning your brand now.",
        dismissAfterMs: 5000,
      });
      router.replace("/settings/messaging");
    } else if (checkoutStatus === "cancelled") {
      addNotification({
        id: `stripe-cancelled-${Date.now()}`,
        severity: "warning",
        title: "Payment cancelled. You can retry when ready.",
        dismissAfterMs: 5000,
      });
      router.replace("/settings/messaging");
    }
  }, [searchParams, router, addNotification]);

  // ── Data states ────────────────────────────────────────────────────────────

  if (isPending) {
    return <LoadingState type="inline" label="Loading messaging setup..." />;
  }

  if (isError) {
    return (
      <ErrorState
        type="server"
        title="Could not load messaging status"
        description="Check your connection and try again."
        onRetry={() => void refetch()}
      />
    );
  }

  // statusData === null means 404 (not_started)
  const status: MessagingStatus | null =
    (statusData?.status as MessagingStatus) ?? null;
  const currentEntityType: EntityType =
    (statusData?.entity_type as EntityType) ?? entityType ?? "standard";

  return (
    <div className="space-y-6" data-testid="messaging-setup-client">
      {/* Page header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-h1 font-semibold text-neutral-900">
            Text Messaging Setup
          </h1>
          <p className="text-body text-neutral-500 mt-1">
            Register your business with the carrier network to send compliant
            SMS messages. Carrier fees apply.
          </p>
        </div>
      </div>

      {/* Status indicator — always visible once provisioning has started */}
      {status && status !== "not_started" && (
        <ProvisioningStatusIndicator
          status={status}
          entityType={currentEntityType}
        />
      )}

      {/* State-driven panel */}
      {status === null && (
        // not_started — initial panel
        <div className="bg-white rounded-lg border border-neutral-200 shadow-sm p-6 space-y-6">
          <EntityTypeSelector value={entityType} onChange={setEntityType} />
          {entityType && (
            <BrandRegistrationForm
              entityType={entityType}
              onProvisioned={() => void refetch()}
            />
          )}
        </div>
      )}

      {status === "quoting" && (
        <div className="space-y-4">
          <CarrierQuoteDisplay
            quote={
              statusData
                ? {
                    entity_type: statusData.entity_type,
                    setup_total_millicents: statusData.quoted_setup_cents ?? 0,
                    recurring_monthly_millicents:
                      statusData.quoted_monthly_cents ?? 0,
                    setup_items: [],
                    recurring_items: [],
                  }
                : null
            }
          />
          <RoleGate permission="settings.manage">
            <CheckoutRedirectButton />
          </RoleGate>
        </div>
      )}

      {status === "awaiting_payment" && (
        <div className="space-y-4">
          <CarrierQuoteDisplay
            quote={
              statusData
                ? {
                    entity_type: statusData.entity_type,
                    setup_total_millicents: statusData.quoted_setup_cents ?? 0,
                    recurring_monthly_millicents:
                      statusData.quoted_monthly_cents ?? 0,
                    setup_items: [],
                    recurring_items: [],
                  }
                : null
            }
            readOnly
          />
          <div className="bg-white rounded-lg border border-neutral-200 shadow-sm p-6 text-center">
            <p className="text-sm text-neutral-500">
              Waiting for payment confirmation...
            </p>
          </div>
        </div>
      )}

      {status === "payment_failed" && (
        <ProvisioningErrorPanel
          variant="payment_failed"
          failureReason={statusData?.failure_reason ?? null}
          onRetry={() => void refetch()}
        />
      )}

      {(status === "brand_submitted" ||
        status === "brand_verified" ||
        status === "campaign_submitted" ||
        status === "number_assigned") && (
        <div className="bg-white rounded-lg border border-neutral-200 shadow-sm p-6 text-center">
          <p className="text-sm text-neutral-500">
            {status === "brand_submitted" &&
              "Your brand registration is being processed by the carrier. This may take a few minutes."}
            {status === "brand_verified" &&
              "Brand verified! Campaign registration is being submitted..."}
            {status === "campaign_submitted" &&
              "Campaign registration is being reviewed by the carrier. This may take a few minutes."}
            {status === "number_assigned" &&
              "Phone number assigned! Activating your messaging..."}
          </p>
        </div>
      )}

      {status === "awaiting_otp" && (
        <OtpEntryPanel
          supportPhone={profile?.support_phone ?? null}
          otpRequestedAt={statusData?.otp_requested_at ?? null}
        />
      )}

      {status === "awaiting_number_selection" && (
        <PhoneNumberSelector onAssigned={() => void refetch()} />
      )}

      {status === "active" && (
        <div
          className="bg-white rounded-lg border border-margin-200 p-6 space-y-4"
          data-testid="messaging-success"
        >
          <div className="flex items-center gap-2">
            <CheckCircleIcon className="w-6 h-6 text-margin-600" />
            <h2 className="text-h2 font-semibold text-margin-600">
              Text Messaging is Active
            </h2>
          </div>
          <p className="text-sm text-neutral-900">
            Your dedicated SMS number is ready.
          </p>
          <p className="text-lg font-medium text-neutral-900">
            {formatPhoneNumber(statusData?.telnyx_phone_number ?? null)}
          </p>
          <p className="text-sm text-neutral-500">
            You can now send and receive SMS messages with customers.
            Per-message carrier surcharges apply (~$0.003/segment).
          </p>
          <a
            href="/settings/communications/sms-compliance"
            className="inline-block border border-brand-600 text-brand-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-50 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none"
          >
            Go to SMS Settings
          </a>
        </div>
      )}

      {status && getErrorVariant(status) && status !== "payment_failed" && (
        <ProvisioningErrorPanel
          variant={getErrorVariant(status)!}
          failureReason={statusData?.failure_reason ?? null}
        />
      )}
    </div>
  );
}

export function MessagingSetupClient() {
  return (
    <NotificationQueueProvider>
      <MessagingSetupContent />
    </NotificationQueueProvider>
  );
}
