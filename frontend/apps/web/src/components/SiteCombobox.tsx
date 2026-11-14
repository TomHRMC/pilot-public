/* eslint-disable react-hooks/set-state-in-effect */
"use client";

/**
 * SiteCombobox — typeahead site picker (cascades from customerId)
 *
 * Location: apps/web/src/components/SiteCombobox.tsx
 *
 * FE-B28: Web-app-scoped component (NOT in packages/ui — uses TanStack Query + apiClient).
 * Disabled when customerId is null/empty. Re-fetches when customerId changes.
 * Resets selection when customerId changes.
 */

import { useState, useRef, useEffect } from "react";
import { useCustomerSites } from "../features/customers/hooks/useCustomerSites";
import type { SiteResponse } from "../features/customers/hooks/useCustomerSites";

interface SiteComboboxProps {
  customerId: string | null;
  /** Current site_id (empty string = no selection) */
  value: string;
  onChange: (siteId: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

function getSiteLabel(site: SiteResponse): string {
  return site.name ?? site.address?.line1 ?? site.id.slice(0, 8);
}

export function SiteCombobox({
  customerId,
  value,
  onChange,
  disabled,
  placeholder = "Search sites…",
}: SiteComboboxProps) {
  const [inputText, setInputText] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // Track the previous customerId so we only reset the site selection when the
  // customer actually changes — not on initial mount (which would wipe a
  // pre-populated site_id passed in from the edit modal).
  // Using a ref (not state) so the comparison is synchronous and survives React
  // Strict-Mode's simulated remount without triggering a spurious reset.
  const prevCustomerIdRef = useRef(customerId);

  const { data: sites, isLoading } = useCustomerSites(customerId ?? undefined);

  // Reset selection only when customerId genuinely changes to a different value.
  useEffect(() => {
    if (prevCustomerIdRef.current === customerId) {
      // No change (includes initial mount and Strict-Mode's double-invoke).
      return;
    }
    prevCustomerIdRef.current = customerId;
    onChange("");
    setInputText("");
    setOpen(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [customerId]);

  // Sync inputText with selected value's label
  const selectedSite = (sites ?? []).find((s) => s.id === value);
  useEffect(() => {
    if (selectedSite) {
      setInputText(getSiteLabel(selectedSite));
    } else if (!customerId) {
      setInputText("");
    }
  }, [selectedSite, customerId]);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
        // Restore if input doesn't match selected
        if (selectedSite) {
          setInputText(getSiteLabel(selectedSite));
        }
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [selectedSite]);

  const isDisabled = disabled || !customerId || isLoading;

  const filtered = (sites ?? [])
    .filter((s) =>
      getSiteLabel(s).toLowerCase().includes(inputText.toLowerCase()),
    )
    .slice(0, 20);

  function handleSelect(siteId: string, label: string) {
    onChange(siteId);
    setInputText(label);
    setOpen(false);
  }

  function handleClear() {
    onChange("");
    setInputText("");
    setOpen(false);
  }

  const effectivePlaceholder = !customerId
    ? "Select a customer first"
    : isLoading
      ? "Loading sites…"
      : placeholder;

  return (
    <div ref={containerRef} className="relative">
      <div className="flex items-center relative">
        <input
          type="text"
          value={inputText}
          onChange={(e) => {
            setInputText(e.target.value);
            setOpen(true);
          }}
          onFocus={() => {
            if (!isDisabled) setOpen(true);
          }}
          disabled={isDisabled}
          placeholder={effectivePlaceholder}
          className="w-full border border-neutral-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-400 disabled:bg-neutral-50 disabled:text-neutral-400"
          role="combobox"
          aria-expanded={open}
          aria-autocomplete="list"
          aria-controls="site-combobox-listbox"
          aria-haspopup="listbox"
          aria-label="Site"
        />
        {value && !disabled && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-2 text-neutral-400 hover:text-neutral-600 text-lg leading-none"
            aria-label="Clear site selection"
          >
            ×
          </button>
        )}
      </div>

      {open && filtered.length > 0 && (
        <ul
          id="site-combobox-listbox"
          className="absolute z-50 w-full mt-1 bg-white border border-neutral-200 rounded-md shadow-lg max-h-48 overflow-y-auto"
          role="listbox"
        >
          {filtered.map((s) => {
            const label = getSiteLabel(s);
            return (
              <li
                key={s.id}
                role="option"
                aria-selected={s.id === value}
                onMouseDown={(e) => {
                  e.preventDefault();
                  handleSelect(s.id, label);
                }}
                className={`px-3 py-2 text-sm cursor-pointer ${
                  s.id === value
                    ? "bg-brand-50 text-brand-700 font-medium"
                    : "text-neutral-700 hover:bg-brand-50"
                }`}
              >
                {label}
              </li>
            );
          })}
        </ul>
      )}

      {open &&
        !isLoading &&
        filtered.length === 0 &&
        inputText &&
        customerId && (
          <div className="absolute z-50 w-full mt-1 bg-white border border-neutral-200 rounded-md shadow-lg px-3 py-2 text-sm text-neutral-500">
            No sites found
          </div>
        )}
    </div>
  );
}
