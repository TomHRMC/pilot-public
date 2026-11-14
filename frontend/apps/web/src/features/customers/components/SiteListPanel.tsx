/**
 * SiteListPanel — list of sites for a customer with add/edit
 *
 * Location: apps/web/src/features/customers/components/SiteListPanel.tsx
 *
 * Shows all sites for the given customerId.
 * "Add Site" opens SiteForm modal (RoleGate: sites.create).
 * "Edit" per site opens pre-filled SiteForm (RoleGate: sites.edit).
 */

"use client";

import { useState } from "react";
import { useCustomerSites } from "../hooks/useCustomerSites";
import type { SiteResponse } from "../hooks/useCustomerSites";
import { useCreateSite } from "../hooks/useCreateSite";
import { useUpdateSite } from "../hooks/useUpdateSite";
import { useCustomer } from "../hooks/useCustomer";
import { SiteForm } from "./SiteForm";
import type { SiteCreateRequest } from "../hooks/useCreateSite";
import { LoadingState, ErrorState, EmptyState } from "@pilot/ui/states";
import { RoleGate } from "@pilot/ui/role-gate";

interface SiteListPanelProps {
  customerId: string;
}

function formatAddress(address: SiteResponse["address"]): string | null {
  if (!address) return null;
  const parts = [
    address.line1,
    address.city,
    address.state,
    address.postal_code,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(", ") : null;
}

export function SiteListPanel({ customerId }: SiteListPanelProps) {
  const [showAdd, setShowAdd] = useState(false);
  const [editingSite, setEditingSite] = useState<SiteResponse | null>(null);

  const { data: customer } = useCustomer(customerId);
  const customerType = customer?.type as "person" | "company" | undefined;

  const {
    data: sites,
    isLoading,
    isError,
    refetch,
  } = useCustomerSites(customerId);
  const createSite = useCreateSite(customerId);
  const updateSite = useUpdateSite(editingSite?.id ?? "", customerId);

  if (isLoading) {
    return <LoadingState type="inline" label="Loading sites..." />;
  }

  if (isError) {
    return (
      <ErrorState
        type="server"
        title="Could not load sites"
        description="Check your connection and try again."
        onRetry={() => void refetch()}
      />
    );
  }

  function handleCreate(data: SiteCreateRequest) {
    createSite.mutate(data, {
      onSuccess: () => setShowAdd(false),
    });
  }

  function handleUpdate(data: SiteCreateRequest) {
    if (!editingSite) return;
    updateSite.mutate(data, {
      onSuccess: () => setEditingSite(null),
    });
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-neutral-900">Sites</h2>
        <RoleGate permission="sites.create">
          <button
            onClick={() => setShowAdd(true)}
            className="px-3 py-1.5 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors"
            data-testid="add-site-btn"
          >
            + Add Site
          </button>
        </RoleGate>
      </div>

      {/* Add Site Modal */}
      {showAdd && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="add-site-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center"
        >
          <div
            className="absolute inset-0 bg-neutral-900 opacity-40"
            onClick={() => setShowAdd(false)}
            aria-hidden="true"
          />
          <div className="relative bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-screen overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3
                  id="add-site-modal-title"
                  className="text-lg font-semibold text-neutral-900"
                >
                  Add Site
                </h3>
                <button
                  type="button"
                  onClick={() => setShowAdd(false)}
                  className="text-neutral-400 hover:text-neutral-600"
                  aria-label="Close modal"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
              <SiteForm
                customerId={customerId}
                customerType={customerType}
                onSubmit={handleCreate}
                onCancel={() => setShowAdd(false)}
                isSubmitting={createSite.isPending}
                submitLabel="Add Site"
              />
            </div>
          </div>
        </div>
      )}

      {/* Edit Site Modal */}
      {editingSite && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="edit-site-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center"
        >
          <div
            className="absolute inset-0 bg-neutral-900 opacity-40"
            onClick={() => setEditingSite(null)}
            aria-hidden="true"
          />
          <div className="relative bg-white rounded-lg shadow-xl w-full max-w-lg mx-4 max-h-screen overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3
                  id="edit-site-modal-title"
                  className="text-lg font-semibold text-neutral-900"
                >
                  Edit Site
                </h3>
                <button
                  type="button"
                  onClick={() => setEditingSite(null)}
                  className="text-neutral-400 hover:text-neutral-600"
                  aria-label="Close modal"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
              <SiteForm
                customerId={customerId}
                customerType={customerType}
                initialValues={{
                  name: editingSite.name ?? "",
                  notes: editingSite.notes ?? "",
                  jurisdiction_code: editingSite.jurisdiction_code ?? "",
                  site_type: editingSite.site_type ?? undefined,
                  showAddress: !!editingSite.address,
                  address: {
                    line1: editingSite.address?.line1 ?? "",
                    line2: editingSite.address?.line2 ?? "",
                    city: editingSite.address?.city ?? "",
                    state: editingSite.address?.state ?? "",
                    postal_code: editingSite.address?.postal_code ?? "",
                    country: editingSite.address?.country ?? "US",
                  },
                }}
                onSubmit={handleUpdate}
                onCancel={() => setEditingSite(null)}
                isSubmitting={updateSite.isPending}
                submitLabel="Save Changes"
              />
            </div>
          </div>
        </div>
      )}

      {/* Site list */}
      {!sites || sites.length === 0 ? (
        <EmptyState
          type="no-data"
          title="No sites yet"
          description="Sites are physical locations for this customer. Add one to get started."
        />
      ) : (
        <div className="space-y-3">
          {sites.map((site) => {
            const address = formatAddress(site.address);
            return (
              <div
                key={site.id}
                className="rounded-md border border-neutral-200 bg-white p-4"
                data-testid={`site-card-${site.id}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-semibold text-neutral-900 truncate">
                        {site.name ?? "Unnamed Site"}
                      </h3>
                      {site.site_type && (
                        <span
                          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-700 capitalize"
                          data-testid={`site-type-chip-${site.id}`}
                        >
                          {site.site_type}
                        </span>
                      )}
                    </div>
                    {address && (
                      <p className="mt-0.5 text-xs text-neutral-500 truncate">
                        {address}
                      </p>
                    )}
                    {site.notes && (
                      <p className="mt-1 text-xs text-neutral-600 line-clamp-2">
                        {site.notes}
                      </p>
                    )}
                    {site.jurisdiction_code && (
                      <p className="mt-1 text-xs text-neutral-400">
                        Jurisdiction: {site.jurisdiction_code}
                      </p>
                    )}
                  </div>
                  <div className="ml-3 flex-shrink-0">
                    <RoleGate permission="sites.edit">
                      <button
                        onClick={() => setEditingSite(site)}
                        className="px-2.5 py-1 text-xs font-medium text-neutral-600 border border-neutral-200 rounded hover:bg-neutral-50 transition-colors"
                        data-testid={`edit-site-btn-${site.id}`}
                      >
                        Edit
                      </button>
                    </RoleGate>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
