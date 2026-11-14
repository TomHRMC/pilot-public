/**
 * Mobile Comms Send Flow — (tabs)/jobs/[jobId]/comms
 *
 * Full-screen stack route pushed from Job Detail → "Communicate" button.
 * Contains: template picker → (optionally) time-extraction editor → preview modal → sent confirmation.
 *
 * Voice path: also navigates here after intent classification.
 * Online-only: blocks send when offline (§G3 — no offline queue for comms).
 */

import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  Pressable,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useQuery } from "@tanstack/react-query";
import { usePreviewBeforeSend, TimeExtractionEditor } from "@pilot/ui";
import { ErrorState } from "@pilot/ui/states";
import { colors, radii, spacing, fontWeights } from "@pilot/ui/tokens";
import type { CommTemplateTypeResponse } from "@pilot/ui";

// ── Template icon map ─────────────────────────────────────────────────────────

const TEMPLATE_ICONS: Record<string, string> = {
  on_my_way: "🚗",
  running_late: "⏰",
  arrived: "📍",
  job_complete: "✅",
  appointment_reminder: "📅",
  follow_up: "👋",
};

// ── Screen states ─────────────────────────────────────────────────────────────

type ScreenState =
  | "template-picker"
  | "disambiguation"
  | "time-extraction"
  | "sent-confirmation";

// ── API fetch ─────────────────────────────────────────────────────────────────

async function fetchTemplates(): Promise<CommTemplateTypeResponse[]> {
  const res = await fetch(
    "/api/v1/communications/comm-template-types?initiator=tech",
  );
  if (!res.ok) throw new Error("Failed to load templates");
  const data = (await res.json()) as { items: CommTemplateTypeResponse[] };
  return data.items.sort((a, b) => a.sort_order - b.sort_order);
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function JobCommsScreen() {
  const { jobId, customerId: paramCustomerId } = useLocalSearchParams<{
    jobId: string;
    customerId: string;
  }>();

  const [screenState, setScreenState] =
    useState<ScreenState>("template-picker");
  const [channelOverride, setChannelOverride] = useState<
    "sms" | "email" | null
  >(null);
  const [selectedTemplate, setSelectedTemplate] =
    useState<CommTemplateTypeResponse | null>(null);
  const [extractedMinutes] = useState<number>(20);
  const [isOffline, setIsOffline] = useState(false);
  const [sendErrorMsg, setSendErrorMsg] = useState<string | null>(null);
  const [isSentSuccess, setIsSentSuccess] = useState(false);

  // Online guard
  useEffect(() => {
    // React Native: use NetInfo if available; fall back to navigator.onLine
    const checkOnline = () => {
      if (typeof navigator !== "undefined") {
        setIsOffline(!navigator.onLine);
      }
    };
    checkOnline();
    if (typeof window !== "undefined") {
      window.addEventListener?.("online", checkOnline);
      window.addEventListener?.("offline", checkOnline);
      return () => {
        window.removeEventListener?.("online", checkOnline);
        window.removeEventListener?.("offline", checkOnline);
      };
    }
    return undefined;
  }, []);

  // Auto-return after sent success
  useEffect(() => {
    if (isSentSuccess) {
      const timer = setTimeout(() => router.back(), 2400);
      return () => clearTimeout(timer);
    }
    return undefined;
  }, [isSentSuccess]);

  const {
    data: templates,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["comm-template-types"],
    queryFn: fetchTemplates,
    staleTime: 5 * 60 * 1000,
  });

  const { preview, MessagePreviewModal, isPreviewLoading } =
    usePreviewBeforeSend({
      onSendSuccess: () => {
        setIsSentSuccess(true);
        setScreenState("sent-confirmation");
      },
      onSendError: (err) => {
        if (err.message === "QUOTA_EXHAUSTED") {
          setSendErrorMsg(
            "Monthly SMS quota reached — contact your account owner",
          );
        } else if (err.message === "OFFLINE") {
          setIsOffline(true);
        } else {
          setSendErrorMsg(err.message);
        }
      },
    });

  async function handleTemplateSelect(template: CommTemplateTypeResponse) {
    if (isOffline) return;
    setSelectedTemplate(template);

    // Templates requiring time variable go through TimeExtractionEditor first
    const needsTimeExtraction =
      template.code === "on_my_way" || template.code === "running_late";

    if (needsTimeExtraction) {
      setScreenState("time-extraction");
    } else {
      // Call preview immediately with empty variables
      try {
        await preview({
          mode: "template",
          customerId: paramCustomerId,
          templateCode: template.code,
          jobId,
          variables: {},
          channelOverride,
        });
      } catch (err) {
        if (err instanceof Error) {
          setSendErrorMsg(err.message);
        }
      }
    }
  }

  async function handleTimeConfirm(minutes: number) {
    if (!selectedTemplate) return;
    try {
      await preview({
        mode: "template",
        customerId: paramCustomerId,
        templateCode: selectedTemplate.code,
        jobId,
        variables: { eta_minutes: minutes },
        channelOverride,
      });
    } catch (err) {
      if (err instanceof Error) setSendErrorMsg(err.message);
      setScreenState("template-picker");
    }
  }

  // ── Offline state ─────────────────────────────────────────────────────────
  if (isOffline) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Pressable
            onPress={() => router.back()}
            style={styles.backButton}
            accessibilityLabel="Back"
          >
            <Text style={styles.backButtonText}>← Back</Text>
          </Pressable>
          <Text style={styles.headerTitle}>Send message</Text>
        </View>
        <View style={styles.center}>
          <ErrorState
            type="network"
            title="No internet connection"
            description="Message send requires internet connection."
          />
        </View>
      </View>
    );
  }

  // ── Sent confirmation ─────────────────────────────────────────────────────
  if (screenState === "sent-confirmation") {
    return (
      <View style={styles.container} testID="sent-confirmation">
        <View style={styles.center}>
          <Text style={styles.successIcon}>✅</Text>
          <Text style={styles.successTitle}>Message sent</Text>
          <Text style={styles.successSubtitle}>Returning to job…</Text>
        </View>
      </View>
    );
  }

  // ── Time extraction editor ────────────────────────────────────────────────
  if (screenState === "time-extraction") {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Pressable
            onPress={() => setScreenState("template-picker")}
            style={styles.backButton}
            accessibilityLabel="Back"
          >
            <Text style={styles.backButtonText}>← Back</Text>
          </Pressable>
          <Text style={styles.headerTitle}>ETA</Text>
        </View>
        <TimeExtractionEditor
          initialMinutes={extractedMinutes}
          onConfirm={handleTimeConfirm}
          onCancel={() => setScreenState("template-picker")}
          testID="time-extraction-editor"
        />
        {isPreviewLoading && (
          <ActivityIndicator style={styles.loader} color={colors.brand[600]} />
        )}
      </View>
    );
  }

  // ── Template picker ───────────────────────────────────────────────────────
  return (
    <View style={styles.container} testID="job-comms-screen">
      {/* Header */}
      <View style={styles.header}>
        <Pressable
          onPress={() => router.back()}
          style={styles.backButton}
          accessibilityLabel="Back to job"
        >
          <Text style={styles.backButtonText}>← Job</Text>
        </Pressable>
        <Text style={styles.headerTitle}>Send message</Text>
      </View>

      {/* Channel override */}
      <View style={styles.channelRow}>
        <View style={styles.channelPill}>
          <Text style={styles.channelPillText}>
            {channelOverride === "email" ? "✉️ Email" : "💬 SMS preferred"}
          </Text>
        </View>
        <Pressable
          onPress={() =>
            setChannelOverride((prev) => (prev === "email" ? null : "email"))
          }
          accessibilityRole="button"
          accessibilityLabel="Change channel"
          testID="channel-override-link"
        >
          <Text style={styles.channelOverrideLink}>
            {channelOverride === "email"
              ? "Use SMS instead →"
              : "Send via email instead →"}
          </Text>
        </Pressable>
      </View>

      {/* Voice CTA panel */}
      <View style={styles.voiceCta}>
        <Text style={styles.voiceCtaText}>
          {`🎙️ Say "Tell [customer] I'm on my way" to send by voice`}
        </Text>
      </View>

      {/* Error display */}
      {sendErrorMsg && (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{sendErrorMsg}</Text>
          <Pressable onPress={() => setSendErrorMsg(null)}>
            <Text style={styles.errorDismiss}>✕</Text>
          </Pressable>
        </View>
      )}

      {/* Template grid */}
      <ScrollView style={styles.scrollContent}>
        {isLoading && (
          <ActivityIndicator
            color={colors.brand[600]}
            style={styles.loader}
            accessibilityLabel="Loading templates"
          />
        )}
        {isError && (
          <View style={styles.center}>
            <ErrorState
              type="server"
              title="Failed to load templates"
              description="Please try again"
            />
          </View>
        )}
        {templates && (
          <View style={styles.templateGrid} testID="template-grid">
            {templates.map((template, idx) => (
              <Pressable
                key={template.code}
                style={styles.templateCard}
                onPress={() => handleTemplateSelect(template)}
                disabled={isPreviewLoading}
                accessibilityRole="button"
                accessibilityLabel={template.name}
                testID={`template-card-${template.code}`}
              >
                <Text style={styles.templateIcon} aria-hidden>
                  {TEMPLATE_ICONS[template.code] ?? "📨"}
                </Text>
                <Text style={styles.templateName}>{template.name}</Text>
                {template.description ? (
                  <Text style={styles.templateDesc} numberOfLines={1}>
                    {template.description}
                  </Text>
                ) : null}
              </Pressable>
            ))}
          </View>
        )}
      </ScrollView>

      {/* Embedded preview modal from hook */}
      <MessagePreviewModal
        onEdit={() => setScreenState("template-picker")}
        testID="message-preview-modal"
      />
    </View>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.neutral[50],
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[200],
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[4],
    backgroundColor: "#FFFFFF",
    gap: spacing[4],
  },
  backButton: {
    minWidth: 44,
    minHeight: 44,
    justifyContent: "center",
  },
  backButtonText: {
    color: colors.brand[600],
    fontSize: 15,
    fontWeight: String(fontWeights.medium) as "500",
  },
  headerTitle: {
    color: colors.neutral[900],
    fontSize: 20,
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 28,
  },
  channelRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[3],
    backgroundColor: "#FFFFFF",
    borderBottomWidth: 1,
    borderBottomColor: colors.neutral[100],
  },
  channelPill: {
    backgroundColor: colors.brand[50],
    borderRadius: radii.full,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[1],
  },
  channelPillText: {
    color: colors.brand[800],
    fontSize: 13,
    fontWeight: String(fontWeights.medium) as "500",
  },
  channelOverrideLink: {
    color: colors.brand[600],
    fontSize: 13,
    textDecorationLine: "underline",
  },
  voiceCta: {
    backgroundColor: colors.alert[50],
    borderBottomWidth: 1,
    borderBottomColor: colors.alert[200],
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[3],
  },
  voiceCtaText: {
    color: colors.alert[800],
    fontSize: 13,
    lineHeight: 20,
  },
  errorBanner: {
    backgroundColor: colors.fault[50],
    borderBottomWidth: 1,
    borderBottomColor: colors.fault[200],
    paddingHorizontal: spacing[6],
    paddingVertical: spacing[3],
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  errorText: {
    color: colors.fault[800],
    fontSize: 13,
    flex: 1,
  },
  errorDismiss: {
    color: colors.fault[600],
    fontSize: 15,
    paddingLeft: spacing[3],
  },
  scrollContent: {
    flex: 1,
  },
  templateGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    padding: spacing[4],
    gap: spacing[3],
  },
  templateCard: {
    width: "47%",
    backgroundColor: "#FFFFFF",
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    padding: spacing[4],
    minHeight: 100,
  },
  templateIcon: {
    fontSize: 28,
    marginBottom: spacing[2],
  },
  templateName: {
    color: colors.neutral[900],
    fontSize: 15,
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 22,
  },
  templateDesc: {
    color: colors.neutral[400],
    fontSize: 11,
    lineHeight: 16,
    marginTop: 2,
  },
  loader: {
    marginTop: spacing[8],
  },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing[6],
  },
  successIcon: {
    fontSize: 56,
    marginBottom: spacing[4],
  },
  successTitle: {
    color: colors.margin[600],
    fontSize: 22,
    fontWeight: String(fontWeights.medium) as "500",
    lineHeight: 30,
    marginBottom: spacing[2],
  },
  successSubtitle: {
    color: colors.neutral[400],
    fontSize: 15,
    lineHeight: 22,
  },
});
