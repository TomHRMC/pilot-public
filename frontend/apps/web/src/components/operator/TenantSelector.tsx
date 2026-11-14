"use client";

/**
 * TenantSelector — searchable dropdown in the operator header
 *
 * Location: apps/web/src/components/operator/TenantSelector.tsx
 *
 * C-B15 Part B: Source GET /api/v1/operator/tenants. Client-side filtering
 * (§16.6 — optimistic, no refetch). Selecting a tenant:
 *   - owner/support → open ImpersonationConfirmModal
 *   - accountant → show NotificationBanner warning (hide-not-disable at action level)
 *
 * Spec §4 is binding: trigger button, dropdown panel, search input, list,
 * footer, keyboard nav, loading/empty/error/no-results states.
 *
 * RULE 5: zero hex codes. RULE 15: WCAG 2.2 AA (keyboard nav, aria, ≥24px targets).
 */

import React, { useRef, useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  BuildingOffice2Icon,
  ChevronDownIcon,
  MagnifyingGlassIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { EmptyState, ErrorState } from "@pilot/ui/states";
import { useNotificationQueue } from "@pilot/ui/notification-banner";
import {
  useOperatorTenants,
  OPERATOR_TENANTS_QUERY_KEY,
} from "@/features/operator/hooks/useOperatorTenants";
import { StatusPill, getStatusLabel } from "./StatusPill";
import { ImpersonationConfirmModal } from "./ImpersonationConfirmModal";
import type { components } from "@pilot/shared-types";

type OperatorTenantSummary = components["schemas"]["OperatorTenantSummary"];

interface TenantSelectorProps {
  platformRoleCode: string;
}

// Roles that can impersonate (impersonate_tenant === true)
const IMPERSONATE_ROLES = ["owner", "support"];

export function TenantSelector({ platformRoleCode }: TenantSelectorProps) {
  const queryClient = useQueryClient();
  const { data, isPending, isError } = useOperatorTenants();
  const { addNotification } = useNotificationQueue();

  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTenant, setSelectedTenant] =
    useState<OperatorTenantSummary | null>(null);

  const triggerRef = useRef<HTMLButtonElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  const canImpersonate = IMPERSONATE_ROLES.includes(platformRoleCode);

  // Focus the search input when the panel opens
  useEffect(() => {
    if (isOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsOpen(false);
        triggerRef.current?.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen]);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        triggerRef.current?.contains(target) ||
        listRef.current?.contains(target) ||
        searchInputRef.current?.contains(target)
      ) {
        return;
      }
      // Check if click is inside the panel container
      const panel = document.querySelector("[data-tenant-selector-panel]");
      if (panel && panel.contains(target)) return;
      setIsOpen(false);
    };
    window.addEventListener("mousedown", handleClickOutside);
    return () => window.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  // Client-side filtering (§16.6 — optimistic, no refetch)
  const tenants = data?.tenants ?? [];
  const filteredTenants = searchQuery.trim()
    ? tenants.filter((t) =>
        t.name.toLowerCase().includes(searchQuery.toLowerCase().trim()),
      )
    : tenants;

  const handleTriggerClick = () => {
    setIsOpen((prev) => !prev);
  };

  const handleSelectTenant = (tenant: OperatorTenantSummary) => {
    setIsOpen(false);
    setSearchQuery("");

    if (canImpersonate) {
      setSelectedTenant(tenant);
    } else {
      // accountant — show warning toast, no modal (hide-not-disable at action level)
      addNotification({
        id: `impersonation-blocked-${tenant.tenant_id}`,
        severity: "warning",
        title: "Your role does not permit impersonation.",
      });
    }
  };

  const handleRetry = () => {
    void queryClient.invalidateQueries({
      queryKey: OPERATOR_TENANTS_QUERY_KEY,
    });
  };

  // Keyboard navigation for list rows
  const handleListKeyDown = (e: React.KeyboardEvent<HTMLUListElement>) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const current = document.activeElement as HTMLElement;
      const items =
        listRef.current?.querySelectorAll<HTMLButtonElement>(
          "[data-tenant-row]",
        );
      if (!items || items.length === 0) return;
      const itemsArray = Array.from(items);
      const currentIndex = itemsArray.findIndex((item) => item === current);

      let nextIndex: number;
      if (e.key === "ArrowDown") {
        nextIndex =
          currentIndex < 0 || currentIndex === itemsArray.length - 1
            ? 0
            : currentIndex + 1;
      } else {
        nextIndex =
          currentIndex <= 0 ? itemsArray.length - 1 : currentIndex - 1;
      }
      itemsArray[nextIndex]?.focus();
    }
  };

  return (
    <div className="relative">
      {/* Trigger button */}
      <button
        ref={triggerRef}
        type="button"
        onClick={handleTriggerClick}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label="Select a tenant to view as"
        className="inline-flex items-center gap-2 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-700 hover:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:border-brand-500 transition-colors"
        data-testid="tenant-selector-trigger"
      >
        <BuildingOffice2Icon
          className="w-4 h-4 text-neutral-400"
          aria-hidden="true"
        />
        <span>Select a tenant</span>
        <ChevronDownIcon
          className="w-4 h-4 text-neutral-400"
          aria-hidden="true"
        />
      </button>

      {/* Dropdown panel */}
      {isOpen && (
        <div
          data-tenant-selector-panel
          className="absolute right-0 top-full mt-1 w-96 max-w-[calc(100vw-2rem)] bg-white rounded-lg border border-neutral-200 shadow-lg z-40"
          role="listbox"
        >
          {/* Search input */}
          <div className="relative border-b border-neutral-200">
            <MagnifyingGlassIcon
              className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400"
              aria-hidden="true"
            />
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search tenants…"
              aria-label="Search tenants"
              className="w-full pl-9 pr-8 py-2 text-sm border-0 focus-visible:ring-0 focus:outline-none bg-transparent"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery("");
                  searchInputRef.current?.focus();
                }}
                aria-label="Clear search"
                className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center justify-center w-6 h-6 rounded-md hover:bg-neutral-100 focus-visible:ring-2 focus-visible:ring-brand-500"
              >
                <XMarkIcon
                  className="w-4 h-4 text-neutral-400"
                  aria-hidden="true"
                />
              </button>
            )}
          </div>

          {/* List / states */}
          {isPending ? (
            <div className="py-1">
              {Array.from({ length: 6 }).map((_, i) => (
                <div
                  key={i}
                  className="h-9 bg-neutral-100 animate-pulse rounded mx-1 my-0.5"
                />
              ))}
              <div className="px-3 py-2 border-t border-neutral-100 text-caption text-neutral-500">
                Loading tenants…
              </div>
            </div>
          ) : isError ? (
            <div className="p-3">
              <ErrorState
                type="server"
                title="Could not load tenants"
                description="Check your connection and try again."
                onRetry={handleRetry}
              />
            </div>
          ) : tenants.length === 0 ? (
            <div className="p-3">
              <EmptyState
                type="no-data"
                title="No tenants found"
                description="Tenants will appear here once they sign up."
              />
            </div>
          ) : filteredTenants.length === 0 ? (
            <div className="text-sm text-neutral-500 py-6 text-center">
              No tenants match &ldquo;
              <span className="font-medium text-neutral-700">
                {searchQuery}
              </span>
              &rdquo;.
            </div>
          ) : (
            <>
              <ul
                ref={listRef}
                onKeyDown={handleListKeyDown}
                className="max-h-80 overflow-y-auto py-1"
              >
                {filteredTenants.map((tenant) => (
                  <li key={tenant.tenant_id}>
                    <button
                      type="button"
                      data-tenant-row
                      onClick={() => handleSelectTenant(tenant)}
                      aria-label={`${tenant.name}, ${tenant.tier_name ?? "—"}, ${getStatusLabel(tenant.subscription_status)}`}
                      className="flex items-center justify-between gap-3 w-full px-3 py-2 text-sm text-neutral-900 hover:bg-neutral-50 focus-visible:bg-neutral-50 focus-visible:ring-2 focus-visible:ring-brand-500 rounded-md mx-1 text-left"
                      style={{ width: "calc(100% - 0.5rem)" }}
                    >
                      <span className="text-neutral-900 font-medium truncate">
                        {tenant.name}
                      </span>
                      <span className="flex items-center gap-2 shrink-0">
                        <span className="text-caption text-neutral-500">
                          {tenant.tier_name ?? "—"}
                        </span>
                        <StatusPill status={tenant.subscription_status} />
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              <div className="px-3 py-2 border-t border-neutral-100 text-caption text-neutral-500">
                {filteredTenants.length} tenants
              </div>
            </>
          )}
        </div>
      )}

      {/* Impersonation confirm modal */}
      {selectedTenant && canImpersonate && (
        <ImpersonationConfirmModal
          tenant={selectedTenant}
          onClose={() => setSelectedTenant(null)}
        />
      )}
    </div>
  );
}
