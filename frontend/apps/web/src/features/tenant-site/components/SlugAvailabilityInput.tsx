"use client";

/**
 * SlugAvailabilityInput — C-B16 slug input with live availability feedback
 *
 * Location: apps/web/src/features/tenant-site/components/SlugAvailabilityInput.tsx
 *
 * URL display layout: https://[slug].p4tsites.com
 * 300ms debounce (in the component, not the hook per web spec §8).
 * Four feedback states: idle, checking, available, taken/reserved/invalid + suggestion.
 * Read-only after first publish (Design Decision #7).
 *
 * web spec §8: URL prefix/suffix, availability feedback, suggestion link.
 * Domain read from NEXT_PUBLIC_TENANT_SITES_DOMAIN — never hardcoded.
 */

import React, { useState, useEffect } from "react";
import {
  CheckIcon,
  XMarkIcon,
  LockClosedIcon,
} from "@heroicons/react/24/solid";
import { useSlugAvailability } from "../hooks/useSlugAvailability";

interface SlugAvailabilityInputProps {
  value: string;
  onChange: (slug: string) => void;
  /** When true, slug is locked (published_at is set) — read-only */
  locked?: boolean;
  /** Called when the slug is confirmed available (for form validation) */
  onAvailabilityChange?: (available: boolean) => void;
}

export function SlugAvailabilityInput({
  value,
  onChange,
  locked = false,
  onAvailabilityChange,
}: SlugAvailabilityInputProps) {
  const [debouncedSlug, setDebouncedSlug] = useState(value);

  // 300ms debounce
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSlug(value), 300);
    return () => clearTimeout(timer);
  }, [value]);

  const { data, isPending } = useSlugAvailability(locked ? "" : debouncedSlug);

  // Notify parent of availability state
  useEffect(() => {
    if (locked || !debouncedSlug) {
      onAvailabilityChange?.(false);
      return;
    }
    if (data) {
      onAvailabilityChange?.(data.available);
    }
  }, [data, locked, debouncedSlug, onAvailabilityChange]);

  const domain = process.env.NEXT_PUBLIC_TENANT_SITES_DOMAIN ?? "localhost";

  // Determine border color based on state
  const borderClass = locked
    ? "border-neutral-300"
    : data?.available
      ? "border-margin-400"
      : data && !data.available
        ? "border-fault-400"
        : "border-neutral-300";

  return (
    <div>
      <label
        htmlFor="site-slug"
        className="mb-1 text-sm font-medium text-neutral-700"
      >
        Site URL slug <span className="text-alert-600">*</span>
      </label>

      <div
        className={`flex items-center rounded-md border ${borderClass} focus-within:ring-2 focus-within:ring-brand-500 focus-within:border-brand-500`}
      >
        <span className="rounded-l-md border-r border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-500">
          https://
        </span>
        <input
          id="site-slug"
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value.toLowerCase())}
          maxLength={63}
          readOnly={locked}
          disabled={locked}
          placeholder="your-business"
          className={`flex-1 px-3 py-2 text-sm text-neutral-900 outline-none lowercase ${
            locked
              ? "cursor-not-allowed bg-neutral-50 text-neutral-500"
              : "bg-white"
          }`}
          data-testid="site-slug-input"
          aria-describedby="site-slug-feedback"
        />
        <span className="rounded-r-md border-l border-neutral-200 bg-neutral-50 px-3 py-2 text-sm text-neutral-500">
          .{domain}
        </span>
      </div>

      {/* Feedback area */}
      <div id="site-slug-feedback" className="mt-1 min-h-5">
        {locked ? (
          <div className="flex items-center gap-1.5 text-xs text-neutral-500">
            <LockClosedIcon
              className="h-4 w-4 text-neutral-400"
              aria-hidden="true"
            />
            <span>
              Slug is locked after first publish. Contact support to change it.
            </span>
          </div>
        ) : !value ? (
          <p className="text-xs text-neutral-500">
            Lowercase letters, numbers, and hyphens. Must start and end with a
            letter or number.
          </p>
        ) : isPending ? (
          <div className="flex items-center gap-1.5 text-xs text-neutral-500">
            <span
              className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-neutral-300 border-t-brand-500 motion-reduce:animate-none"
              aria-hidden="true"
            />
            <span>Checking availability…</span>
          </div>
        ) : data?.available ? (
          <div className="flex items-center gap-1.5 text-xs text-margin-700">
            <CheckIcon className="h-4 w-4 text-margin-600" aria-hidden="true" />
            <span>Available</span>
          </div>
        ) : data && !data.available ? (
          <div className="space-y-1">
            <div className="flex items-center gap-1.5 text-xs text-fault-600">
              <XMarkIcon
                className="h-4 w-4 text-fault-500"
                aria-hidden="true"
              />
              <span>
                {data.reason === "taken" && "This slug is taken"}
                {data.reason === "reserved" && "This slug is reserved"}
                {data.reason === "invalid" &&
                  "Invalid slug — use lowercase letters, numbers, and hyphens only"}
                {!data.reason && "This slug is not available"}
              </span>
            </div>
            {data.suggestion && (
              <button
                type="button"
                onClick={() => onChange(data.suggestion!)}
                className="inline-block py-1 text-xs text-brand-600 underline hover:text-brand-800 focus-visible:outline-2 focus-visible:outline-brand-400 focus-visible:outline-offset-2 focus-visible:rounded-sm"
              >
                Try: {data.suggestion}
              </button>
            )}
          </div>
        ) : (
          <p className="text-xs text-neutral-500">
            Lowercase letters, numbers, and hyphens. Must start and end with a
            letter or number.
          </p>
        )}
      </div>
    </div>
  );
}
