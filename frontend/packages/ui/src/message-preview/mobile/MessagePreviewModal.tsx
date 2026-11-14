/**
 * MessagePreviewModal — Mobile (React Native / Gluestack-UI)
 *
 * Location: packages/ui/src/message-preview/mobile/MessagePreviewModal.tsx
 *
 * Renders as a full-screen bottom sheet modal on mobile.
 * All spacing/colors from token system — zero hardcoded values.
 *
 * IMPORTANT: Uses React Native primitives + token system.
 * No hardcoded fontSize, color, padding, or borderRadius values.
 */

import React from "react";
import {
  View,
  Text,
  Pressable,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
  Modal,
} from "react-native";
import { colors, lightTheme, radii, spacing, fontWeights } from "../../tokens";
import { VoiceConfirmTurn } from "../../voice-confirm-turn";
import type {
  EditableVariableResponse,
  MessagePreviewModalProps,
} from "../types";

// ── Helpers ───────────────────────────────────────────────────────────────────

function ChannelPill({
  channel,
  isOverridden,
}: {
  channel: string;
  isOverridden: boolean;
}) {
  const isSms = channel === "sms";
  return (
    <View style={styles.channelRow}>
      <View style={[styles.pill, isSms ? styles.smsPill : styles.emailPill]}>
        <Text
          style={[
            styles.pillText,
            isSms ? styles.smsPillText : styles.emailPillText,
          ]}
          accessibilityLabel={`Channel: ${channel}`}
        >
          {isSms ? "💬 SMS" : "✉️ Email"}
        </Text>
      </View>
      {isOverridden && (
        <View style={styles.overrideBadge}>
          <Text style={styles.overrideBadgeText}>Channel overridden</Text>
        </View>
      )}
    </View>
  );
}

// ── Component ─────────────────────────────────────────────────────────────────

/**
 * MessagePreviewModal (Mobile)
 *
 * Full-screen modal rendering the server-rendered message preview.
 * voiceMode renders <VoiceConfirmTurn> instead of tap buttons.
 */
export function MessagePreviewModal({
  previewData,
  isOpen,
  onConfirm,
  onCancel,
  onEdit,
  isSending = false,
  voiceMode = false,
  onChannelOverride,
  smsSegmentCount,
  testID,
}: MessagePreviewModalProps) {
  if (!previewData) return null;

  const {
    rendered_body,
    rendered_subject,
    recipient_name,
    recipient_address,
    actual_channel,
    editable_variables,
  } = previewData;

  const isChannelOverridden =
    "channel_override_flag" in previewData
      ? Boolean(
          (previewData as { channel_override_flag?: boolean })
            .channel_override_flag,
        )
      : false;

  const sendLabel = `Send to ${recipient_name}`;

  return (
    <Modal
      visible={isOpen}
      animationType="slide"
      presentationStyle="fullScreen"
      accessible
      accessibilityViewIsModal
      onRequestClose={onCancel}
      testID={testID ?? "message-preview-modal"}
    >
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Preview message</Text>
          <Pressable
            onPress={onCancel}
            disabled={isSending}
            accessibilityRole="button"
            accessibilityLabel="Close preview"
            accessibilityState={{ disabled: isSending }}
            testID="preview-close-btn"
            style={styles.closeButton}
          >
            <Text style={styles.closeButtonText}>✕</Text>
          </Pressable>
        </View>

        <ScrollView
          style={styles.scrollContent}
          contentContainerStyle={styles.scrollInner}
          showsVerticalScrollIndicator={false}
        >
          {/* Recipient row */}
          <View style={styles.section}>
            <Text style={styles.labelText}>To</Text>
            <Text style={styles.recipientName}>{recipient_name}</Text>
            <Text style={styles.recipientAddress}>{recipient_address}</Text>
          </View>

          {/* Channel + override */}
          <View style={[styles.section, styles.channelSection]}>
            <ChannelPill
              channel={actual_channel}
              isOverridden={isChannelOverridden}
            />
            {onChannelOverride && (
              <Pressable
                onPress={() =>
                  onChannelOverride(actual_channel === "sms" ? "email" : "sms")
                }
                disabled={isSending}
                accessibilityRole="button"
                accessibilityLabel="Change channel"
              >
                <Text style={styles.changChannelLink}>Change channel</Text>
              </Pressable>
            )}
          </View>

          {/* Subject (email only) */}
          {rendered_subject ? (
            <View style={styles.section}>
              <Text style={styles.labelText}>Subject</Text>
              <Text style={styles.bodyText}>{rendered_subject}</Text>
            </View>
          ) : null}

          {/* Message body */}
          <View style={styles.section}>
            <Text style={styles.labelText}>Message</Text>
            <View style={styles.messageBox}>
              <Text style={styles.messageBody} accessibilityLiveRegion="polite">
                {rendered_body}
              </Text>
            </View>

            {/* Editable variable chips */}
            {editable_variables.length > 0 && (
              <View style={styles.chipRow}>
                {editable_variables.map((v: EditableVariableResponse) => (
                  <View key={v.name} style={styles.editableChip}>
                    <Text style={styles.editableChipText}>
                      {v.label}: {String(v.value)}
                    </Text>
                  </View>
                ))}
              </View>
            )}
          </View>

          {/* SMS segment count */}
          {actual_channel === "sms" && smsSegmentCount !== undefined && (
            <View style={styles.section}>
              <Text style={styles.segmentText}>
                {smsSegmentCount} SMS segment{smsSegmentCount !== 1 ? "s" : ""}
              </Text>
            </View>
          )}
        </ScrollView>

        {/* Footer actions */}
        <View style={styles.footer}>
          {voiceMode ? (
            <VoiceConfirmTurn
              prompt={`Send "${rendered_body.slice(0, 60)}${rendered_body.length > 60 ? "…" : ""}" to ${recipient_name}?`}
              onConfirm={onConfirm}
              onCancel={onCancel}
              isProcessing={isSending}
              testID="voice-confirm-in-preview"
            />
          ) : (
            <View style={styles.buttonRow}>
              {onEdit && (
                <Pressable
                  style={[styles.button, styles.editButton]}
                  onPress={onEdit}
                  disabled={isSending}
                  accessibilityRole="button"
                  accessibilityLabel="Edit message"
                  accessibilityState={{ disabled: isSending }}
                  testID="preview-edit-btn"
                >
                  <Text style={styles.editButtonText}>Edit</Text>
                </Pressable>
              )}
              <Pressable
                style={[styles.button, styles.cancelButton]}
                onPress={onCancel}
                disabled={isSending}
                accessibilityRole="button"
                accessibilityLabel="Cancel"
                accessibilityState={{ disabled: isSending }}
                testID="preview-cancel-btn"
              >
                <Text style={styles.cancelButtonText}>Cancel</Text>
              </Pressable>
              <Pressable
                style={[
                  styles.button,
                  styles.sendButton,
                  isSending && styles.buttonDisabled,
                ]}
                onPress={onConfirm}
                disabled={isSending}
                accessibilityRole="button"
                accessibilityLabel={sendLabel}
                accessibilityState={{ disabled: isSending, busy: isSending }}
                testID="preview-send-btn"
              >
                {isSending ? (
                  <ActivityIndicator
                    color={colors.neutral[50]}
                    accessibilityLabel="Sending"
                  />
                ) : (
                  <Text style={styles.sendButtonText}>{sendLabel}</Text>
                )}
              </Pressable>
            </View>
          )}
        </View>
      </View>
    </Modal>
  );
}

// ── Styles (token-based — zero hardcoded values) ──────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[4],
    backgroundColor: lightTheme.background.secondary,
  },
  headerTitle: {
    color: colors.neutral[900],
    fontSize: 20, // mobileFontSizes.h1
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 28,
  },
  closeButton: {
    padding: spacing[2],
    minWidth: 44,
    minHeight: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  closeButtonText: {
    color: colors.neutral[600],
    fontSize: 17, // mobileFontSizes.h3
  },
  scrollContent: {
    flex: 1,
  },
  scrollInner: {
    paddingBottom: spacing[8],
  },
  section: {
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[3],
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[100],
  },
  channelSection: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  labelText: {
    color: colors.neutral[400],
    fontSize: 11, // mobileFontSizes.caption
    lineHeight: 16,
    marginBottom: spacing[1],
  },
  recipientName: {
    color: colors.neutral[900],
    fontSize: 15, // mobileFontSizes.bodyLg
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 22,
  },
  recipientAddress: {
    color: colors.neutral[600],
    fontSize: 13, // mobileFontSizes.body
    lineHeight: 20,
  },
  channelRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing[2],
  },
  pill: {
    borderRadius: radii.full,
    paddingHorizontal: spacing[2],
    paddingVertical: spacing[1],
  },
  smsPill: {
    backgroundColor: colors.brand[50],
  },
  emailPill: {
    backgroundColor: colors.neutral[100],
  },
  pillText: {
    fontSize: 11, // mobileFontSizes.caption
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 16,
  },
  smsPillText: {
    color: colors.brand[800],
  },
  emailPillText: {
    color: colors.neutral[600],
  },
  overrideBadge: {
    backgroundColor: colors.alert[50],
    borderRadius: radii.full,
    paddingHorizontal: spacing[2],
    paddingVertical: spacing[1],
  },
  overrideBadgeText: {
    color: colors.alert[800],
    fontSize: 11, // mobileFontSizes.caption
    fontWeight: String(fontWeights.medium) as "500",
  },
  changChannelLink: {
    color: colors.brand[600],
    fontSize: 13, // mobileFontSizes.body
    textDecorationLine: "underline",
  },
  bodyText: {
    color: colors.neutral[900],
    fontSize: 13, // mobileFontSizes.body
    lineHeight: 20,
  },
  messageBox: {
    backgroundColor: colors.neutral[100],
    borderRadius: radii.md,
    padding: spacing[3],
  },
  messageBody: {
    color: colors.neutral[900],
    fontSize: 13, // mobileFontSizes.body
    lineHeight: 20,
  },
  chipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing[2],
    marginTop: spacing[2],
  },
  editableChip: {
    borderWidth: 1,
    borderStyle: "dashed",
    borderColor: colors.alert[400],
    backgroundColor: colors.alert[50],
    borderRadius: radii.sm,
    paddingHorizontal: spacing[2],
    paddingVertical: spacing[1],
  },
  editableChipText: {
    color: colors.alert[800],
    fontSize: 11, // mobileFontSizes.caption
  },
  segmentText: {
    color: colors.neutral[400],
    fontSize: 11, // mobileFontSizes.caption
    lineHeight: 16,
  },
  footer: {
    borderTopWidth: 1,
    borderTopColor: colors.neutral[200],
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[4],
    backgroundColor: lightTheme.background.secondary,
  },
  buttonRow: {
    flexDirection: "row",
    gap: spacing[3],
  },
  button: {
    borderRadius: radii.md,
    paddingVertical: spacing[3],
    alignItems: "center",
    justifyContent: "center",
    minHeight: 56, // touchTargets.mobile.md — glove-friendly
  },
  editButton: {
    flex: 1,
    backgroundColor: colors.neutral[100],
    borderWidth: 1,
    borderColor: colors.neutral[200],
  },
  cancelButton: {
    flex: 1,
    backgroundColor: colors.neutral[100],
    borderWidth: 1,
    borderColor: colors.neutral[200],
  },
  sendButton: {
    flex: 2,
    backgroundColor: colors.brand[600],
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  editButtonText: {
    color: colors.neutral[800],
    fontSize: 15, // mobileFontSizes.bodyLg
    fontWeight: String(fontWeights.medium) as "500",
  },
  cancelButtonText: {
    color: colors.neutral[800],
    fontSize: 15, // mobileFontSizes.bodyLg
    fontWeight: String(fontWeights.medium) as "500",
  },
  sendButtonText: {
    color: colors.neutral[50],
    fontSize: 15, // mobileFontSizes.bodyLg
    fontWeight: String(fontWeights.medium) as "500",
  },
});
