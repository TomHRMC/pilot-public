/**
 * Push Permission Pre-Explainer Screen — Tier 3 #11
 *
 * Location: apps/mobile/app/(onboarding)/push-permission.tsx
 *
 * RULE 6: requestPermissionsAsync fires EXACTLY ONCE per device-install.
 *         "Allow notifications" → OS prompt → granted or denied_by_os.
 *         "Maybe later" → denied_by_user_choice — NO OS prompt fires.
 *         On denial: PushDeniedFallback screen inline (no re-prompt).
 */

import React, { useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  ActivityIndicator,
} from "react-native";
import { useRouter } from "expo-router";
import { usePushPermission } from "@/features/onboarding/hooks/usePushPermission";

type ScreenState = "pre-explainer" | "denied-fallback" | "granted-confirmation";

const BENEFITS = [
  {
    icon: "🔔",
    title: "Job updates",
    detail: "Get notified when a customer approves your quote",
  },
  {
    icon: "⚡",
    title: "Instant alerts",
    detail: "Know immediately when a new job request comes in",
  },
  {
    icon: "💬",
    title: "Customer messages",
    detail: "Reply to customers faster with push alerts",
  },
  {
    icon: "📋",
    title: "Schedule changes",
    detail: "Never miss a reschedule or cancellation",
  },
];

export default function PushPermissionScreen() {
  const router = useRouter();
  const {
    requestPermission,
    deferPermission,
    openNotificationSettings,
    isLoading,
  } = usePushPermission();
  const [screenState, setScreenState] = useState<ScreenState>("pre-explainer");

  const handleAllow = async () => {
    // RULE 6: This is the ONLY call to requestPermission — never repeats
    const result = await requestPermission();
    if (result === "granted") {
      setScreenState("granted-confirmation");
      // Auto-advance after 1.5s
      setTimeout(() => {
        router.push("/(onboarding)/tour-today" as never);
      }, 1500);
    } else {
      // denied_by_os — show fallback without re-prompting
      setScreenState("denied-fallback");
    }
  };

  const handleMaybeLater = async () => {
    // No OS prompt fires for "Maybe later"
    await deferPermission();
    router.push("/(onboarding)/tour-today" as never);
  };

  const handleOpenSettings = () => {
    openNotificationSettings();
  };

  const handleContinueFromDenied = () => {
    router.push("/(onboarding)/tour-today" as never);
  };

  // ── Granted confirmation ──────────────────────────────────────────────────
  if (screenState === "granted-confirmation") {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.confirmationContent}>
          <Text style={styles.confirmationIcon}>✅</Text>
          <Text style={styles.confirmationTitle}>
            Push notifications enabled
          </Text>
          <Text style={styles.confirmationSub}>
            You&apos;re all set to receive updates from Pilot.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  // ── Denied fallback ───────────────────────────────────────────────────────
  if (screenState === "denied-fallback") {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.content} testID="push-denied-fallback">
          <Text style={styles.deniedIcon}>📵</Text>
          <Text style={styles.headline}>No worries</Text>
          <Text style={styles.subheadline}>
            You&apos;ll still get email and in-app alerts for important updates.
            You can enable push notifications anytime in your device Settings.
          </Text>

          <TouchableOpacity
            style={styles.button}
            onPress={handleOpenSettings}
            accessibilityRole="button"
            accessibilityLabel="Open notification settings"
            testID="push-denied-open-settings"
          >
            <Text style={styles.buttonText}>Open Settings</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.secondaryButton}
            onPress={handleContinueFromDenied}
            accessibilityRole="button"
            accessibilityLabel="Continue without push notifications"
            testID="push-denied-continue"
          >
            <Text style={styles.secondaryButtonText}>Continue →</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // ── Pre-explainer ─────────────────────────────────────────────────────────
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content} testID="push-permission-preexplainer">
        <Text style={styles.headline}>Stay in the loop</Text>
        <Text style={styles.subheadline}>
          Enable notifications so you never miss a job update, customer message,
          or schedule change.
        </Text>

        {/* Benefits list */}
        <View style={styles.benefitsList}>
          {BENEFITS.map((b) => (
            <View key={b.title} style={styles.benefitRow}>
              <Text style={styles.benefitIcon}>{b.icon}</Text>
              <View style={styles.benefitText}>
                <Text style={styles.benefitTitle}>{b.title}</Text>
                <Text style={styles.benefitDetail}>{b.detail}</Text>
              </View>
            </View>
          ))}
        </View>

        {/* Allow button */}
        <TouchableOpacity
          style={[styles.button, isLoading && styles.buttonDisabled]}
          onPress={handleAllow}
          disabled={isLoading}
          accessibilityRole="button"
          accessibilityLabel="Allow notifications"
          testID="push-permission-allow-button"
        >
          {isLoading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.buttonText}>Allow notifications</Text>
          )}
        </TouchableOpacity>

        {/* Maybe later */}
        <TouchableOpacity
          style={styles.secondaryButton}
          onPress={handleMaybeLater}
          disabled={isLoading}
          accessibilityRole="button"
          accessibilityLabel="Maybe later"
          testID="push-permission-maybe-later"
        >
          <Text style={styles.secondaryButtonText}>Maybe later</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#F9FAFB" },
  content: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 28,
    gap: 16,
  },
  headline: {
    fontSize: 26,
    fontWeight: "700",
    color: "#111827",
    textAlign: "center",
  },
  subheadline: {
    fontSize: 15,
    color: "#6B7280",
    textAlign: "center",
    lineHeight: 22,
  },
  benefitsList: {
    width: "100%",
    gap: 12,
    marginVertical: 8,
  },
  benefitRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 12,
    backgroundColor: "#FFFFFF",
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: "#F3F4F6",
  },
  benefitIcon: { fontSize: 22 },
  benefitText: { flex: 1 },
  benefitTitle: {
    fontSize: 14,
    fontWeight: "600",
    color: "#111827",
  },
  benefitDetail: {
    fontSize: 13,
    color: "#9CA3AF",
    marginTop: 2,
  },
  button: {
    backgroundColor: "#4F46E5",
    paddingVertical: 14,
    paddingHorizontal: 32,
    borderRadius: 12,
    width: "100%",
    alignItems: "center",
    marginTop: 8,
  },
  buttonDisabled: { opacity: 0.5 },
  buttonText: { color: "#FFFFFF", fontSize: 15, fontWeight: "600" },
  secondaryButton: {
    paddingVertical: 10,
    alignItems: "center",
    width: "100%",
  },
  secondaryButtonText: {
    color: "#6B7280",
    fontSize: 14,
  },
  // Confirmation state
  confirmationContent: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 12,
    paddingHorizontal: 32,
  },
  confirmationIcon: { fontSize: 56 },
  confirmationTitle: {
    fontSize: 22,
    fontWeight: "700",
    color: "#059669", // margin-600 approx
    textAlign: "center",
  },
  confirmationSub: {
    fontSize: 15,
    color: "#6B7280",
    textAlign: "center",
  },
  // Denied state
  deniedIcon: { fontSize: 48 },
});
