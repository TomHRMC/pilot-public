/**
 * MfaEnrollmentRequiredGate — mobile
 *
 * Location: apps/mobile/features/login/components/MfaEnrollmentRequiredGate.tsx
 *
 * Blocking screen shown when MFA enrollment is required but not completed.
 * Routes to /settings/account for enrollment (FE-B12 scope).
 *
 * FE-B2: design doc §A.2 MfaEnrollmentRequiredGate (mobile)
 */

import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
} from "react-native";
import { tokens, fontWeights } from "@/constants/style-constants";
import { lightTheme } from "@pilot/ui/tokens";

interface MfaEnrollmentRequiredGateProps {
  gracePeriodEndsAt?: string;
  onBeginEnrollment: () => void;
  onSignOut: () => void;
}

function getDaysRemaining(endsAt: string): number {
  const end = new Date(endsAt);
  const now = new Date();
  const diffMs = end.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
}

export function MfaEnrollmentRequiredGate({
  gracePeriodEndsAt,
  onBeginEnrollment,
  onSignOut,
}: MfaEnrollmentRequiredGateProps) {
  const isInGracePeriod = Boolean(gracePeriodEndsAt);
  const daysRemaining = gracePeriodEndsAt
    ? getDaysRemaining(gracePeriodEndsAt)
    : 0;

  if (isInGracePeriod) {
    return (
      <View style={styles.warningBanner} accessibilityRole="alert">
        <Text style={styles.warningText}>
          MFA enrollment required within{" "}
          <Text style={styles.warningBold}>
            {daysRemaining} day{daysRemaining !== 1 ? "s" : ""}
          </Text>
          .
        </Text>
        <TouchableOpacity
          onPress={onBeginEnrollment}
          accessibilityLabel="Set up MFA now"
          style={styles.setupNowButton}
          activeOpacity={0.7}
        >
          <Text style={styles.setupNowText}>Set up now →</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <ScrollView
      contentContainerStyle={styles.container}
      keyboardShouldPersistTaps="handled"
    >
      <View style={styles.card}>
        <Text style={styles.title}>Multi-factor authentication required</Text>
        <Text style={styles.body}>
          Multi-factor authentication is required by your organization. Set it
          up to continue.
        </Text>

        <TouchableOpacity
          onPress={onBeginEnrollment}
          accessibilityLabel="Set up MFA"
          testID="setup-mfa-button"
          style={styles.primaryButton}
          activeOpacity={0.8}
        >
          <Text style={styles.primaryButtonText}>Set up MFA</Text>
        </TouchableOpacity>

        <TouchableOpacity
          onPress={onSignOut}
          accessibilityLabel="Sign out"
          testID="signout-button"
          style={styles.secondaryButton}
          activeOpacity={0.7}
        >
          <Text style={styles.secondaryButtonText}>Sign out</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: tokens.spacing[6],
    backgroundColor: tokens.colors.neutral[100],
  },
  card: {
    width: "100%",
    backgroundColor: lightTheme.background.secondary,
    borderRadius: tokens.radii.lg,
    padding: tokens.spacing[6],
    gap: tokens.spacing[4],
    alignItems: "center",
  },
  title: {
    fontSize: tokens.mobileFontSizes.h1,
    lineHeight: tokens.mobileLineHeights.h1,
    fontWeight: fontWeights.medium,
    color: tokens.colors.neutral[900],
    textAlign: "center",
  },
  body: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[600],
    textAlign: "center",
  },
  primaryButton: {
    width: "100%",
    backgroundColor: lightTheme.brand.bg,
    borderRadius: tokens.radii.md,
    paddingVertical: tokens.spacing[3],
    paddingHorizontal: tokens.spacing[4],
    minHeight: tokens.touchTargets.mobile.md,
    alignItems: "center",
    justifyContent: "center",
  },
  primaryButtonText: {
    fontSize: tokens.mobileFontSizes.bodyLg,
    lineHeight: tokens.mobileLineHeights.bodyLg,
    fontWeight: fontWeights.medium,
    color: lightTheme.brand.text,
  },
  secondaryButton: {
    paddingVertical: tokens.spacing[2],
    minHeight: tokens.touchTargets.mobile.sm,
    alignItems: "center",
  },
  secondaryButtonText: {
    fontSize: tokens.mobileFontSizes.caption,
    lineHeight: tokens.mobileLineHeights.caption,
    color: tokens.colors.neutral[400],
  },
  warningBanner: {
    backgroundColor: lightTheme.warning.bgMuted,
    borderWidth: 1,
    borderColor: tokens.colors.alert[200],
    borderRadius: tokens.radii.md,
    padding: tokens.spacing[3],
    gap: tokens.spacing[2],
  },
  warningText: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: lightTheme.warning.textOnMuted,
  },
  warningBold: {
    fontWeight: fontWeights.medium,
  },
  setupNowButton: {
    minHeight: tokens.touchTargets.mobile.sm,
    justifyContent: "center",
  },
  setupNowText: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: lightTheme.brand.textOnMuted,
  },
});
