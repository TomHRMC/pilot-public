/**
 * InviteMemberDialog — TEAM-INVITE-1
 *
 * Location: apps/web/src/features/settings/components/InviteMemberDialog.tsx
 *
 * Replaces the P0 "coming soon" placeholder InviteDialog. Production-grade
 * modal with email + role select, Zod v4 validation via React Hook Form,
 * Idempotency-Key on submit, and 409 state handling:
 *  - invite_pending_exists → offer Resend
 *  - invite_user_exists → explainer (contact support)
 *
 * WCAG 2.2 AA: role="dialog", aria-modal, focus-trap, return-focus,
 * visible labels, ≥44px primary action, ESC + backdrop close.
 */

"use client";

import React, { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  useCreateInvite,
  type CreateInviteError,
} from "../hooks/useCreateInvite";
import { useResendInvite } from "../hooks/useResendInvite";

const ROLE_OPTIONS = [
  {
    value: "owner",
    label: "Owner",
    description: "Full access including billing & team management",
  },
  {
    value: "technician",
    label: "Field Technician",
    description: "Jobs, time entries, expenses, voice quoting",
  },
  {
    value: "office_staff",
    label: "Office Staff",
    description: "Customers, quotes, scheduling, invoices",
  },
  {
    value: "accountant",
    label: "Accountant",
    description: "Read-only books & reports",
  },
] as const;

const inviteSchema = z.object({
  email: z.email({ error: "Enter a valid email address" }),
  role_code: z.string().min(1, "Select a role"),
});

type InviteFormValues = z.infer<typeof inviteSchema>;

interface InviteMemberDialogProps {
  onClose: () => void;
}

export function InviteMemberDialog({ onClose }: InviteMemberDialogProps) {
  const createInvite = useCreateInvite();
  const resendInvite = useResendInvite();
  const [errorState, setErrorState] = useState<CreateInviteError | null>(null);
  const [success, setSuccess] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<InviteFormValues>({
    resolver: zodResolver(inviteSchema),
    defaultValues: {
      email: "",
      role_code: "technician",
    },
  });

  // Focus trap: focus the dialog on open, return focus to trigger on close
  useEffect(() => {
    closeButtonRef.current?.focus();
    const dialogEl = dialogRef.current;
    if (!dialogEl) return;

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key === "Tab") {
        const focusable = dialogEl!.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
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
  }, [onClose]);

  async function onSubmit(values: InviteFormValues) {
    setErrorState(null);
    try {
      await createInvite.mutateAsync(values);
      setSuccess(true);
      reset();
    } catch (err) {
      setErrorState(err as CreateInviteError);
    }
  }

  function handleBackdropClick(e: React.MouseEvent) {
    if (e.target === e.currentTarget) {
      onClose();
    }
  }

  async function handleResendExisting() {
    if (!errorState?.invite_id) return;
    try {
      await resendInvite.mutateAsync(errorState.invite_id);
      setSuccess(true);
      setErrorState(null);
      reset();
    } catch {
      // Resend failed — keep the error state visible
    }
  }

  const isPendingExists =
    errorState?.type ===
    "https://errors.pilotfortrades.com/invite_pending_exists";
  const isUserExists =
    errorState?.type === "https://errors.pilotfortrades.com/invite_user_exists";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={handleBackdropClick}
      data-testid="invite-dialog-backdrop"
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="invite-dialog-title"
        aria-describedby="invite-dialog-desc"
        className="bg-white rounded-lg p-6 max-w-md w-full shadow-xl"
        data-testid="invite-dialog"
      >
        <div className="flex items-center justify-between mb-4">
          <h2
            id="invite-dialog-title"
            className="text-lg font-semibold text-neutral-900"
          >
            Invite Team Member
          </h2>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            aria-label="Close invite dialog"
            className="rounded-md p-2 text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
            data-testid="invite-dialog-close"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        <p id="invite-dialog-desc" className="text-sm text-neutral-600 mb-4">
          Send an invite email. The recipient creates their own account and
          joins your team with the role you choose.
        </p>

        {success ? (
          <div className="text-center py-4">
            <div className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-success-100">
              <svg
                className="h-6 w-6 text-success-600"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M4.5 12.75l6 6 9-13.5"
                />
              </svg>
            </div>
            <p className="text-sm font-medium text-neutral-900">
              Invite sent successfully
            </p>
            <p className="mt-1 text-xs text-neutral-500">
              The invite appears in the pending list below.
            </p>
            <button
              onClick={onClose}
              className="mt-4 rounded-md bg-brand-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500"
              data-testid="invite-dialog-done"
            >
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} noValidate>
            {/* Email field */}
            <div className="mb-4">
              <label
                htmlFor="invite-email"
                className="block text-sm font-medium text-neutral-700 mb-1"
              >
                Email
              </label>
              <input
                id="invite-email"
                type="email"
                autoComplete="email"
                {...register("email")}
                aria-invalid={!!errors.email}
                aria-describedby={
                  errors.email ? "invite-email-error" : undefined
                }
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
                placeholder="teammate@example.com"
                data-testid="invite-email-input"
              />
              {errors.email && (
                <p
                  id="invite-email-error"
                  className="mt-1 text-xs text-fault-600"
                  data-testid="invite-email-error"
                >
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* Role select */}
            <div className="mb-4">
              <label
                htmlFor="invite-role"
                className="block text-sm font-medium text-neutral-700 mb-1"
              >
                Role
              </label>
              <select
                id="invite-role"
                {...register("role_code")}
                className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:outline-none focus:ring-2 focus:ring-brand-500"
                data-testid="invite-role-select"
              >
                {ROLE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label} — {opt.description}
                  </option>
                ))}
              </select>
            </div>

            {/* 409: invite_pending_exists → offer Resend */}
            {isPendingExists && (
              <div
                className="mb-4 rounded-md border border-alert-200 bg-alert-50 p-3"
                data-testid="invite-pending-exists"
              >
                <p className="text-sm text-alert-800">
                  An invite is already pending for this email.
                </p>
                <button
                  type="button"
                  onClick={handleResendExisting}
                  disabled={resendInvite.isPending}
                  className="mt-2 rounded-md bg-alert-600 px-4 py-2 text-sm font-medium text-white hover:bg-alert-700 focus:outline-none focus:ring-2 focus:ring-alert-500 disabled:opacity-50"
                  data-testid="invite-resend-existing"
                >
                  {resendInvite.isPending ? "Resending…" : "Resend invite"}
                </button>
              </div>
            )}

            {/* 409: invite_user_exists → explainer */}
            {isUserExists && (
              <div
                className="mb-4 rounded-md border border-neutral-200 bg-neutral-50 p-3"
                data-testid="invite-user-exists"
              >
                <p className="text-sm text-neutral-700">
                  This person already has a Pilot account. Contact Pilot support
                  for multi-business access.
                </p>
              </div>
            )}

            {/* Generic error */}
            {errorState && !isPendingExists && !isUserExists && (
              <div
                className="mb-4 rounded-md border border-fault-200 bg-fault-50 p-3"
                data-testid="invite-generic-error"
              >
                <p className="text-sm text-fault-700">
                  {/* PLP-FIX-7: String-guard — never render a non-string
                      detail (objects are not valid React children). */}
                  {typeof errorState.detail === "string" &&
                  errorState.detail.length > 0
                    ? errorState.detail
                    : "Something went wrong. Please try again."}
                </p>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="rounded-md border border-neutral-300 px-4 py-2.5 text-sm font-medium text-neutral-700 hover:bg-neutral-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={createInvite.isPending}
                className="rounded-md bg-brand-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
                data-testid="invite-submit"
              >
                {createInvite.isPending ? "Sending…" : "Send invite"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
