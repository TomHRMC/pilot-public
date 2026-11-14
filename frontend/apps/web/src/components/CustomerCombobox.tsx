/* eslint-disable react-hooks/set-state-in-effect */
"use client";

/**
 * CustomerCombobox — typeahead customer picker
 *
 * Location: apps/web/src/components/CustomerCombobox.tsx
 *
 * FE-B28: Web-app-scoped component (NOT in packages/ui — uses TanStack Query + apiClient).
 * Loads up to 200 customers and filters in-memory by display_name.
 * No extra library needed — native <input> + dropdown <ul>.
 */

import { useState, useRef, useEffect } from "react";
import { useCustomers } from "../features/customers/hooks/useCustomers";

interface CustomerComboboxProps {
  /** Current customer_id (empty string = no selection) */
  value: string;
  onChange: (customerId: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function CustomerCombobox({
  value,
  onChange,
  disabled,
  placeholder = "Search customers…",
}: CustomerComboboxProps) {
  const [inputText, setInputText] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const { data: customersData, isLoading } = useCustomers({ limit: 200 });
  const customerItems = customersData?.items ?? [];

  // Sync inputText with selected value's display_name
  const selectedCustomer = customerItems.find((c) => c.id === value);
  useEffect(() => {
    if (selectedCustomer) {
      setInputText(selectedCustomer.display_name);
    } else {
      setInputText("");
    }
  }, [selectedCustomer]);

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
        // If input doesn't match selected, restore it
        if (selectedCustomer) {
          setInputText(selectedCustomer.display_name);
        } else {
          setInputText("");
        }
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [selectedCustomer]);

  const filtered = customerItems
    .filter((c) =>
      c.display_name.toLowerCase().includes(inputText.toLowerCase()),
    )
    .slice(0, 20);

  function handleSelect(customerId: string, displayName: string) {
    onChange(customerId);
    setInputText(displayName);
    setOpen(false);
  }

  function handleClear() {
    onChange("");
    setInputText("");
    setOpen(false);
  }

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
          onFocus={() => setOpen(true)}
          disabled={disabled || isLoading}
          placeholder={isLoading ? "Loading customers…" : placeholder}
          className="w-full border border-neutral-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-400 disabled:bg-neutral-50 disabled:text-neutral-400"
          role="combobox"
          aria-expanded={open}
          aria-autocomplete="list"
          aria-controls="customer-combobox-listbox"
          aria-haspopup="listbox"
          aria-label="Customer"
        />
        {value && !disabled && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-2 text-neutral-400 hover:text-neutral-600 text-lg leading-none"
            aria-label="Clear selection"
          >
            ×
          </button>
        )}
      </div>

      {open && filtered.length > 0 && (
        <ul
          id="customer-combobox-listbox"
          className="absolute z-50 w-full mt-1 bg-white border border-neutral-200 rounded-md shadow-lg max-h-48 overflow-y-auto"
          role="listbox"
        >
          {(filtered as typeof customerItems).map((c) => (
            <li
              key={c.id}
              role="option"
              aria-selected={c.id === value}
              onMouseDown={(e) => {
                // Prevent blur before click
                e.preventDefault();
                handleSelect(c.id, c.display_name);
              }}
              className={`px-3 py-2 text-sm cursor-pointer ${
                c.id === value
                  ? "bg-brand-50 text-brand-700 font-medium"
                  : "text-neutral-700 hover:bg-brand-50"
              }`}
            >
              {c.display_name}
            </li>
          ))}
        </ul>
      )}

      {open && !isLoading && filtered.length === 0 && inputText && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-neutral-200 rounded-md shadow-lg px-3 py-2 text-sm text-neutral-500">
          No customers found
        </div>
      )}
    </div>
  );
}
