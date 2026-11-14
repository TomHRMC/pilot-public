"use client";

/**
 * @pilot/ui — Public API barrel
 *
 * Location: packages/ui/src/index.ts
 *
 * Every shared component exported here. A component does not exist until
 * it appears in this barrel export.
 *
 * Import from category subpaths for tree-shaking:
 *   import { EmptyState } from '@pilot/ui/states'
 *   import { useNotificationQueue } from '@pilot/ui/notification-banner'
 *
 * Or from the root for convenience:
 *   import { EmptyState, useNotificationQueue } from '@pilot/ui'
 */

// ── FE-B0 Exports ─────────────────────────────────────────────────────────────

export { AuthProvider, AuthContext, RequireAuth } from "./auth";
export type {
  AuthProviderProps,
  RequireAuthProps,
  AuthContextValue,
  PilotUser,
  PilotRole,
} from "./auth";
export { useAuth } from "./auth";

export { RoleGate, useRequiresPermission, useHasPermission } from "./role-gate";
export type { RoleGateProps } from "./role-gate";
export { hasPermission, ROLE_PERMISSION_MAP } from "./role-gate";
export type { PermissionKey } from "./role-gate";

// ── FE-B1 Exports ─────────────────────────────────────────────────────────────

// States catalog
export {
  EmptyState,
  LoadingState,
  ErrorState,
  FirstTimeUserState,
} from "./states";
export type {
  EmptyStateProps,
  EmptyStateType,
  EmptyStateIllustration,
  LoadingStateProps,
  LoadingStateType,
  ErrorStateProps,
  ErrorStateType,
  FirstTimeUserStateProps,
  FTUSurface,
} from "./states/types";
export {
  FTU_DEFAULTS,
  EMPTY_STATE_DEFAULTS,
  ERROR_STATE_DEFAULTS,
  MOBILE_SUPPORTED_FTU_TYPES,
} from "./states/types";

// Notification Banner
export {
  NotificationBanner,
  NotificationPortal,
  useNotificationQueue,
  NotificationQueueProvider,
} from "./notification-banner";
export type {
  NotificationItem,
  NotificationSeverity,
  NotificationQueueContextValue,
  NotificationBannerWebProps,
  NotificationBannerMobileProps,
  NotificationQueueProviderProps,
} from "./notification-banner/types";
export { AUTO_DISMISS_MS } from "./notification-banner/types";

// In-Flight Sync Indicator (unified FE-B15 — API LOCKED)
export { InFlightSyncIndicator } from "./sync-indicator";
export type {
  InFlightSyncIndicatorProps,
  SyncSurface,
  SyncState,
  PendingItem,
} from "./sync-indicator/types";

// Email Branding Preview (fleshed in FE-B14 — interface LOCKED by FE-B14)
export { EmailBrandingPreview } from "./email-branding-preview";
export type {
  EmailBrandingPreviewProps,
  TenantBranding,
  // FE-B14 additions:
  EmailTemplateId,
} from "./email-branding-preview/types";
export { EMAIL_TEMPLATE_CATEGORIES } from "./email-branding-preview/types";

// MFA Enrollment Wizard — FE-B1 skeleton; fleshed out in FE-B12 (see FE-B12 Exports block below)
// Export consolidated in FE-B12 block to avoid duplicates

// Tier Picker Card (fleshed in FE-B13 — interface FROZEN)
export { TierPickerCard } from "./tier-picker-card";
export type {
  TierPickerCardProps,
  TierPickerCardPropsExtended,
  TierFeature,
  TierName,
} from "./tier-picker-card/types";

// ── FE-B3 Exports ─────────────────────────────────────────────────────────────

// Voice stream hook + types (platform-resolved: mobile default)
export { useVoiceStream, voiceStateTokens } from "./voice";
export type {
  VoiceState,
  VoiceStreamEventType,
  VoiceStreamEvent,
  UseVoiceStreamReturn,
} from "./voice";

// Voice confirm-as-turn UI
export { VoiceConfirmTurn, useVoiceConfirmation } from "./voice-confirm-turn";
export type {
  VoiceConfirmTurnProps,
  PendingConfirmation,
  UseVoiceConfirmationReturn,
} from "./voice-confirm-turn";

// ── FE-B4 Exports ─────────────────────────────────────────────────────────────
// These modules are consumed by FE-B5, FE-B8, FE-B9, FE-B10 and later batches.
// ⚠️ Interfaces locked — coordinate changes with downstream batches.

// Pre-commit 409 staleness retry hook (gates FE-B5/B8/B9/B10)
export { useStalenessRetry, StalenessError } from "./hooks/useStalenessRetry";
export type {
  UseStalenessRetryOptions,
  UseStalenessRetryReturn,
  StalenessConflictPayload,
} from "./hooks/useStalenessRetry";

// SSE channel hook (gates FE-B8/B10/B12)
export { useSseChannel } from "./hooks/useSseChannel";
export type {
  SseMessage,
  UseSseChannelOptions,
  UseSseChannelReturn,
} from "./hooks/useSseChannel";

// Staleness refresh dialog (used internally by useStalenessRetry; exported for custom usage)
export { StalenessRefreshDialog } from "./staleness-refresh-dialog/StalenessRefreshDialog";
export type { StalenessRefreshDialogProps } from "./staleness-refresh-dialog/types";

// Four-class conflict severity tokens (gates FE-B7/B8/B9)
export { CONFLICT_CLASS_TOKENS } from "./conflict-severity/types";
export type {
  DispatchConflictClass,
  FourClassSeverity,
  ConflictVisualTokens,
} from "./conflict-severity/types";

// ── FE-B5 Exports ─────────────────────────────────────────────────────────────
// DiffView is the canonical track-changes diff renderer (§16.2).
// Consumed by FE-B7 (entity), FE-B8 (calendar-event), FE-B9 (qb-entity).
// ⚠️ Interface locked — changes require FE-B7/B8/B9 impact review.

export { DiffView } from "./diff-view";
export type {
  DiffViewProps,
  DiffViewVariant,
  DiffField,
  DiffLineItem,
  QuoteLineDiffViewProps,
  IntegrationDiffViewProps,
  EntityDiffViewProps,
} from "./diff-view/types";
export { normalizeFieldDiffs, buildQuoteLineDiff } from "./diff-view/utils";

export { useApproveWithEdits } from "./hooks/useApproveWithEdits";
export type {
  UseApproveWithEditsOptions,
  UseApproveWithEditsReturn,
  QuotePendingEditCreate,
  QuotePendingEditResponse,
  QuoteApproveRequest,
  QuoteApproveResponse,
} from "./hooks/useApproveWithEdits";

// ── FE-B6 Exports ─────────────────────────────────────────────────────────────
// MessagePreviewModal + usePreviewBeforeSend establish the always-preview-before-send
// pattern (§16.7). Consumed by FE-B10 (SMS reply composer).
// ⚠️ Interfaces locked — changes require FE-B10 impact review.

export { MessagePreviewModal } from "./message-preview";
export type {
  MessagePreviewModalProps,
  MessagePreviewModalOverrideProps,
  FreeFormPreviewData,
} from "./message-preview/types";

export { usePreviewBeforeSend } from "./hooks/usePreviewBeforeSend";
export type {
  UsePreviewBeforeSendReturn,
  UsePreviewBeforeSendOptions,
  PreviewInput,
} from "./hooks/usePreviewBeforeSend";

export { CustomerDisambiguationList } from "./message-preview/CustomerDisambiguationList";
export type { CustomerDisambiguationListProps } from "./message-preview/types";

export { TimeExtractionEditor } from "./message-preview/TimeExtractionEditor";
export type { TimeExtractionEditorProps } from "./message-preview/types";

// ── FE-B7 Exports ─────────────────────────────────────────────────────────────
// PendingBadge + useOptimisticMutation establish optimistic UI with pending badges (§16.8).
// Consumed by FE-B9 (background sync), FE-B12 (account settings async ops).
// ⚠️ Interfaces locked — changes require FE-B9 and FE-B12 impact review.

export { PendingBadge } from "./pending-badge";
export type {
  PendingBadgeProps,
  PendingBadgeVariant,
} from "./pending-badge/types";

export { useOptimisticMutation } from "./hooks/useOptimisticMutation";
export type {
  UseOptimisticMutationOptions,
  UseOptimisticMutationReturn,
} from "./hooks/useOptimisticMutation";

// EscalationStatusRow establishes the mobile-to-web escalation pattern (§16.11).
// Consumed by FE-B9 (full owner escalation flow).
export { EscalationStatusRow } from "./escalation-status";
export type {
  EscalationStatusRowProps,
  EscalationStatus,
} from "./escalation-status/types";

// Additional FE-B6 types needed by app routes
export type {
  CommunicationHistoryItem,
  CommunicationHistoryResponse,
  CommTemplateTypeResponse,
  CommTemplateTypeListResponse,
  CommunicationSendResponse,
  CommunicationPreviewResponse,
  CommunicationPreviewRequest,
  CommunicationSendRequest,
  FreeFormSendResponse,
  EditableVariableResponse,
  CustomerMatch,
  TimeQuickPick,
} from "./message-preview/types";
export { TIME_QUICK_PICKS } from "./message-preview/types";

// ── FE-B8 Exports ─────────────────────────────────────────────────────────────
// IntegrationConflictResolver cluster — bilateral integration conflict resolution (§16.10).
// Established here with integration="calendar"; FE-B9 extends with integration="quickbooks".
// ⚠️ IntegrationConflictResolverProps LOCKED after FE-B8. FE-B9 may only extend via optional additive props.

export {
  IntegrationConflictResolver,
  DeletionConflictView,
  ExpiryCountdownBadge,
  ConflictTypeLabel,
} from "./integration-conflict-resolver";
export type {
  IntegrationConflictResolverProps,
  DeletionConflictViewProps,
  ExpiryCountdownBadgeProps,
  ConflictTypeLabelProps,
  CalendarConflictDetail,
  CalendarApiFieldDiff,
  CalendarResolution,
  CalendarConnectionStatus,
  CalendarSyncStatusRowProps,
  ConflictType,
  // FE-B9 additions — locked for FE-B11/FE-B15/FE-B16
  QbConflictDetail,
  QbFieldDiff,
  FieldIssueDetail,
  FieldIssueDiff,
  PerFieldSelection,
} from "./integration-conflict-resolver";

// CalendarSyncStatusRow — mobile Owner tab calendar sync health row.
// Deep-links to web resolution surface when conflicts exist.
export { CalendarSyncStatusRow } from "./calendar-sync-status";

// FieldIssuesSyncStatusRow — mobile Owner tab field issues health row (FE-B9).
// Mirrors CalendarSyncStatusRow pattern. Locked for FE-B15 (status row refinement).
export { FieldIssuesSyncStatusRow } from "./field-issues-status";
export type { FieldIssuesSyncStatusRowProps } from "./field-issues-status";

// InvoiceFinancialDeltaCallout — QB invoice conflict financial delta summary (FE-B9).
// Injected via renderDomainSpecificFields slot on <IntegrationConflictResolver>.
// Lives in packages/ui for reuse by future financial-stakes integrations (RULE 7).
export { InvoiceFinancialDeltaCallout } from "./invoice-financial-delta";
export type { InvoiceFinancialDeltaCalloutProps } from "./invoice-financial-delta";

// ── FE-B10 Exports ─────────────────────────────────────────────────────────────
// SMS Inbound / Customer Comms Extension (Pass 4 Tier 1.5)
// Canonical types for Phase 2 reuse — do not redefine.

export { useSegmentCount } from "./hooks/useSegmentCount";
export type { SegmentCountResult } from "./hooks/useSegmentCount";

export { SmsQuotaIndicator } from "./sms-quota-indicator";
export type { SmsQuotaIndicatorProps } from "./sms-quota-indicator/types";

export { SmsThreadBubble } from "./sms-thread-bubble";
export type { SmsThreadBubbleProps } from "./sms-thread-bubble/types";

export { SmsOptOutBadge } from "./sms-opt-out-badge";
export type { SmsOptOutBadgeProps } from "./sms-opt-out-badge/types";

// Canonical SMS domain types — locked for Phase 2
export type {
  SmsThread,
  SmsMessage,
  SmsReplyRequest,
  SmsReplyResponse,
  SmsQuotaStatus,
  SmsThreadListItem,
  UnroutedMessage,
  QuotaVisualState,
  VoiceDictationState,
  UseVoiceDictationReturn,
} from "./sms-thread-bubble/types";

export { deriveQuotaState } from "./sms-quota-indicator/utils";

// ── FE-B11 Exports ─────────────────────────────────────────────────────────────
// Settings Foundation — system-default-with-tenant-override pattern (arch doc §16.5).
// Canonical visual treatment: SettingControl (Mockup A), EffectiveSettingDisplay (Mockup C)
// Save behavior: useFormSaveStrategy (Mockup B)
// ⚠️ All interfaces LOCKED after FE-B11 ships.
// FE-B12 may only add OPTIONAL additive props.

export { SettingControl } from "./setting-control";
export type { SettingControlProps } from "./setting-control";

export { EffectiveSettingDisplay } from "./setting-control";
export type { EffectiveSettingDisplayProps } from "./setting-control";

export { RevertToDefaultDialog } from "./setting-control";
export type { RevertToDefaultDialogProps } from "./setting-control";

export { SaveOnGroupCompleteIndicator } from "./setting-control";
export type { SaveOnGroupCompleteIndicatorProps } from "./setting-control";

export { SettingsSidebarSearch } from "./setting-control";
export type { SettingsSidebarSearchProps } from "./setting-control";

export { useFormSaveStrategy } from "./hooks/useFormSaveStrategy";
export type {
  UseFormSaveStrategyOptions,
  UseFormSaveStrategyReturn,
  BlurSaveOptions,
  BlurSaveReturn,
  GroupSaveOptions,
  GroupSaveReturn,
  GroupFieldDef,
  ExplicitSaveOptions,
  ExplicitSaveReturn,
} from "./hooks/useFormSaveStrategy";

// Canonical settings domain types (frontend representation of backend Pydantic schemas)
export type {
  CatalogEntry,
  EffectiveSettingValue,
} from "./setting-control/types";

// ── FE-B12 Exports ─────────────────────────────────────────────────────────────
// Settings Sub-Surfaces: MFA wizard (fleshed out), notification matrix, notification bell
// ⚠️ MFAEnrollmentWizard, NotificationPreferenceMatrix, NotificationCenterBell:
//    INTERFACES LOCKED after FE-B12 ships — FE-B13 embeds all three.

// MFAEnrollmentWizard (fleshed out from FE-B1 skeleton)
export { MFAEnrollmentWizard } from "./mfa-enrollment-wizard";
export type {
  MFAEnrollmentWizardProps,
  MFAEnrollmentWizardPropsExtended,
  MFAEnrollmentPath,
  MFAEnrollmentStep,
  MFAWizardInternalStep,
  MfaEnrollStartPayload,
  MfaWizardState,
} from "./mfa-enrollment-wizard";
export {
  MFA_PATH_LABELS,
  MFA_PATH_DESCRIPTIONS,
  MFA_STEP_LABELS,
  MFA_STEP_ORDER,
} from "./mfa-enrollment-wizard";

// NotificationPreferenceMatrix (shared — FE-B13 uses visibleCategories subset)
export { NotificationPreferenceMatrix } from "./notification-preference-matrix";
export type {
  NotificationPreferenceMatrixProps,
  NotificationPreferenceCell,
  NotificationCategoryRow,
  NotificationChannel,
  NotificationPreferenceScope,
} from "./notification-preference-matrix";

// NotificationCenterBell (shared — FE-B13 embeds in onboarding confirmation)
export { NotificationCenterBell } from "./notification-center-bell";
export type {
  NotificationCenterBellProps,
  InAppNotification,
  NotificationSseEvent,
  UseInAppNotificationsReturn,
} from "./notification-center-bell";

// useInAppNotifications hook (shared — web + mobile)
export { useInAppNotifications } from "./hooks/useInAppNotifications";

// ── FE-B13 Exports ─────────────────────────────────────────────────────────────
// Onboarding & Push Permissions: StripePaymentForm (LOCKED for FE-B14),
// TierPickerCard fleshed (interface frozen after FE-B13)

// StripePaymentForm — SINGLE Stripe Elements boundary (RULE 1)
// LOCKED INTERFACE: FE-B14 may only add optional props
export { StripePaymentForm } from "./stripe-payment";
export type {
  StripePaymentFormProps,
  StripePaymentResult,
  StripePaymentError,
  StripePaymentMode,
} from "./stripe-payment";

// ── FE-B15 Exports ─────────────────────────────────────────────────────────────
// In-Flight Sync Indicator refinement — unified hook + API locked
// useInFlightSyncStatus: single data source for all sync surfaces (except dispatch)
// InFlightSyncStatus: hook return type — spread as props onto <InFlightSyncIndicator>

export { useInFlightSyncStatus } from "./hooks/useInFlightSyncStatus";
export type { InFlightSyncStatus } from "./hooks/useInFlightSyncStatus";

// ── FE-B16 Exports ─────────────────────────────────────────────────────────────
// Help System — FINAL MVP FRONTEND BATCH
// ⚠️ HelpAnchor, HelpChatMessages, KnowledgeBoundaryMessage: LOCKED after FE-B16.

// HelpAnchor — contextual "?" icon (14 surfaces consume this)
export { HelpAnchor } from "./help-anchor";
export type {
  HelpAnchorProps,
  HelpContextPayload,
  HelpActionType,
} from "./help-anchor/types";

// HelpChatMessages — shared message list + composer (web drawer + mobile screen)
export { HelpChatMessages } from "./help-chat-messages";
export type {
  HelpChatMessagesProps,
  HelpChatMessage,
  HelpChatSession,
  HelpFollowUpAction,
} from "./help-chat-messages/types";

// KnowledgeBoundaryMessage — distinct AI non-answer bubble (web + mobile)
export { KnowledgeBoundaryMessage } from "./knowledge-boundary-message";
export type { KnowledgeBoundaryMessageProps } from "./knowledge-boundary-message/types";

// ── PLP-FIX-4 Exports ───────────────────────────────────────────────────────────
// PhoneInput — shared US phone input with progressive masking (web-first).
// Pure formatting utils are platform-agnostic; RN variant deferred.
export { PhoneInput } from "./phone-input";
export type { PhoneInputProps } from "./phone-input";
export {
  normalizeUsPhoneDigits,
  formatUsPhoneDisplay,
  usPhoneToE164,
} from "./phone-input";
