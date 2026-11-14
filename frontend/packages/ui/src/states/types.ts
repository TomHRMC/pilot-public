/**
 * States Catalog — Shared TypeScript Interfaces
 *
 * Location: packages/ui/src/states/types.ts
 *
 * Discriminated-union types for EmptyState, LoadingState, ErrorState,
 * and FirstTimeUserState. Shared across web and mobile variants.
 * Consumed by every surface batch (FE-B2 onward).
 */

import type React from "react";

// ── Empty States ──────────────────────────────────────────────────────────────

export type EmptyStateType =
  | "no-data" // Entity list is empty (no records exist yet)
  | "no-results" // Search/filter returned zero results
  | "not-yet-set-up" // Feature requires setup before use (e.g., QuickBooks not connected)
  | "permission-denied" // Role gate — user cannot view this content
  | "filtered-empty"; // Date range / filter selection returns nothing

export interface EmptyStateProps {
  type: EmptyStateType;
  /** Override the default heading for this type */
  title?: string;
  /** Override the default body copy for this type */
  description?: string;
  /** Primary CTA label (e.g., "Create your first quote") */
  ctaLabel?: string;
  /** Primary CTA handler */
  onCta?: () => void;
  /** Secondary CTA label (e.g., "Learn more") */
  secondaryCtaLabel?: string;
  onSecondaryCta?: () => void;
  /** Illustration key; resolves to platform-appropriate art */
  illustration?: EmptyStateIllustration;
  testID?: string; // Mobile e2e targeting
}

export type EmptyStateIllustration =
  | "empty-clipboard" // no-data, no-results
  | "lock" // permission-denied
  | "wrench" // not-yet-set-up
  | "filter" // filtered-empty
  | "none"; // No illustration (compact layouts)

/** Default content per EmptyStateType */
export const EMPTY_STATE_DEFAULTS: Record<
  EmptyStateType,
  { title: string; description: string; illustration: EmptyStateIllustration }
> = {
  "no-data": {
    title: "Nothing here yet",
    description: "Create your first record to get started.",
    illustration: "empty-clipboard",
  },
  "no-results": {
    title: "No results found",
    description: "Try adjusting your search or filter criteria.",
    illustration: "empty-clipboard",
  },
  "not-yet-set-up": {
    title: "Not yet set up",
    description: "Complete setup to unlock this feature.",
    illustration: "wrench",
  },
  "permission-denied": {
    title: "Access restricted",
    description: "You don't have permission to view this content.",
    illustration: "lock",
  },
  "filtered-empty": {
    title: "No results for this filter",
    description: "Clear or adjust your filters to see more results.",
    illustration: "filter",
  },
};

// ── Loading States ────────────────────────────────────────────────────────────

export type LoadingStateType =
  | "full-page" // Full-viewport skeleton screen for initial page loads
  | "inline" // Spinner for embedded async areas (form submits, button loads)
  | "optimistic"; // Subtle pulse on an entity that has a pending operation

export interface LoadingStateProps {
  type: LoadingStateType;
  /** For 'full-page': number of skeleton rows to render (default: 4) */
  skeletonRows?: number;
  /** For 'inline': label for screen readers (default: "Loading…") */
  label?: string;
  /** For 'optimistic': applies pulse animation to children */
  children?: React.ReactNode;
  testID?: string;
}

// ── Error States ──────────────────────────────────────────────────────────────

export type ErrorStateType =
  | "network" // No internet / connection timeout
  | "server" // Backend 5xx error
  | "validation" // Form validation failure (rendered inline in forms, not as full-page)
  | "permission"; // 403 / unauthorized — distinct from permission-denied empty state

export interface ErrorStateProps {
  type: ErrorStateType;
  /** Override default heading for this error type */
  title?: string;
  /** Override default body copy */
  description?: string;
  /** Show a retry CTA (applicable for network, server errors) */
  onRetry?: () => void;
  /** For 'validation': field-level error map — renders inline under relevant inputs */
  fieldErrors?: Record<string, string>;
  /** Contact-support CTA for persistent server errors */
  onContactSupport?: () => void;
  testID?: string;
}

/** Default content per ErrorStateType */
export const ERROR_STATE_DEFAULTS: Record<
  ErrorStateType,
  { title: string; description: string }
> = {
  network: {
    title: "Connection error",
    description:
      "Unable to reach the server. Check your internet connection and try again.",
  },
  server: {
    title: "Server error",
    description: "Something went wrong on our end. Please try again shortly.",
  },
  validation: {
    title: "Please fix the errors below",
    description: "Correct the highlighted fields before submitting.",
  },
  permission: {
    title: "Access denied",
    description: "You don't have permission to perform this action.",
  },
};

// ── First-Time-User States ────────────────────────────────────────────────────

export type FTUSurface =
  | "dashboard" // Owner's first login: guide to adding tech, sending first quote
  | "quotes" // No quotes created yet: guide to voice quote creation
  | "schedule" // No jobs scheduled: guide to dispatch board
  | "customers" // No customers added: guide to customer management
  | "invoices" // No invoices sent: guide to invoice workflow
  | "reports" // No data for reports: guide to data-generating actions
  | "comms" // No messages sent: guide to customer communications
  | "settings"; // Settings not yet configured: guide to key settings

export interface FirstTimeUserStateProps {
  type: FTUSurface;
  /**
   * Override the default headline for this FTU surface.
   * Default copy is baked into the component per Pass 4 Tier 3 #9 spec.
   */
  headingText?: string;
  /** Override the default body copy */
  bodyText?: string;
  /** Override the primary CTA label */
  ctaLabel?: string;
  /** CTA handler — typically navigates to the first onboarding action */
  onCta?: () => void;
  /** Optional secondary CTA (e.g., "Watch a 2-minute demo") */
  secondaryCtaLabel?: string;
  onSecondaryCta?: () => void;
  testID?: string;
}

/**
 * Default FTU content map — used when props are not overridden.
 * Copy sourced from Pass 4 Tier 3 #9 spec; parameterized here for
 * discoverability and future copy iteration without code changes.
 */
export const FTU_DEFAULTS: Record<
  FTUSurface,
  { heading: string; body: string; ctaLabel: string; ctaPath: string }
> = {
  dashboard: {
    heading: "Welcome to Pilot",
    body: "Start by adding your first technician or sending a voice quote.",
    ctaLabel: "Add a technician",
    ctaPath: "/settings/team",
  },
  quotes: {
    heading: "No quotes yet",
    body: "Use the Pilot mobile app to create your first quote by voice, hands-free.",
    ctaLabel: "Learn how voice quotes work",
    ctaPath: "/help?context=voice-quotes",
  },
  schedule: {
    heading: "Your dispatch board is empty",
    body: "Schedule your first job by dragging a tech to a time slot.",
    ctaLabel: "View the dispatch board",
    ctaPath: "/schedule",
  },
  customers: {
    heading: "No customers yet",
    body: "Add your first customer to start sending quotes and tracking jobs.",
    ctaLabel: "Add a customer",
    ctaPath: "/customers/new",
  },
  invoices: {
    heading: "No invoices sent",
    body: "Invoices are generated automatically when a quote is approved and work is complete.",
    ctaLabel: "View quotes",
    ctaPath: "/quotes",
  },
  reports: {
    heading: "Not enough data yet",
    body: "Complete your first job to start seeing profitability and efficiency reports.",
    ctaLabel: "Go to the dispatch board",
    ctaPath: "/schedule",
  },
  comms: {
    heading: "No messages sent",
    body: "Send your first customer communication — on the way, running late, job complete.",
    ctaLabel: "Send a message",
    ctaPath: "/comms/new",
  },
  settings: {
    heading: "Configure your account",
    body: "Set your company name, logo, and notification preferences to personalize Pilot.",
    ctaLabel: "Open settings",
    ctaPath: "/settings",
  },
};

/** FTU surfaces that render on mobile — all others return null */
export const MOBILE_SUPPORTED_FTU_TYPES: FTUSurface[] = [
  "dashboard",
  "schedule",
  "customers",
];
