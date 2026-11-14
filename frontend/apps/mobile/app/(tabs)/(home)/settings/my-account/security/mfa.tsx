/**
 * MFA Enrollment Screen (MOB-B10)
 * Route: /(tabs)/(home)/settings/my-account/security/mfa
 *
 * 10DLC COMPLIANCE NOTE: The SMS disclosure text in this file is mandatory
 * per TCPA requirements for any screen that initiates SMS verification.
 * Do NOT remove or abbreviate this text.
 *
 * MFA-WIRE-1 Part C: four-state refinement (loading skeleton, error retry,
 * empty, populated) + token migration (zero hex codes). SMS disclosure
 * preserved unchanged. allowedPaths passed explicitly to the wizard.
 */
import React, { useState } from "react";
import {
  ScrollView,
  Text,
  Pressable,
  View,
  StyleSheet,
  Linking,
} from "react-native";
import { MFAEnrollmentWizard } from "@pilot/ui";
import {
  useMfaStatus,
  MFA_STATUS_QUERY_KEY,
} from "../../../../../../features/account-settings/hooks/useMfaStatus";
import { useQueryClient } from "@tanstack/react-query";
import { tokens, fontWeights } from "@/constants/style-constants";

export default function MfaScreen() {
  const { data: mfaStatus, isLoading, isError, refetch } = useMfaStatus();
  const queryClient = useQueryClient();
  const [showWizard, setShowWizard] = useState(false);

  const handleComplete = () => {
    setShowWizard(false);
    void queryClient.invalidateQueries({ queryKey: MFA_STATUS_QUERY_KEY });
  };

  const enrolledMethods = mfaStatus?.enrolled_methods ?? [];

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      testID="mfa-screen"
    >
      <Text style={styles.subtitle}>
        Add an extra layer of security to your account.
      </Text>

      {/* Enrolled methods — four data states (spec §5) */}
      <View style={styles.enrolledBox} testID="enrolled-methods-box">
        {isLoading ? (
          // Loading: 2 skeleton rows
          <>
            <View testID="mfa-status-skeleton" style={styles.skeletonRow} />
            <View style={styles.skeletonRow} />
          </>
        ) : isError ? (
          // Error: fault-colored text + retry button
          <View>
            <Text style={styles.errorText}>
              Could not load MFA status. Please try again.
            </Text>
            <Pressable
              testID="mfa-status-retry"
              onPress={() => void refetch()}
              accessibilityRole="button"
              accessibilityLabel="Try loading MFA status again"
              style={({ pressed }) => [
                styles.retryButton,
                pressed && styles.retryButtonPressed,
              ]}
            >
              <Text style={styles.retryText}>Try again</Text>
            </Pressable>
          </View>
        ) : enrolledMethods.length === 0 ? (
          // Empty
          <Text style={styles.enrolledText} testID="no-methods-text">
            No methods enrolled.
          </Text>
        ) : (
          // Populated
          enrolledMethods.map((method) => (
            <Text key={method} style={styles.enrolledText}>
              •{" "}
              {method === "totp"
                ? "Authenticator app (TOTP)"
                : method === "sms"
                  ? "SMS / Text message"
                  : method}
            </Text>
          ))
        )}
      </View>

      {/* Add method button — always rendered (below methods area) when not showing wizard */}
      {!showWizard && !isLoading && !isError && (
        <Pressable
          style={({ pressed }) => [
            styles.addButton,
            pressed && styles.addButtonPressed,
          ]}
          onPress={() => setShowWizard(true)}
          accessibilityRole="button"
          accessibilityLabel="Add authentication method"
          testID="add-mfa-method-btn"
        >
          <Text style={styles.addButtonText}>Add authentication method</Text>
        </Pressable>
      )}

      {/* MFAEnrollmentWizard — allowedPaths passed explicitly (defensive) */}
      {showWizard && (
        <View style={styles.wizardContainer} testID="mfa-wizard-container">
          <MFAEnrollmentWizard
            onComplete={handleComplete}
            onCancel={() => setShowWizard(false)}
            enrolledMethods={enrolledMethods}
            forceFlow={false}
            showRecoveryCodes={enrolledMethods.length === 0}
            allowedPaths={["totp", "sms"]}
            testID="mfa-enrollment-wizard"
          />
        </View>
      )}

      {/* ── 10DLC-COMPLIANT SMS DISCLOSURE — MANDATORY — DO NOT REMOVE OR EDIT ── */}
      <View style={styles.disclosureBox} testID="sms-disclosure">
        <Text style={styles.disclosureText}>
          {"📱 "}
          <Text style={styles.disclosureBold}>SMS verification</Text>
          {
            " — By enrolling your phone number, you consent to receive one-time verification codes from Pilot for Trades. Message frequency: One message per sign-in attempt, login or enrollment event. Message and data rates may apply. Reply STOP to opt out. Reply HELP for help. Privacy policy: "
          }
          <Text
            style={styles.disclosureLink}
            onPress={() =>
              void Linking.openURL(
                "https://www.pilotfortrades.com/legal/privacy",
              )
            }
            accessibilityRole="link"
            testID="sms-privacy-policy-link"
          >
            www.pilotfortrades.com/legal/privacy
          </Text>
        </Text>
      </View>
    </ScrollView>
  );
}

// ── Token-migrated styles (zero hex codes — spec §8.13) ───────────────────────

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: tokens.colors.neutral[50],
  },
  content: {
    padding: tokens.spacing[4],
    gap: tokens.spacing[4],
  },
  subtitle: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[600],
  },
  enrolledBox: {
    backgroundColor: tokens.lightTheme.background.secondary,
    borderRadius: tokens.radii.md,
    padding: tokens.spacing[3] + 2,
    borderWidth: 1,
    borderColor: tokens.colors.neutral[200],
  },
  skeletonRow: {
    backgroundColor: tokens.colors.neutral[100],
    height: 20,
    borderRadius: tokens.radii.sm,
    marginVertical: tokens.spacing[2],
  },
  enrolledText: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.neutral[800],
  },
  errorText: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.fault[600],
  },
  retryButton: {
    minHeight: tokens.touchTargets.mobile.sm,
    justifyContent: "center",
    alignItems: "center",
    marginTop: tokens.spacing[2],
    borderRadius: tokens.radii.md,
    paddingVertical: tokens.spacing[2],
  },
  retryButtonPressed: {
    opacity: 0.8,
  },
  retryText: {
    fontSize: tokens.mobileFontSizes.body,
    color: tokens.colors.brand[600],
  },
  addButton: {
    backgroundColor: tokens.colors.brand[600],
    borderRadius: tokens.radii.md,
    paddingVertical: tokens.spacing[3],
    paddingHorizontal: tokens.spacing[4],
    alignItems: "center",
    minHeight: tokens.touchTargets.mobile.md,
    justifyContent: "center",
  },
  addButtonPressed: {
    opacity: 0.85,
  },
  addButtonText: {
    color: tokens.lightTheme.brand.text,
    fontSize: tokens.mobileFontSizes.bodyLg,
    fontWeight: fontWeights.medium,
  },
  wizardContainer: {
    borderRadius: tokens.radii.lg,
    borderWidth: 1,
    borderColor: tokens.colors.neutral[200],
    backgroundColor: tokens.lightTheme.background.secondary,
    overflow: "hidden",
  },
  disclosureBox: {
    backgroundColor: tokens.colors.brand[50],
    borderRadius: tokens.radii.md,
    padding: tokens.spacing[3] + 2,
    borderWidth: 1,
    borderColor: tokens.colors.brand[100],
    marginTop: tokens.spacing[2],
  },
  disclosureText: {
    fontSize: tokens.mobileFontSizes.body,
    lineHeight: tokens.mobileLineHeights.body,
    color: tokens.colors.brand[800],
  },
  disclosureBold: {
    fontWeight: fontWeights.medium,
  },
  disclosureLink: {
    fontSize: tokens.mobileFontSizes.body,
    color: tokens.colors.brand[800],
    lineHeight: tokens.mobileLineHeights.body,
    textDecorationLine: "underline" as const,
  },
});
