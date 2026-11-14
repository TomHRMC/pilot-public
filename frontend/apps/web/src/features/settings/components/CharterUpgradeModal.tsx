"use client";

/**
 * CharterUpgradeModal — C-B12 Part B
 *
 * Location: apps/web/src/features/settings/components/CharterUpgradeModal.tsx
 *
 * Blocking forfeiture warning modal for Charter to Teams upgrade.
 * Shows both Teams pricing options (monthly $179/mo, annual $149/mo effective),
 * a billing interval selector, and a safe default ("Keep my Charter rate").
 *
 * Pattern: always-preview-before-send (mvp-arch §16.7) + destructive
 * confirmation (forfeiture is irreversible).
 *
 * RULE 5: zero hex codes. RULE 11: no hand-memo. RULE 15: WCAG 2.2 AA —
 * focus trap, target size >=24px, Escape to close (safe default),
 * prefers-reduced-motion fallbacks, non-color-only status.
 */

import React, { useEffect, useRef, useState } from "react";
import {
  ExclamationTriangleIcon,
  ExclamationCircleIcon,
  XMarkIcon,
  ArrowPathIcon,
} from "@heroicons/react/24/outline";
import { NotificationBanner } from "@pilot/ui/notification-banner";
import type { BillingInterval } from "../hooks/useTenantSubscription";

interface CharterUpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpgrade: (billingInterval: BillingInterval) => Promise<void>;
  isUpgrading: boolean;
  upgradeError: string | null;
}

// Fixed pricing copy (product-defined, not dynamic data).
const CHARTER_RATE_DISPLAY = "$49/month";
const TEAMS_MONTHLY_DISPLAY = "$179/mo";
const TEAMS_ANNUAL_DISPLAY = "$149/mo (billed $1,788/yr)";

export function CharterUpgradeModal({
  isOpen,
  onClose,
  onUpgrade,
  isUpgrading,
  upgradeError,
}: CharterUpgradeModalProps) {
  const [billingInterval, setBillingInterval] =
    useState<BillingInterval>("monthly");
  const modalRef = useRef<HTMLDivElement>(null);
  const safeDefaultRef = useRef<HTMLButtonElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);

  // Capture the trigger element on open so we can restore focus on close.
  useEffect(() => {
    if (isOpen) {
      triggerRef.current = document.activeElement as HTMLElement;
      // Focus the safe-default button on open.
      const timer = setTimeout(() => {
        safeDefaultRef.current?.focus();
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  // Restore focus to the trigger on close.
  useEffect(() => {
    return () => {
      if (!isOpen) {
        triggerRef.current?.focus();
      }
    };
  }, [isOpen]);

  // Escape to close (safe default) + focus trap.
  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        if (!isUpgrading) {
          onClose();
        }
        return;
      }
      if (e.key === "Tab" && modalRef.current) {
        const focusable = modalRef.current.querySelectorAll(
          'button, [href], input, [tabindex]:not([tabindex="-1"])',
        );
        if (focusable.length === 0) return;
        const first = focusable[0] as HTMLElement;
        const last = focusable[focusable.length - 1] as HTMLElement;
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, isUpgrading, onClose]);

  function handleOverlayClick() {
    // Overlay click is suppressed during loading (spec §5.2).
    if (!isUpgrading) {
      onClose();
    }
  }

  async function handleConfirm() {
    try {
      await onUpgrade(billingInterval);
    } catch {
      // Error is surfaced via the upgradeError prop (mutation error state).
      // The modal stays open so the user can retry or cancel.
    }
  }

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-neutral-900/50 z-50 flex items-start justify-center motion-safe:transition-opacity"
      onClick={handleOverlayClick}
      role="dialog"
      aria-modal="true"
      aria-label="Upgrade to Teams — Charter rate forfeiture warning"
    >
      <div
        ref={modalRef}
        className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-auto mt-16 p-6 motion-safe:transition-transform"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header row */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <ExclamationTriangleIcon
              className="w-6 h-6 text-alert-600 shrink-0"
              aria-hidden="true"
            />
            <h2
              id="charter-upgrade-heading"
              className="text-h2 font-semibold text-neutral-900"
            >
              You&apos;ll lose your Charter rate.
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded-md p-2.5 focus-visible:ring-2 focus-visible:ring-brand-500"
            aria-label="Close modal"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Current rate display */}
        <p className="text-body text-neutral-700 mt-1">
          You&apos;re on {CHARTER_RATE_DISPLAY}, locked.
        </p>

        {/* Teams pricing display */}
        <div className="mt-4">
          <p className="text-body text-neutral-700 mb-1">
            Moving to Teams means:
          </p>
          <ul className="space-y-1.5 list-disc list-inside">
            <li className="text-body text-neutral-900">
              <span className="text-neutral-400">$179/month</span> if you pay
              monthly
            </li>
            <li className="text-body text-neutral-900">
              <span className="text-neutral-400">$149/month</span> if you pay
              annually ($1,788/year)
            </li>
          </ul>
        </div>

        {/* Forfeiture warning callout */}
        <div className="mt-4 flex items-start gap-1.5 bg-fault-50 border border-fault-200 rounded-md p-3">
          <ExclamationCircleIcon
            className="w-4 h-4 text-fault-600 mt-0.5 shrink-0"
            aria-hidden="true"
          />
          <p className="text-body text-fault-600">
            The Charter rate is gone for good — you can&apos;t get it back
            later, even if you move back to Starter.
          </p>
        </div>

        {/* Billing interval selector */}
        <div className="mt-4">
          <span
            id="billing-interval-label"
            className="block text-sm font-medium text-neutral-700 mb-2"
          >
            Billing interval
          </span>
          <div
            role="radiogroup"
            aria-label="Billing interval"
            aria-labelledby="billing-interval-label"
            className="grid grid-cols-2 gap-3"
          >
            <button
              type="button"
              role="radio"
              aria-checked={billingInterval === "monthly"}
              onClick={() => setBillingInterval("monthly")}
              className={`px-4 py-3 rounded-md border text-left motion-safe:transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 ${
                billingInterval === "monthly"
                  ? "bg-brand-50 border-brand-500 text-brand-700"
                  : "bg-white border-neutral-200 text-neutral-700 hover:border-brand-400"
              }`}
            >
              <span className="block text-sm font-medium">Monthly</span>
              <span className="block text-caption">
                {TEAMS_MONTHLY_DISPLAY}
              </span>
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={billingInterval === "annual"}
              onClick={() => setBillingInterval("annual")}
              className={`px-4 py-3 rounded-md border text-left motion-safe:transition-colors focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-1 ${
                billingInterval === "annual"
                  ? "bg-brand-50 border-brand-500 text-brand-700"
                  : "bg-white border-neutral-200 text-neutral-700 hover:border-brand-400"
              }`}
            >
              <span className="block text-sm font-medium">Annual</span>
              <span className="block text-caption">{TEAMS_ANNUAL_DISPLAY}</span>
            </button>
          </div>
        </div>

        {/* Error banner (inside modal, above button bar) */}
        {upgradeError && (
          <div className="mt-4">
            <NotificationBanner
              notification={{
                id: "charter-upgrade-error",
                severity: "error",
                title: upgradeError,
                createdAt: new Date(),
              }}
              onDismiss={() => {
                /* Errors are user-dismissable but do not auto-dismiss */
              }}
            />
          </div>
        )}

        {/* Button bar */}
        <div className="flex justify-end gap-3 mt-6">
          <button
            type="button"
            ref={safeDefaultRef}
            onClick={onClose}
            className="bg-brand-600 text-white rounded-md px-4 py-2.5 min-h-11 text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            Keep my Charter rate
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isUpgrading}
            className="bg-fault-600 text-white rounded-md px-4 py-2.5 min-h-11 text-sm font-medium hover:bg-fault-700 focus-visible:ring-2 focus-visible:ring-fault-500 disabled:bg-neutral-300 disabled:cursor-not-allowed inline-flex items-center justify-center"
          >
            {isUpgrading && (
              <ArrowPathIcon
                className="w-4 h-4 mr-2 animate-spin motion-reduce:hidden"
                aria-hidden="true"
              />
            )}
            {isUpgrading ? "Upgrading…" : "I understand — upgrade to Teams"}
          </button>
        </div>
      </div>
    </div>
  );
}
