/**
 * QuoteCreatePage — full-page quote builder
 *
 * Location: apps/web/src/features/quotes/components/QuoteCreatePage.tsx
 *
 * Route: /quotes/new
 * RBAC: Gated to quotes.create permission (owner, office_staff, operator)
 *
 * Flow:
 *  1. Select customer (searchable dropdown via useCustomers)
 *  2. Select site (dropdown populated from useCustomerSites after customer selected)
 *  3. Optional expiry date
 *  4. Add line items via LineItemEditor (local state, not yet persisted)
 *
 *  "Save Draft":
 *    a. POST /api/v1/quotes/ → quoteId
 *    b. POST /api/v1/quotes/{quoteId}/lines for each line (sequentially)
 *    c. Navigate to /quotes/[quoteId]
 *
 *  "Send":
 *    a. Same save-and-add-lines flow
 *    b. Open SendQuotePreviewModal (always-preview-before-send)
 *    c. On confirm → useGeneratePublicLink fires
 *    d. Navigate to /quotes/[quoteId]
 */

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { RoleGate } from "@pilot/ui/role-gate";
import { useCustomers } from "../../customers/hooks/useCustomers";
import { useCustomerSites } from "../../customers/hooks/useCustomerSites";
import { useCreateQuote } from "../hooks/useCreateQuote";
import { LineItemEditor } from "./LineItemEditor";
import type { LocalLineItem } from "./LineItemEditor";

// ---------------------------------------------------------------------------
// Inner component (gated)
// ---------------------------------------------------------------------------
function QuoteCreatePageContent() {
  const router = useRouter();

  // --- Form state ---
  const [customerSearch, setCustomerSearch] = useState("");
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(
    null,
  );
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<string>("");
  const [lines, setLines] = useState<LocalLineItem[]>([]);

  // --- Save state ---
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // --- Data hooks ---
  const { data: customersData, isLoading: customersLoading } = useCustomers({
    search: customerSearch || undefined,
  });
  const customers = customersData?.items ?? [];

  const { data: sites = [], isLoading: sitesLoading } = useCustomerSites(
    selectedCustomerId ?? undefined,
  );

  // --- Mutation hooks ---
  const createQuoteMutation = useCreateQuote();

  // --- Derived values ---
  const selectedCustomer = customers.find((c) => c.id === selectedCustomerId);
  const selectedSite = sites.find((s) => s.id === selectedSiteId);

  function formatSiteLabel(site: (typeof sites)[number]): string {
    if (site.name) return site.name;
    if (site.address) {
      return [site.address.line1, site.address.city, site.address.state]
        .filter(Boolean)
        .join(", ");
    }
    return site.id.slice(0, 8) + "…";
  }

  // --- Save draft (create quote + add all lines) ---
  async function handleSave(): Promise<string | null> {
    if (!selectedCustomerId || !selectedSiteId) {
      setSaveError("Please select a customer and site.");
      return null;
    }
    // PLP-FIX-2: defensive guard — line types must be loaded before saving.
    // The editor prevents this state; the guard keeps the contract honest.
    if (lines.some((l) => !l.qco_line_type_id)) {
      setSaveError(
        "Line types are still loading — please wait a moment and try again.",
      );
      return null;
    }
    setIsSaving(true);
    setSaveError(null);

    try {
      // 1. Create the quote
      const quoteResp = await createQuoteMutation.mutateAsync({
        customer_id: selectedCustomerId,
        site_id: selectedSiteId,
        currency: "USD",
        expires_at: expiresAt || null,
      });

      const quoteId = quoteResp.id;

      // 2. Add each line item sequentially via apiClient
      if (lines.length > 0) {
        const { apiClient } = await import("@pilot/shared-api");
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i]!;
          await apiClient.post(`/api/v1/quotes/${quoteId}/lines`, {
            position: i + 1,
            qco_line_type_id: line.qco_line_type_id,
            description: line.description.trim() || "(no description)",
            quantity: line.quantity,
            unit_price_cents: line.unit_price_cents,
            customer_visible: true,
          });
        }
      }

      setIsSaving(false);
      return quoteId;
    } catch (err) {
      setIsSaving(false);
      setSaveError(
        err instanceof Error ? err.message : "Failed to save quote.",
      );
      return null;
    }
  }

  async function handleSaveDraft() {
    const quoteId = await handleSave();
    if (quoteId) {
      router.push(`/quotes/${quoteId}`);
    }
  }

  async function handleSend() {
    // Save draft first, then navigate to detail page.
    // The detail page shows QuoteActionBar which reads quote_version_id from the detail
    // endpoint — the correct place to trigger the public-link send flow.
    const quoteId = await handleSave();
    if (quoteId) {
      router.push(`/quotes/${quoteId}`);
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="max-w-4xl mx-auto p-6 pb-24">
      {/* Breadcrumb */}
      <nav className="text-sm text-neutral-500 mb-4">
        <Link href="/quotes" className="hover:text-brand-600">
          Quotes
        </Link>{" "}
        / <span className="text-neutral-900 font-medium">New Quote</span>
      </nav>

      <h1 className="text-2xl font-semibold text-neutral-900 mb-6">
        New Quote
      </h1>

      <div className="space-y-6">
        {/* Customer + Site row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Customer picker */}
          <div className="space-y-1">
            <label
              htmlFor="customer-search"
              className="text-sm font-medium text-neutral-700"
            >
              Customer <span className="text-alert-600">*</span>
            </label>
            <input
              id="customer-search"
              type="text"
              value={customerSearch}
              onChange={(e) => {
                setCustomerSearch(e.target.value);
                // Reset if text cleared
                if (!e.target.value) setSelectedCustomerId(null);
              }}
              placeholder="Search customer name…"
              className="w-full border border-neutral-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-400"
            />
            {customersLoading && (
              <p className="text-xs text-neutral-400">Loading…</p>
            )}
            {!customersLoading &&
              customerSearch.length > 0 &&
              !selectedCustomerId && (
                <ul className="mt-1 bg-white border border-neutral-200 rounded-md shadow-lg max-h-40 overflow-y-auto z-10 relative">
                  {customers.length === 0 ? (
                    <li className="px-3 py-2 text-sm text-neutral-400">
                      No customers found
                    </li>
                  ) : (
                    customers.map((c) => (
                      <li key={c.id}>
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedCustomerId(c.id);
                            setCustomerSearch(c.display_name);
                            setSelectedSiteId(null);
                          }}
                          className="w-full text-left px-3 py-2 text-sm hover:bg-brand-50 text-neutral-700"
                        >
                          {c.display_name}
                          {c.email && (
                            <span className="text-neutral-400 ml-1 text-xs">
                              {c.email}
                            </span>
                          )}
                        </button>
                      </li>
                    ))
                  )}
                </ul>
              )}
            {selectedCustomer && (
              <p className="text-xs text-margin-600">
                ✓ {selectedCustomer.display_name} selected
              </p>
            )}
          </div>

          {/* Site picker */}
          <div className="space-y-1">
            <label
              htmlFor="site-select"
              className="text-sm font-medium text-neutral-700"
            >
              Site <span className="text-alert-600">*</span>
            </label>
            <select
              id="site-select"
              value={selectedSiteId ?? ""}
              onChange={(e) => setSelectedSiteId(e.target.value || null)}
              disabled={!selectedCustomerId}
              className="w-full border border-neutral-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-400 disabled:bg-neutral-50 disabled:text-neutral-400"
            >
              <option value="">
                {!selectedCustomerId
                  ? "— select a customer first —"
                  : sitesLoading
                    ? "Loading sites…"
                    : sites.length === 0
                      ? "— no sites found —"
                      : "— select a site —"}
              </option>
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {formatSiteLabel(s)}
                </option>
              ))}
            </select>
            {selectedSite && (
              <p className="text-xs text-margin-600">
                ✓ {formatSiteLabel(selectedSite)} selected
              </p>
            )}
          </div>
        </div>

        {/* Expiry date */}
        <div className="w-full md:w-64 space-y-1">
          <label
            htmlFor="expires-at"
            className="text-sm font-medium text-neutral-700"
          >
            Expiry Date{" "}
            <span className="text-neutral-400 font-normal">(optional)</span>
          </label>
          <input
            id="expires-at"
            type="date"
            value={expiresAt}
            onChange={(e) => setExpiresAt(e.target.value)}
            min={new Date().toISOString().split("T")[0]}
            className="w-full border border-neutral-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-brand-400"
          />
        </div>

        {/* Line items */}
        <div className="space-y-2">
          <h2 className="text-base font-semibold text-neutral-800">
            Line Items
          </h2>
          <LineItemEditor lines={lines} onLinesChange={setLines} />
        </div>

        {/* Error */}
        {saveError && (
          <div className="text-sm text-alert-700 bg-alert-50 border border-alert-200 rounded px-3 py-2">
            {saveError}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-neutral-100">
          <Link
            href="/quotes"
            className="px-4 py-2 text-sm font-medium text-neutral-700 border border-neutral-200 rounded-md hover:bg-neutral-50 transition-colors"
          >
            Cancel
          </Link>
          <button
            type="button"
            onClick={() => void handleSaveDraft()}
            disabled={isSaving || !selectedCustomerId || !selectedSiteId}
            className="px-4 py-2 text-sm font-medium text-brand-700 border border-brand-200 bg-brand-50 rounded-md hover:bg-brand-100 transition-colors disabled:opacity-50"
          >
            {isSaving ? "Saving…" : "Save Draft"}
          </button>
          <button
            type="button"
            onClick={() => void handleSend()}
            disabled={isSaving || !selectedCustomerId || !selectedSiteId}
            className="px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 transition-colors disabled:opacity-50"
          >
            {isSaving ? "Saving…" : "Send"}
          </button>
        </div>
      </div>

      {/*
       * Send flow: on create, we navigate to quote detail where QuoteActionBar
       * renders with the correct quote_version_id from the detail endpoint.
       * The always-preview-before-send modal fires from there.
       */}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Exported page (with RoleGate wrapper)
// ---------------------------------------------------------------------------
export function QuoteCreatePage() {
  return (
    <RoleGate permission="quotes.create">
      <QuoteCreatePageContent />
    </RoleGate>
  );
}
