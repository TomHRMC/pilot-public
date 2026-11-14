/**
 * CustomerOverviewTab — customer detail overview with inline edit
 *
 * Location: apps/web/src/features/customers/components/CustomerOverviewTab.tsx
 *
 * View mode: shows all CustomerResponse fields.
 * Edit mode: toggled by "Edit" button (RoleGate: customers.edit).
 *            Renders CustomerForm pre-filled; on submit calls useUpdateCustomer.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCustomer } from "../hooks/useCustomer";
import { useUpdateCustomer } from "../hooks/useUpdateCustomer";
import { CustomerForm } from "./CustomerForm";
import type { CustomerFormValues } from "./CustomerForm";
import { LoadingState, ErrorState } from "@pilot/ui/states";
import { RoleGate } from "@pilot/ui/role-gate";
import { DeleteCustomerModal } from "./DeleteCustomerModal";

interface CustomerOverviewTabProps {
  customerId: string;
}

function formatPhone(phone: string | null): string | null {
  if (!phone) return null;
  // Basic format: 5551234567 → (555) 123-4567
  const digits = phone.replace(/\D/g, "");
  if (digits.length === 10) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }
  return phone;
}

const FIELD_LABEL =
  "text-xs font-medium text-neutral-500 uppercase tracking-wide";
const FIELD_VALUE = "mt-1 text-sm text-neutral-900";

export function CustomerOverviewTab({ customerId }: CustomerOverviewTabProps) {
  const router = useRouter();
  const [isEditing, setIsEditing] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const {
    data: customer,
    isLoading,
    isError,
    refetch,
  } = useCustomer(customerId);
  const updateCustomer = useUpdateCustomer(customerId);

  if (isLoading) {
    return <LoadingState type="inline" label="Loading customer..." />;
  }

  if (isError || !customer) {
    return (
      <ErrorState
        type="server"
        title="Could not load customer"
        description="Check your connection and try again."
        onRetry={() => void refetch()}
      />
    );
  }

  if (isEditing) {
    const initialValues: CustomerFormValues = {
      type: (customer.type as "person" | "company") ?? "person",
      display_name: customer.display_name,
      first_name: customer.first_name,
      last_name: customer.last_name,
      company_name: customer.company_name,
      email: customer.email,
      mobile_phone: customer.mobile_phone,
    };

    return (
      <div className="p-6 max-w-xl">
        <h2 className="text-base font-semibold text-neutral-900 mb-4">
          Edit Customer
        </h2>
        <CustomerForm
          initialValues={initialValues}
          onSubmit={(values) => {
            updateCustomer.mutate(values, {
              onSuccess: () => setIsEditing(false),
            });
          }}
          onCancel={() => setIsEditing(false)}
          isSubmitting={updateCustomer.isPending}
          submitLabel="Save Changes"
        />
      </div>
    );
  }

  const smsStatus = customer.sms_opted_out
    ? { label: "Opted out", className: "bg-alert-100 text-alert-700" }
    : customer.sms_opt_in_consent
      ? { label: "Opted in", className: "bg-success-100 text-success-700" }
      : { label: "Unknown", className: "bg-neutral-100 text-neutral-600" };

  return (
    <div className="p-6">
      {/* FE-B24: Delete Customer Modal */}
      <DeleteCustomerModal
        customerId={customerId}
        customerName={customer.display_name}
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        onSuccess={() => {
          router.push("/customers");
        }}
      />

      {/* Action buttons */}
      <div className="flex justify-end gap-2 mb-4">
        <RoleGate permission="customers.edit">
          <button
            onClick={() => setIsEditing(true)}
            className="px-3 py-1.5 text-sm font-medium text-brand-600 border border-brand-200 rounded-md hover:bg-brand-50 transition-colors"
            data-testid="customer-edit-btn"
          >
            Edit Customer
          </button>
        </RoleGate>
        <RoleGate permission="customers.delete">
          <button
            onClick={() => setDeleteOpen(true)}
            className="px-3 py-1.5 text-sm font-medium text-white bg-fault-600 border border-fault-600 rounded-md hover:bg-fault-700 transition-colors"
            data-testid="delete-customer-btn"
          >
            Delete Customer
          </button>
        </RoleGate>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
        {/* Type */}
        <div>
          <dt className={FIELD_LABEL}>Type</dt>
          <dd className={FIELD_VALUE}>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-neutral-100 text-neutral-700 capitalize">
              {customer.type}
            </span>
          </dd>
        </div>

        {/* Display Name */}
        <div>
          <dt className={FIELD_LABEL}>Display Name</dt>
          <dd className={FIELD_VALUE}>{customer.display_name}</dd>
        </div>

        {/* Person: First + Last Name */}
        {customer.type === "person" && (
          <>
            {customer.first_name && (
              <div>
                <dt className={FIELD_LABEL}>First Name</dt>
                <dd className={FIELD_VALUE}>{customer.first_name}</dd>
              </div>
            )}
            {customer.last_name && (
              <div>
                <dt className={FIELD_LABEL}>Last Name</dt>
                <dd className={FIELD_VALUE}>{customer.last_name}</dd>
              </div>
            )}
          </>
        )}

        {/* Company: Company Name */}
        {customer.type === "company" && customer.company_name && (
          <div>
            <dt className={FIELD_LABEL}>Company Name</dt>
            <dd className={FIELD_VALUE}>{customer.company_name}</dd>
          </div>
        )}

        {/* Email */}
        <div>
          <dt className={FIELD_LABEL}>Email</dt>
          <dd className={FIELD_VALUE}>
            {customer.email ? (
              <a
                href={`mailto:${customer.email}`}
                className="text-brand-600 hover:underline"
              >
                {customer.email}
              </a>
            ) : (
              <span className="text-neutral-400">—</span>
            )}
          </dd>
        </div>

        {/* Mobile Phone */}
        <div>
          <dt className={FIELD_LABEL}>Mobile Phone</dt>
          <dd className={FIELD_VALUE}>
            {customer.mobile_phone ? (
              formatPhone(customer.mobile_phone)
            ) : (
              <span className="text-neutral-400">—</span>
            )}
          </dd>
        </div>

        {/* SMS Consent */}
        <div>
          <dt className={FIELD_LABEL}>SMS Status</dt>
          <dd className={`mt-1`}>
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${smsStatus.className}`}
            >
              {smsStatus.label}
            </span>
            {customer.sms_opted_out && customer.sms_opt_out_at && (
              <span className="ml-2 text-xs text-neutral-400">
                (opted out{" "}
                {new Date(customer.sms_opt_out_at).toLocaleDateString()})
              </span>
            )}
          </dd>
        </div>

        {/* Active status */}
        <div>
          <dt className={FIELD_LABEL}>Status</dt>
          <dd className={FIELD_VALUE}>
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                customer.is_active
                  ? "bg-success-100 text-success-700"
                  : "bg-neutral-100 text-neutral-500"
              }`}
            >
              {customer.is_active ? "Active" : "Inactive"}
            </span>
          </dd>
        </div>
      </div>
    </div>
  );
}
