"use client";

/**
 * BrandStateNotice — C-B16 persistent inline banner (§G-17)
 *
 * Location: apps/web/src/features/tenant-site/components/BrandStateNotice.tsx
 *
 * Four state-keyed variants from `brand_status`:
 *   none/draft     → "Ready for brand submission" (brand-50)
 *   in-flight      → "Brand registration in progress" (alert-50)
 *   brand_rejected → "Brand registration was rejected" (fault-50)
 *   active/approved → "Live brand references old URL" (alert-50)
 *
 * web spec §11: role="status", aria-live="polite", color + text label + icon.
 * WCAG 1.4.1: never color-only — every variant has a title + icon.
 */

import React from "react";
import Link from "next/link";
import {
  InformationCircleIcon,
  ClockIcon,
  ExclamationCircleIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/24/solid";

type BrandStatus =
  | "none"
  | "draft"
  | "in-flight"
  | "brand_rejected"
  | "active"
  | "approved";

interface BrandStateNoticeProps {
  brandStatus: string;
}

interface VariantConfig {
  containerClass: string;
  iconClass: string;
  titleClass: string;
  bodyClass: string;
  Icon: React.ComponentType<{ className?: string }>;
  title: string;
  body: string;
  deepLink?: { label: string; href: string; className: string };
}

function getVariant(brandStatus: string): VariantConfig {
  const status = brandStatus as BrandStatus;

  switch (status) {
    case "none":
    case "draft":
      return {
        containerClass: "border-brand-200 bg-brand-50",
        iconClass: "text-brand-600",
        titleClass: "text-brand-700",
        bodyClass: "text-brand-700",
        Icon: InformationCircleIcon,
        title: "Ready for brand submission",
        body: "Your hosted site URL will be used when you submit your 10DLC brand registration. No action needed yet — publish your site, then complete your brand registration from Messaging Setup.",
        deepLink: {
          label: "Go to Messaging Setup →",
          href: "/settings/messaging",
          className:
            "text-brand-600 hover:text-brand-800 underline focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2 focus-visible:rounded-sm",
        },
      };

    case "in-flight":
      return {
        containerClass: "border-alert-200 bg-alert-50",
        iconClass: "text-alert-600",
        titleClass: "text-alert-700",
        bodyClass: "text-alert-700",
        Icon: ClockIcon,
        title: "Brand registration in progress",
        body: "Your 10DLC brand is currently being vetted by the carrier. The vetting process checks the URL already on file — publishing a new URL now will not update the in-flight review. Wait for the vetting outcome, then re-submit your brand from Messaging Setup if needed.",
      };

    case "brand_rejected":
      return {
        containerClass: "border-fault-200 bg-fault-50",
        iconClass: "text-fault-600",
        titleClass: "text-fault-600",
        bodyClass: "text-fault-600",
        Icon: ExclamationCircleIcon,
        title: "Brand registration was rejected",
        body: "Your 10DLC brand registration was rejected. If the rejection was due to website content, publish your hosted compliance site (which includes all required SMS disclosure language), then re-submit your brand from Messaging Setup.",
        deepLink: {
          label: "Go to Messaging Setup →",
          href: "/settings/messaging",
          className:
            "font-medium text-fault-600 hover:text-fault-700 underline focus-visible:outline-2 focus-visible:outline-fault-400 focus-visible:outline-offset-2 focus-visible:rounded-sm",
        },
      };

    case "active":
    case "approved":
      return {
        containerClass: "border-alert-200 bg-alert-50",
        iconClass: "text-alert-600",
        titleClass: "text-alert-700",
        bodyClass: "text-alert-700",
        Icon: ExclamationTriangleIcon,
        title: "Your brand is live — updating the URL may trigger re-vetting",
        body: "Your 10DLC brand is approved and currently references the URL on file. Publishing a new URL and updating your profile may cause the carrier to re-vet your brand. Proceed with caution — if your current URL is working, consider keeping it.",
      };

    default:
      return {
        containerClass: "border-brand-200 bg-brand-50",
        iconClass: "text-brand-600",
        titleClass: "text-brand-700",
        bodyClass: "text-brand-700",
        Icon: InformationCircleIcon,
        title: "Ready for brand submission",
        body: "Your hosted site URL will be used when you submit your 10DLC brand registration. No action needed yet — publish your site, then complete your brand registration from Messaging Setup.",
        deepLink: {
          label: "Go to Messaging Setup →",
          href: "/settings/messaging",
          className:
            "text-brand-600 hover:text-brand-800 underline focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2 focus-visible:rounded-sm",
        },
      };
  }
}

export function BrandStateNotice({ brandStatus }: BrandStateNoticeProps) {
  const variant = getVariant(brandStatus);
  const { Icon } = variant;

  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex items-start gap-3 rounded-lg border p-4 ${variant.containerClass}`}
      data-testid="brand-state-notice"
      data-brand-status={brandStatus}
    >
      <Icon
        className={`mt-0.5 h-5 w-5 shrink-0 ${variant.iconClass}`}
        aria-hidden="true"
      />
      <div className="flex-1 space-y-1">
        <p className={`text-sm font-semibold ${variant.titleClass}`}>
          {variant.title}
        </p>
        <p className={`text-sm ${variant.bodyClass}`}>{variant.body}</p>
        {variant.deepLink && (
          <div className="pt-1">
            <Link
              href={variant.deepLink.href}
              className={`inline-block py-1 text-sm ${variant.deepLink.className}`}
            >
              {variant.deepLink.label}
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
