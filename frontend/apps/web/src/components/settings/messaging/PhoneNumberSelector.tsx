"use client";

/**
 * PhoneNumberSelector — C-B9
 *
 * Location: apps/web/src/components/settings/messaging/PhoneNumberSelector.tsx
 *
 * Allows the tenant to search for and select an available phone number
 * from the carrier's inventory. Appears at awaiting_number_selection status.
 *
 * UI spec §4.10. WCAG 2.2 AA: ≥44px rows, color-independent selection.
 * RULE 5: zero hex codes. RULE 11: no hand-memo.
 */

import React, { useState } from "react";
import {
  CheckCircleIcon,
  InformationCircleIcon,
} from "@heroicons/react/24/outline";
import { CheckCircleIcon as CheckCircleIconSolid } from "@heroicons/react/24/solid";
import { ErrorState, EmptyState } from "@pilot/ui";
import { useAvailablePhoneNumbers } from "@/features/messaging/hooks/useAvailablePhoneNumbers";
import { useAssignPhoneNumber } from "@/features/messaging/hooks/useAssignPhoneNumber";
import { useNotificationQueue } from "@pilot/ui";
import { formatPhoneNumber } from "@/features/messaging/types";

export interface PhoneNumberSelectorProps {
  onAssigned?: (phoneNumber: string) => void;
}

export function PhoneNumberSelector({ onAssigned }: PhoneNumberSelectorProps) {
  const [areaCode, setAreaCode] = useState("");
  const [searchAreaCode, setSearchAreaCode] = useState<string | null>(null);
  const [selectedNumber, setSelectedNumber] = useState<string | null>(null);

  const { data, isPending, isError, refetch } =
    useAvailablePhoneNumbers(searchAreaCode);
  const assignNumber = useAssignPhoneNumber();
  const { addNotification } = useNotificationQueue();

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const cleaned = areaCode.replace(/\D/g, "");
    if (cleaned.length === 3) {
      setSearchAreaCode(cleaned);
      setSelectedNumber(null);
    }
  }

  async function handleAssign() {
    if (!selectedNumber) return;
    try {
      const result = await assignNumber.mutateAsync({
        phone_number: selectedNumber,
      });
      onAssigned?.(result.telnyx_phone_number);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response
        ?.status;
      if (status === 409) {
        addNotification({
          id: `assign-409-${Date.now()}`,
          severity: "error",
          title: "Number no longer available. Search again.",
        });
      } else {
        addNotification({
          id: `assign-err-${Date.now()}`,
          severity: "error",
          title: "Could not assign number. Please try again.",
        });
      }
    }
  }

  const numbers = data?.numbers ?? [];
  const isAssignPending = assignNumber.isPending;

  return (
    <div
      className="bg-white rounded-lg border border-neutral-200 shadow-sm p-6 space-y-4"
      data-testid="phone-number-selector"
    >
      <div>
        <h2 className="text-h2 font-semibold text-neutral-900">
          Choose Your Phone Number
        </h2>
        <p className="text-sm text-neutral-500 mt-1">
          Select a local number for your SMS messaging. This is the number
          customers will see.
        </p>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-3 items-end">
        <div>
          <label
            htmlFor="area-code"
            className="block text-sm font-medium text-neutral-700 mb-1"
          >
            Area code
          </label>
          <input
            id="area-code"
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            maxLength={3}
            value={areaCode}
            onChange={(e) => setAreaCode(e.target.value.replace(/\D/g, ""))}
            placeholder="302"
            className="w-32 border border-neutral-200 rounded-md px-3 py-2 text-sm text-neutral-900 focus:ring-2 focus:ring-brand-400 focus:border-transparent focus:outline-none"
            data-testid="area-code-input"
          />
        </div>
        <button
          type="submit"
          disabled={areaCode.length !== 3}
          className="border border-neutral-300 text-neutral-700 rounded-md px-4 py-2 text-sm font-medium hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none active:bg-neutral-100 disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="search-numbers-button"
        >
          Search
        </button>
      </form>

      {/* Results */}
      {searchAreaCode && isPending && (
        <div className="space-y-2" data-testid="numbers-loading">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex items-center gap-3 px-4 py-3 border border-neutral-100 rounded-md animate-pulse"
            >
              <div className="w-5 h-5 bg-neutral-100 rounded-full" />
              <div className="flex-1 h-4 bg-neutral-100 rounded" />
            </div>
          ))}
        </div>
      )}

      {searchAreaCode && isError && (
        <ErrorState
          type="server"
          title="Could not search numbers"
          description="Check your connection and try again."
          onRetry={() => void refetch()}
        />
      )}

      {searchAreaCode && !isPending && !isError && numbers.length === 0 && (
        <EmptyState
          type="no-data"
          title="No numbers found"
          description="Try a different area code."
        />
      )}

      {searchAreaCode && !isPending && !isError && numbers.length > 0 && (
        <fieldset className="space-y-2">
          <legend className="sr-only">Available phone numbers</legend>
          <p className="text-sm font-medium text-neutral-700">
            Available Numbers
          </p>
          <div className="border border-neutral-200 rounded-md divide-y divide-neutral-100">
            {numbers.map((num) => {
              const isSelected = selectedNumber === num.phone_number;
              return (
                <label
                  key={num.phone_number}
                  className={`flex items-center gap-3 px-4 py-3 cursor-pointer hover:bg-neutral-50 focus-within:ring-2 focus-within:ring-brand-500 ${
                    isSelected ? "bg-brand-50 ring-1 ring-brand-500" : ""
                  }`}
                >
                  <input
                    type="radio"
                    name="phone-number"
                    value={num.phone_number}
                    checked={isSelected}
                    onChange={() => setSelectedNumber(num.phone_number)}
                    className="sr-only"
                  />
                  {isSelected ? (
                    <CheckCircleIconSolid className="w-5 h-5 text-brand-600 shrink-0" />
                  ) : (
                    <CheckCircleIcon className="w-5 h-5 text-neutral-400 shrink-0" />
                  )}
                  <div className="flex-1 flex justify-between items-center">
                    <span className="text-sm font-medium text-neutral-900 font-mono">
                      {formatPhoneNumber(num.phone_number)}
                    </span>
                    <span className="text-sm text-neutral-500">
                      {num.locality}, {num.region}
                    </span>
                  </div>
                </label>
              );
            })}
          </div>
        </fieldset>
      )}

      {/* Info callout */}
      <div className="bg-neutral-50 border border-neutral-200 rounded-md p-3 text-xs text-neutral-600 flex items-start gap-2">
        <InformationCircleIcon className="w-4 h-4 shrink-0 mt-0.5" />
        <p>
          Local numbers build trust with customers. Toll-free numbers are
          available on request.
        </p>
      </div>

      {/* Assign button */}
      <button
        type="button"
        onClick={() => void handleAssign()}
        disabled={!selectedNumber || isAssignPending}
        aria-label="Assign selected phone number"
        aria-disabled={!selectedNumber || isAssignPending}
        className="w-full bg-brand-600 text-white rounded-md px-4 py-3 text-sm font-medium hover:bg-brand-700 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:outline-none active:bg-brand-700 disabled:opacity-50 disabled:cursor-not-allowed"
        data-testid="assign-number-button"
      >
        {isAssignPending ? "Assigning..." : "Assign This Number"}
      </button>
    </div>
  );
}
